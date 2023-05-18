import logging
import os
import textwrap

import openai

logging.basicConfig(level=logging.DEBUG)

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
    # print(spellcheck("prober het noch eens, met dze text."))
    fname = "text.md"
    print(write_file(fname, spellcheck(read_file(fname))))
