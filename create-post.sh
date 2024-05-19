#!/bin/bash

# Get the post name and future days as input parameters
NAME=$1
FUTURE_DAYS=$2

# Validate the post name input parameter
if [ -z "$NAME" ]; then
    echo "Error: Post name is required."
    exit 1
fi

# Set default value for future days if not provided
if [ -z "$FUTURE_DAYS" ]; then
    FUTURE_DAYS=0
fi

# Checkout the main branch
git checkout main

# Pull the latest changes
git fetch --prune
git pull

# Create a new branch
git branch $NAME
git checkout $NAME

# Create a new file with the specified format and future days
if [ "$FUTURE_DAYS" -eq 0 ]; then
    FILE_NAME="_posts/$(date +'%Y-%m-%d')-$NAME.md"
else
    FUTURE_DATE=$(date -d "+$FUTURE_DAYS days" +'%Y-%m-%d')
    FILE_NAME="_posts/${FUTURE_DATE}-${NAME}.md"
fi
touch $FILE_NAME

# Replace hyphens with spaces
NAME_WITH_SPACES="${NAME//-/ }"

# Capitalize the post name
CAPITALIZED_NAME="${NAME_WITH_SPACES^}"

# Add the content to the file
echo -e "---\nlayout: post\ntitle: $CAPITALIZED_NAME\nmeta_image: #generated/\n---" > $FILE_NAME

# Open obsidian
obsidian

# Display a success message
if [ "$FUTURE_DAYS" -eq 0 ]; then
    echo "Everything is ready for a post about $CAPITALIZED_NAME."
else
    echo "Everything is ready for a post about $CAPITALIZED_NAME on $FUTURE_DATE."
fi

# Check if the script is being called on its own
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Execute the meta-image script
    bash meta-image.sh $NAME
fi
