import argparse
import logging
import os
import textwrap

import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

def spellcheck_prompt(text) -> str:
    return textwrap.dedent(f"""\
    Corrigeer de spelling, interpunctie en grammatica van de volgende zin.
    Reageer alleen met de gecorrigeerde tekst in een code blok en behoud markdown opmaak.

    Tekst:
    {text}
    """)

def spellcheck(text: str) -> str:
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=spellcheck_prompt(text),
      max_tokens=2048,
      temperature=0
    )
    logging.debug(f"API response: {response}")

    return response["choices"][0]["text"].strip()

def read_file(filename) -> str:
    with open(filename, 'r') as file:
        text = file.read()

    return text

def write_file(filename, text) -> None:
    with open(filename, 'w') as file:
        file.write(text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spellcheck CLI")
    parser.add_argument("filename", help="Input file name")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity level")

    args = parser.parse_args()
    filename = args.filename

    verbosity = args.verbose
    log_level = max(0, 3 - verbosity) * 10
    logging.basicConfig(level=log_level)

    text = read_file(filename)
    spellchecked_text = spellcheck(text)
    write_file(filename, spellchecked_text)
