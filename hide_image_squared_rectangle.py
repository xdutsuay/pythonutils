#!/usr/bin/env python3
"""
Hide a 2D image (or a simple .obj mesh projected to 2D) inside a colorful
"squared rectangle" mosaic — recursive adaptive square subdivision.

Inspired by the Brooks–Smith–Stone–Tutte squared-rectangle / aiyopasta-style
image mosaics: high-detail regions break into many small squares; flat regions
stay as large squares painted with the region's mean color. The photo is still
recognizable, but "hidden" inside a Mondrian-like tiling of squares that
exactly fills a rectangle.

Dependencies (common):
  pip install pillow numpy

Usage:
  # From a photo / illustration
  python hide_image_squared_rectangle.py photo.jpg -o mosaic.png

  # Tune detail vs. chunkiness
  python hide_image_squared_rectangle.py photo.jpg -o mosaic.png \\
      --max-depth 8 --min-size 4 --variance 18 --seed 42

  # Demo with a built-in synthetic image (no input file)
  python hide_image_squared_rectangle.py --demo -o demo_mosaic.png

  # Simple 3D: orthographic project a tiny .obj, then mosaic it
  python hide_image_squared_rectangle.py mesh.obj -o mosaic.png --obj-size 512

  # Prefer rendering complex 3D in Blender/etc. to PNG first; --from-obj is
  # only a minimal vertex/face orthographic rasterizer (no materials/UVs).
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

RGB = Tuple[int, int, int]
Square = Tuple[int, int, int, RGB]  # x, y, side, fill color


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def load_rgb(path: Path) -> np.ndarray:
    """Load an image as uint8 HxWx3 RGB."""
    img = Image.open(path).convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def synthetic_demo(width: int = 512, height: int = 384, seed: int = 0) -> np.ndarray:
    """Build a colorful synthetic scene so --demo works with no input file."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:height, 0:width]
    # Soft gradient background
    r = (40 + 180 * xx / width).astype(np.uint8)
    g = (30 + 160 * yy / height).astype(np.uint8)
    b = (80 + 100 * (1 - xx / width)).astype(np.uint8)
    canvas = np.stack([r, g, b], axis=-1)

    # Circles / blobs for recognizable structure after mosaicing
    for cx, cy, rad, color in [
        (width * 0.30, height * 0.40, min(width, height) * 0.18, (230, 57, 70)),
        (width * 0.65, height * 0.55, min(width, height) * 0.22, (42, 157, 143)),
        (width * 0.50, height * 0.28, min(width, height) * 0.12, (255, 190, 11)),
        (width * 0.78, height * 0.30, min(width, height) * 0.10, (131, 56, 236)),
    ]:
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= rad**2
        canvas[mask] = color

    # Noisy stripe for extra mid-frequency detail
    stripe = (yy > height * 0.72) & (yy < height * 0.82)
    noise = rng.integers(0, 40, size=(height, width, 3), dtype=np.int16)
    canvas = np.clip(canvas.astype(np.int16) + noise * stripe[..., None], 0, 255).astype(
        np.uint8
    )
    return canvas


