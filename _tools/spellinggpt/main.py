import logging
import os
import textwrap

import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")

def prompt(text) -> str:
    return textwrap.dedent(f"""\
    Corrigeer de spelling, interpunctie en grammatica van de volgende zin.
    Reageer alleen met de gecorrigeerde tekst in een code blok en behoud markdown opmaak.

    Tekst:
    {text}
    """)

def spellcheck(text: str) -> str:
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=prompt(text),
      max_tokens=2048,
      temperature=0
    )
    logging.info(response)

    return response["choices"][0]["text"]

print(spellcheck("prober het noch eens, met dze text."))
