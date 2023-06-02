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
        model="gpt-3.5-turbo",
        messages=[
            system("Jij corrigeert de spelling, grammatica en interpunctie van teksten. Je behoud markdown opmaak en je verandert geen yaml front matter."),
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
