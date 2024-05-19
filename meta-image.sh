#!/bin/bash

# Get the post name and filename as input parameters
NAME=$1
FILENAME=$2

# Validate the post name input parameter
if [ -z "$NAME" ]; then
    echo "Error: Post name is required."
    exit 1
fi

# If no filename is provided, search for a file with the filename pattern in the _posts folder
if [ -z "$FILENAME" ]; then
    FILENAME=$(find _posts/ -type f -regextype posix-extended -regex ".*[0-9]{4}-[0-9]{2}-[0-9]{2}-$NAME\.md" | head -n 1)
fi

# Validate the filename
if [ -z "$FILENAME" ]; then
    echo "Error: File with the filename pattern [$NAME] not found in the _posts folder."
    exit 1
fi

echo "Using filename $FILENAME"

# Monitor the output for the image filename pattern
while read -r line; do
    echo $line
    if [[ $line =~ $NAME-1-500-[a-z0-9]+\.webp ]]; then
        # Copy the image filename
        IMAGE_FILENAME="${BASH_REMATCH[0]}"

        # Replace the image line in the file
        sed -i "s/image: #generated\//image: generated\/$IMAGE_FILENAME/" $FILENAME
    fi
done < <(bundle exec jekyll serve --future)