def region_variance(arr: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    """Mean per-channel variance over the region (detail proxy)."""
    patch = arr[y : y + h, x : x + w]
    if patch.size == 0:
        return 0.0
    # Variance of luminance is enough and cheap
    lum = (
        0.299 * patch[..., 0].astype(np.float64)
        + 0.587 * patch[..., 1].astype(np.float64)
        + 0.114 * patch[..., 2].astype(np.float64)
    )
    return float(lum.var())


def region_mean_color(arr: np.ndarray, x: int, y: int, w: int, h: int) -> RGB:
    patch = arr[y : y + h, x : x + w]
    if patch.size == 0:
        return (0, 0, 0)
    mean = patch.reshape(-1, 3).mean(axis=0)
    return (int(mean[0]), int(mean[1]), int(mean[2]))


# ---------------------------------------------------------------------------
# Minimal .obj → orthographic RGB raster
# ---------------------------------------------------------------------------

def parse_obj_vertices_faces(
    path: Path,
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int]]]:
    """Parse v / f lines only. Faces may be triangulated on the fly (fan)."""
    verts: List[Tuple[float, float, float]] = []
    faces: List[Tuple[int, int, int]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "v" and len(parts) >= 4:
                verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == "f" and len(parts) >= 4:
                idxs = []
                for p in parts[1:]:
                    # formats: v | v/vt | v/vt/vn | v//vn  (1-based)
                    idxs.append(int(p.split("/")[0]) - 1)
                for i in range(1, len(idxs) - 1):
                    faces.append((idxs[0], idxs[i], idxs[i + 1]))
    return verts, faces


def rasterize_obj(
    path: Path,
    size: int = 512,
    seed: int = 0,
) -> np.ndarray:
    """
    Tiny orthographic projector: drop Z for XY, fit to square canvas, paint
    triangles with a depth-tinted flat color. Good enough for a silhouette /
    low-poly mesh. Complex scenes should be rendered to PNG externally.
    """
    verts, faces = parse_obj_vertices_faces(path)
    if not verts:
        raise ValueError(f"No vertices found in {path}")

    pts = np.asarray(verts, dtype=np.float64)
    # Orthographic: use X/Y; if the mesh is flat in XY, fall back to XZ
    span_xy = float(np.ptp(pts[:, 0]) + np.ptp(pts[:, 1]))
    span_xz = float(np.ptp(pts[:, 0]) + np.ptp(pts[:, 2]))
    if span_xy < 1e-9 and span_xz > span_xy:
        xy = pts[:, [0, 2]]
        depth = pts[:, 1]
    else:
        xy = pts[:, [0, 1]]
        depth = pts[:, 2]

    # Normalize to [margin, size-margin]
    margin = size * 0.06
    mn = xy.min(axis=0)
    mx = xy.max(axis=0)
    span = np.maximum(mx - mn, 1e-9)
    scale = (size - 2 * margin) / span.max()
    xy_pix = (xy - mn) * scale + margin
    # Center the shorter axis
    extra = (size - 2 * margin) - span * scale
    xy_pix += extra / 2.0

    d_min, d_max = float(depth.min()), float(depth.max())
    d_span = max(d_max - d_min, 1e-9)

    rng = random.Random(seed)
    # Stable pastel-ish palette keyed by face index
    base_palette = [
        (230, 57, 70),
        (255, 190, 11),
        (42, 157, 143),
        (69, 123, 157),
        (131, 56, 236),
        (255, 0, 110),
        (0, 180, 216),
        (144, 190, 109),
        (249, 65, 68),
        (6, 214, 160),
    ]

    img = Image.new("RGB", (size, size), (18, 18, 24))
    draw = ImageDraw.Draw(img)

    # Paint back-to-front by mean depth
    order = []
    for i, (a, b, c) in enumerate(faces):
        if max(a, b, c) >= len(verts):
            continue
        z = (depth[a] + depth[b] + depth[c]) / 3.0
        order.append((z, i, a, b, c))
    order.sort()  # far first

    for z, i, a, b, c in order:
        poly = [
            (float(xy_pix[a, 0]), float(xy_pix[a, 1])),
            (float(xy_pix[b, 0]), float(xy_pix[b, 1])),
            (float(xy_pix[c, 0]), float(xy_pix[c, 1])),
        ]
        base = base_palette[i % len(base_palette)]
        # Darken with depth a bit so silhouette reads after mosaicing
        t = (z - d_min) / d_span
        shade = 0.55 + 0.45 * (1.0 - t)
        color = tuple(max(0, min(255, int(c_ * shade))) for c_ in base)
        # Tiny jitter so adjacent faces don't merge into one variance blob
        jitter = rng.randint(-8, 8)
        color = tuple(max(0, min(255, c_ + jitter)) for c_ in color)
        draw.polygon(poly, fill=color)

    return np.asarray(img, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Adaptive squared-rectangle dissection
# ---------------------------------------------------------------------------

@dataclass
class DissectParams:
    max_depth: int = 8
    min_size: int = 4
    variance: float = 18.0  # luminance variance threshold
    seed: int = 0


def _greedy_pack_squares(
    arr: np.ndarray, x: int, y: int, w: int, h: int
) -> List[Square]:
    """Tile a rectangle with squares; each gets the mean color of its patch."""
    out: List[Square] = []
    cx, cy, cw, ch = x, y, w, h
    while cw > 0 and ch > 0:
        s = min(cw, ch)
        color = region_mean_color(arr, cx, cy, s, s)
        out.append((cx, cy, s, color))
        if cw > ch:
            cx += s
            cw -= s
        elif ch > cw:
            cy += s
            ch -= s
        else:
            break
    return out


def dissect_rectangle(
    arr: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    params: DissectParams,
    depth: int = 0,
) -> List[Square]:
    """
    Recursively dissect (x,y,w,h) into squares.

    Stop (paint / greedy-pack) when depth, size, or low variance says so.
    Otherwise:
      - square  → split into 4 quadrants
      - wider   → peel a square of side h, recurse on the leftover strip
                  OR bisect if both halves stay useful; we peel to keep
                  true squares in the tiling
      - taller  → peel a square of side w
    """
    if w <= 0 or h <= 0:
        return []

    # Clamp to image bounds
    H, W = arr.shape[:2]
    if x >= W or y >= H:
        return []
    w = min(w, W - x)
    h = min(h, H - y)
    if w <= 0 or h <= 0:
        return []

    stop = (
        depth >= params.max_depth
        or min(w, h) <= params.min_size
        or region_variance(arr, x, y, w, h) <= params.variance
    )

    if stop:
        if w == h:
            return [(x, y, w, region_mean_color(arr, x, y, w, h))]
        return _greedy_pack_squares(arr, x, y, w, h)

    squares: List[Square] = []
    if w == h:
        # Split into 4 (handle odd sizes: left/top get floor, rest get remainder)
        s = w // 2
        rem = w - s
        squares += dissect_rectangle(arr, x, y, s, s, params, depth + 1)
        squares += dissect_rectangle(arr, x + s, y, rem, s, params, depth + 1)
        squares += dissect_rectangle(arr, x, y + s, s, rem, params, depth + 1)
        squares += dissect_rectangle(arr, x + s, y + s, rem, rem, params, depth + 1)
    elif w > h:
        # High detail on a wide rect: peel one square, recurse on leftover.
        # Prefer peeling on the side with higher local variance so detail
        # areas get refined first.
        left_var = region_variance(arr, x, y, h, h) if h <= w else 0.0
        right_var = region_variance(arr, x + (w - h), y, h, h) if w >= h else 0.0
        if left_var >= right_var:
            squares += dissect_rectangle(arr, x, y, h, h, params, depth + 1)
            squares += dissect_rectangle(arr, x + h, y, w - h, h, params, depth + 1)
        else:
            squares += dissect_rectangle(arr, x + (w - h), y, h, h, params, depth + 1)
            squares += dissect_rectangle(arr, x, y, w - h, h, params, depth + 1)
    else:
        top_var = region_variance(arr, x, y, w, w) if w <= h else 0.0
        bot_var = region_variance(arr, x, y + (h - w), w, w) if h >= w else 0.0
        if top_var >= bot_var:
            squares += dissect_rectangle(arr, x, y, w, w, params, depth + 1)
            squares += dissect_rectangle(arr, x, y + w, w, h - w, params, depth + 1)
        else:
            squares += dissect_rectangle(arr, x, y + (h - w), w, w, params, depth + 1)
            squares += dissect_rectangle(arr, x, y, w, h - w, params, depth + 1)

    return squares


def render_squares(
    squares: Sequence[Square],
    width: int,
    height: int,
    gap: int = 1,
    bg: RGB = (0, 0, 0),
) -> Image.Image:
    """Paint squared tiling; optional 1px gap for the classic mosaic look."""
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    for x, y, s, color in squares:
        # Inset by gap so neighboring squares don't bleed together
        x0, y0 = x + gap, y + gap
        x1, y1 = x + s - 1, y + s - 1
        if x1 >= x0 and y1 >= y0:
            draw.rectangle([x0, y0, x1, y1], fill=color)
    return img


def hide_image(
    arr: np.ndarray,
    params: DissectParams,
    gap: int = 1,
) -> Tuple[Image.Image, List[Square]]:
    h, w = arr.shape[:2]
    squares = dissect_rectangle(arr, 0, 0, w, h, params, depth=0)
    return render_squares(squares, w, h, gap=gap), squares


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Hide a 2D image (or simple .obj projection) inside a colorful "
            "squared-rectangle mosaic."
        )
    )
    p.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Input image (.png/.jpg/…) or .obj mesh. Omit with --demo.",
    )
    p.add_argument(
        "-o",
        "--output",
        default="squared_mosaic.png",
        help="Output PNG path (default: squared_mosaic.png)",
    )
    p.add_argument("--max-depth", type=int, default=8, help="Max recursion depth")
    p.add_argument(
        "--min-size",
        type=int,
        default=4,
        help="Smallest square side in pixels before forced leaf",
    )
    p.add_argument(
        "--variance",
        type=float,
        default=18.0,
        help="Luminance variance threshold; lower → more splits / finer mosaic",
    )
    p.add_argument("--seed", type=int, default=0, help="RNG seed (obj face jitter)")
    p.add_argument(
        "--gap",
        type=int,
        default=1,
        help="Pixel gap between squares (0 = seamless)",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Ignore input and mosaic a built-in synthetic image",
    )
    p.add_argument(
        "--obj-size",
        type=int,
        default=512,
        help="Raster size when input is .obj (square canvas)",
    )
    p.add_argument(
        "--save-projection",
        default=None,
        help="If input is .obj, also save the raw orthographic raster here",
    )
    return p


