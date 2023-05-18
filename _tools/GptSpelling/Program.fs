open Argu
open GptSpelling.Gpt
open System
open System.IO

type CliError = | ArgumentsNotSpecified

let getExitCode result =
    match result with
    | Ok () -> 0
    | Error err ->
        match err with
        | ArgumentsNotSpecified -> 1


type Arguments =
    | Filename of path: string

    interface IArgParserTemplate with
        member this.Usage =
            match this with
            | Filename _ -> "Filename to correct the spelling of"

let writeAllText path contents = File.WriteAllText(path, contents)

[<EntryPoint>]
let main argv =
    let errorHandler =
        ProcessExiter(
            colorizer =
                function
                | ErrorCode.HelpText -> None
                | _ -> Some ConsoleColor.Red
        )

    let parser =
        ArgumentParser.Create<Arguments>(
            programName = "spellgpt",
            errorHandler = errorHandler
        )

    match parser.ParseCommandLine argv with
    | p when p.Contains(Filename) ->
        let filename = p.GetResult Filename
        spellcheck filename |> writeAllText "test.txt"
        Ok
    | _ ->
        printfn "%s" (parser.PrintUsage())
        Error ArgumentsNotSpecified
    |> getExitCode
