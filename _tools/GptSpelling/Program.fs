open OpenAI
open OpenAI.Edits
open System

let apiKey =
    let key = Environment.GetEnvironmentVariable("OPENAI_API_KEY")
    match key  with
    | null -> failwith "OPENAI_API_KEY not found in environmental variables"
    | _ -> key

let client =
    Config(
        { Endpoint = "https://api.openai.com/v1"
          ApiKey =  apiKey },
        HttpRequester()
    )

let result =
    client
    |> edits
    |> Edits.create
           { Model = "text-davinci-edit-001"
             Input = "What day of the wek is is?"
             Instruction = "Fix the spelling mistakes" }

printfn "%A" (result)
