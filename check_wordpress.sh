#!/bin/bash

# Check if a URL is provided as a parameter
if [ $# -ne 1 ]; then
    echo "Usage: $0 <URL>"
    exit 1
fi

# Get the URL from the command-line argument
URL="$1"

# Make an HTTP request to the URL using curl
response=$(curl -Is "$URL" | head -n 1)

# Check the HTTP response code
if [[ $response == *"200 OK"* ]]; then
    echo "WordPress is correctly configured and responding to $URL"
    exit 0
else
    echo "WordPress may not be correctly configured or is not responding to $URL"
    exit 1
fi
