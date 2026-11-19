# AI-assisted conversion (design, not yet implemented)

Status: **deferred**. Today, natural-language input in Chat uses the existing
provider pipeline unchanged (`src/services/ai_service.run_natural_language`:
classify → generate a PuLP model → convert it to a `ModelSpec` → solve). It needs
`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, plus credits on that account. Without a
key, Chat shows a "credentials required" reply, keeps your text, and links to
the offline options (templates, Load Problem, AMPL-style input). This document
describes the planned next step. No code for it exists yet.

## Goal

Turn a description, or a document extracted by **Load Problem → Upload**, into
**AMPL-style source** that the user can read and edit. Then send that source
through the same deterministic parser and solver as hand-written models. The AI
proposes text; it never builds or solves models directly.

## Flow

1. The user submits natural language (or chooses **Convert to model** on an
   uploaded document).
2. OR Studio sends the text, a short grammar card for the subset in
   `docs/AMPL_SUBSET.md`, and two worked examples. The prompt asks for AMPL
   source only.
3. The reply is parsed with `parse_structured(text, "ampl")`:
   - **Parses:** show the source in Algebraic with a "Generated, review before
     solving" chip, plus the expanded preview. The user clicks Solve Model;
     nothing solves automatically.
   - **Fails:** make one repair round trip that sends back the parser's
     line/column message. If it still fails, show the source and the error and
     leave the user's text untouched.
4. Store the run with `source.origin = "ai_conversion"`, the provider and model
   name, and the prompt version. Diagnostics then show where the model came
   from.

## Guardrails

- The model must reference names found in the description; any variable that
  appears from nowhere gets a warning in the preview.
- Size caps: 200 variables and 200 constraints before indexing expands, and the
  reply is limited to 20 kB.
- Never ask for Python, and never `eval` the reply. The parser rejects anything
  outside the subset with a location.
- A structured parse failure on user-typed AMPL or OR-Learn never falls through
  to the AI. Conversion applies only when the format is Natural Language.
- Errors such as an exhausted balance (HTTP 429) or a missing key are shown
  as-is, with the offline options next to them.

## Evaluation before enabling

- Run a corpus of the Chat examples' descriptions (`catalog.NL`). Each converted
  model must parse and reach the documented objective (for example 2200 for
  furniture production).
- Track three metrics per provider and model: parse rate, objective match rate,
  and repair-round usage.
- Keep it behind a Settings toggle until the parse rate is at least 95% and the
  objective match rate is at least 90%.
