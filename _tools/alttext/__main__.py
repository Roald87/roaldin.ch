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

def generate_alt_text(image_path: str) -> str:
    resized_image_path = resize_image(image_path)
    with open(resized_image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    completion = client.chat.completions.create(model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """\
                    Je bent een expert in webtoegankelijkheid en bruikbaarheid. Je taak is om effectieve alt-tekst te genereren voor afbeeldingen die op websites worden gebruikt. "
                    Effectieve alt-tekst moet beknopt, beschrijvend en dezelfde informatie bieden als de afbeelding zou doen als deze zichtbaar was.
                    Het moet geen informatie herhalen die al beschikbaar is in de omringende tekst of bijschriften. Houd rekening met de volgende richtlijnen:
                    1. Wees specifiek en beknopt. Beschrijf de inhoud en het doel van de afbeelding.
                    2. Neem alle tekst op die onderdeel is van de afbeelding.
                    3. Vermijd het gebruik van zinnen zoals 'afbeelding van' of 'foto van'.
                    4. Als de afbeelding puur decoratief is en geen belangrijke informatie overbrengt, geef dit dan aan zodat het kan worden genegeerd door schermlezers.
                    Genereer een alt-tekst in het Nederlands voor de volgende afbeelding"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{encoded_string}"
                    }
                }
            ]
        }
    ],
    temperature=0,
    max_tokens=100)

    logging.debug(f"API response: {completion}")

    return completion.choices[0].message.content.strip()


def process_file(filename: str) -> None:
    with open(filename, 'r') as file:
        content = file.read()

    # Find all {% picture <filename> %} tags
    pattern = r'{% picture ([^ ]+)[^%]* %}'
    matches = re.findall(pattern, content)

    logging.debug(f"Matches: {matches}")

    for image_filename in matches:
        image_path = os.path.join('assets', image_filename)
        if os.path.isfile(image_path):
            alt_text = generate_alt_text(image_path).replace("\"", "")

            # Replace or insert alt text in the tag
            content = re.sub(
                rf'{{% picture {image_filename}[^%]? %}}',
                rf'{{% picture {image_filename} --alt {alt_text} %}}',
                content
            )
            logging.info(f"Processed image: {image_filename}, generated alt text: {alt_text}")
        else:
            logging.warning(f"Image file {image_path} does not exist.")

    # Write the updated content back to the file
    with open(filename, 'w') as file:
        file.write(content)

    if matches:
        logging.info(f"Updated alt text in {filename}.")

def process_files(filenames: List[str]) -> None:
    for filename in filenames:
        if not os.path.isfile(filename):
            logging.error(f"File {filename} does not exist.")
            continue
        process_file(filename)

def main() -> None:
    parser = argparse.ArgumentParser(description='Update alt text in image tags. Note: if there is already an alt text present, it will be replaced.')
    parser.add_argument('filenames', type=str, nargs='+', help='The filename(s) to process')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Increase verbosity level')
    args = parser.parse_args()

    verbosity = args.verbose
    log_level = max(0, 5 - verbosity) * 10
    logging.basicConfig(level=log_level)

    process_files(args.filenames)

if __name__ == '__main__':
    main()
