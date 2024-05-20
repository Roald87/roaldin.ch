import os
import re
import argparse
import base64
import logging
from typing import Optional, List
from PIL import Image
from openai import OpenAI


client = OpenAI()
from openai import OpenAI

# Set your OpenAI API key from environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def resize_image(image_path: str, max_size: int = 300) -> str:
    with Image.open(image_path) as img:
        img.thumbnail((max_size, max_size))
        resized_path = f"/tmp/resized_{os.path.basename(image_path)}"
        img.save(resized_path)
    return resized_path

def system(content):
    return {"role": "system", "content": content}

def user(content):
    return {"role": "user", "content": content}

def generate_alt_text(image_path: str) -> str:
    resized_image_path = resize_image(image_path)
    with open(resized_image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    completion = client.chat.completions.create(model="gpt-4o",
    messages=[
        system("You create alt texts from images for web usability purpouses for people with reduced eye sight. You describe whats in the image."),
        user(f"Generate an alt text for the following image:\n\n![image](data:image/jpeg;base64,{encoded_string})")
    ],
    temperature=0,
    max_tokens=50)

    logging.debug(f"API response: {completion}")

    return completion.choices[0].message.content.strip()


def process_file(filename: str, verbosity: int) -> None:
    with open(filename, 'r') as file:
        content = file.read()

    # Find all {% picture <filename> %} tags
    pattern = r'{% picture ([^ ]+) (?:--alt [^%]+)?%}'
    matches = re.findall(pattern, content)

    for image_filename in matches:
        image_path = os.path.join('assets', image_filename)
        if os.path.isfile(image_path):
            alt_text = generate_alt_text(image_path)

            # Replace or insert alt text in the tag
            content = re.sub(
                rf'({{% picture {re.escape(image_filename)})(?: --alt [^%]+)?(%}})',
                rf'\1 --alt "{alt_text}"\2',
                content
            )
            if verbosity > 1:
                print(f"Processed image: {image_filename}, generated alt text: {alt_text}")
        else:
            if verbosity > 0:
                print(f"Image file {image_path} does not exist.")

    # Write the updated content back to the file
    with open(filename, 'w') as file:
        file.write(content)

    if verbosity > 0:
        print(f"Updated alt text in {filename}.")

def process_files(filenames: List[str], verbosity: int) -> None:
    for filename in filenames:
        if not os.path.isfile(filename):
            print(f"File {filename} does not exist.")
            continue
        process_file(filename, verbosity)

def main() -> None:
    parser = argparse.ArgumentParser(description='Update alt text in image tags.')
    parser.add_argument('filenames', type=str, nargs='+', help='The filename(s) to process')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity level')
    args = parser.parse_args()

    verbosity = args.verbose
    log_level = max(0, 3 - verbosity) * 10
    logging.basicConfig(level=log_level)

    process_files(args.filenames, args.verbose)

if __name__ == '__main__':
    main()
