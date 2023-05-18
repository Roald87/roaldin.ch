namespace GptSpelling

open OpenAI
open OpenAI.Chat
open System

module Gpt =
    let apiKey =
        let key = Environment.GetEnvironmentVariable("OPENAI_API_KEY")

        match key with
        | null -> failwith "OPENAI_API_KEY not found in environmental variables"
        | _ -> key

    let client =
        Config(
            { Endpoint = "https://api.openai.com/v1"
              ApiKey = apiKey },
            HttpRequester()
        )

    let spellcheck text =
        let prompt =
            $"""Corrigeer de spelling, interpunctie en grammatica van de volgende zin.
            Reageer alleen met de gecorrigeerde tekst in een code blok en behoud markdown opmaak.

            Tekst:
            {text}
            """
        let response =
            client
            |> chat
            |> create
                { Model = "text-davinci-003"
                          Messages = [| {Role = "user"; Content = prompt} |] }

        response.Choices[0]
