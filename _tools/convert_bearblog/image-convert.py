import os
import re

def convert_picture_links(directory):
    # Regular expression pattern to match the markdown picture links
    pattern = r"!\[(.*?)\]\(assets/(.*?\.(?:png|jpg|jpeg|gif))\)"

    # Iterate over all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            with open(filepath, "r") as file:
                content = file.read()

            # Replace the markdown picture links with the desired format
            converted_content = re.sub(pattern, r"{% picture \2 --alt \1 %}", content)

            # Write the updated content back to the file
            with open(filepath, "w") as file:
                file.write(converted_content)

            print(f"Converted picture links in {filename}")

# Specify the directory where the markdown files are located
directory_path = "../../_posts"

# Call the function to convert the picture links
convert_picture_links(directory_path)