def load_source(args: argparse.Namespace) -> Tuple[np.ndarray, str]:
    """Resolve CLI input into an RGB array + label."""
    if args.demo or args.input is None:
        if args.input is None and not args.demo:
            print(
                "No input given — running --demo synthetic image. "
                "Pass an image path or --demo explicitly.",
                file=sys.stderr,
            )
        return synthetic_demo(seed=args.seed), "synthetic-demo"

    path = Path(args.input)
    if not path.exists():
        raise FileNotFoundError(f"input not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".obj":
        print(f"rasterizing .obj → {args.obj_size}×{args.obj_size} orthographic…")
        arr = rasterize_obj(path, size=args.obj_size, seed=args.seed)
        if args.save_projection:
            Image.fromarray(arr).save(args.save_projection)
            print(f"wrote projection {args.save_projection}")
        return arr, str(path)

    try:
        return load_rgb(path), str(path)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            f"unsupported input '{path}' ({exc}). "
            "Use a raster image, a simple .obj, or --demo."
        ) from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    params = DissectParams(
        max_depth=args.max_depth,
        min_size=max(1, args.min_size),
        variance=max(0.0, args.variance),
        seed=args.seed,
    )

    try:
        arr, source_label = load_source(args)
    except (FileNotFoundError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    mosaic, squares = hide_image(arr, params, gap=max(0, args.gap))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    mosaic.save(out)

    h, w = arr.shape[:2]
    area = sum(s * s for _, _, s, _ in squares)
    print(
        f"hid {source_label} → {out} "
        f"({w}×{h}, {len(squares)} squares, covered≈{area}/{w * h} px, "
        f"depth≤{params.max_depth}, min={params.min_size}, var≤{params.variance})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
