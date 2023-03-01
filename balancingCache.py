class Node:
    def __init__(self, key, value, height):
        self.key = key
        self.value = value
        self.height = height
        self.left = None
        self.right = None

class AVLTreeCache:
    def __init__(self):
        self.root = None

    def get(self, key):
        return self._get(self.root, key)

    def _get(self, node, key):
        if not node:
            return None
        if key < node.key:
            return self._get(node.left, key)
        elif key > node.key:
            return self._get(node.right, key)
        else:
            return node.value

    def put(self, key, value):
        self.root = self._put(self.root, key, value)

    def _put(self, node, key, value):
        if not node:
            return Node(key, value, 1)
        if key < node.key:
            node.left = self._put(node.left, key, value)
        elif key > node.key:
            node.right = self._put(node.right, key, value)
        else:
            node.value = value
        node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))
        balance = self.get_balance(node)
        if balance > 1 and key < node.left.key:
            return self.right_rotate(node)
        if balance < -1 and key > node.right.key:
            return self.left_rotate(node)
        if balance > 1 and key > node.left.key:
            node.left = self.left_rotate(node.left)
            return self.right_rotate(node)
        if balance < -1 and key < node.right.key:
            node.right = self.right_rotate(node.right)
            return self.left_rotate(node)
        return node

    def get_height(self, node):
        if not node:
            return 0
        return node.height

    def get_balance(self, node):
        if not node:
            return 0
        return self.get_height(node.left) - self.get_height(node.right)

    def left_rotate(self, node):
        right_child = node.right
        node.right = right_child.left
        right_child.left = node
        node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))
        right_child.height = 1 + max(self.get_height(right_child.left), self.get_height(right_child.right))
        return right_child

    def right_rotate(self, node):
        left_child = node.left
        node.left = left_child.right
        left_child.left = node
        node.height = 1 + max(self.get_height(node.left), self.get_height(node.right))
        left_child.height = 1 + max(self.get_height(right_child.left), self.get_height(right_child.right))
        return left_child
