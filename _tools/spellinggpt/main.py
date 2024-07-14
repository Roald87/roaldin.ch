import argparse
import logging
import os

import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

def system(content):
    return {"role": "system", "content": content}

def user(content):
    return {"role": "user", "content": content}

def spellcheck(text: str) -> str:
    completion = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            system("Je bent een editor en corrigeert de spelling, grammatica en interpunctie van teksten. "
                   "Daarnaast probeer je ook de flow van de tekst te verbeteren. "
                   "Verander zinnen die niet goed op elkaar aansluiten. "
                   "Probeer zinnen zo kort mogelijk te maken en probeer lange zinnen op te breken."
                   "Je behoud markdown opmaak en je verandert en verwijdert geen yaml front matter, die aan het begin van elk bestand staat. "
                   "Reageer alleen met de veranderde tekst."),
            user(text)
        ],
        temperature=0,
    )

    logging.debug(f"API response: {completion}")

    return completion.choices[0]["message"]["content"].strip()

def read_file(filename) -> str:
    with open(filename, 'r') as file:
        text = file.read()

    return text

def write_file(filename, text) -> None:
    with open(filename, 'w') as file:
        file.write(text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spellcheck CLI")
    parser.add_argument("filename", nargs="+", help="Input file name(s)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity level")

    args = parser.parse_args()
    filenames = args.filename

    verbosity = args.verbose
    log_level = max(0, 3 - verbosity) * 10
    logging.basicConfig(level=log_level)

    for filename in filenames:
        text = read_file(filename)
        spellchecked_text = spellcheck(text)
        write_file(filename, spellchecked_text + "\n")
