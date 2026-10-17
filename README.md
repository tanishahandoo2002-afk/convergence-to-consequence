# From Convergence to Consequence

Does the brain's episodic-retrieval network predict and causally support memory?

This project builds a curated activation likelihood estimation (ALE) map of successful episodic
retrieval (RQ1), then tests it two ways against a domain-general control network: on single trials
of 7T fMRI from the Natural Scenes Dataset (RQ2), and on published sham-controlled tDCS/tACS trials
with electric-field modelling (RQ3).

*Tanisha Handoo, B.Sc. Neurosciences & Neuropsychology, Amity University.*

## Status

Foundation and RQ1 pipeline under construction. Registrations: to be added.

## How to run

```bash
export C2C_DATA=/Volumes/<drive>/c2c_data      # large and non-shareable data
export NCBI_EMAIL=<contact email for NCBI E-utilities>
export GEMINI_API_KEY=<key>                     # AI screening rater 1
OLLAMA_MODELS=$C2C_DATA/ollama ollama serve     # AI screening rater 2 (qwen2.5:7b-instruct)
make setup    # environment + setup check
make test     # known-answer tests on synthetic data
```

Every stage target runs its check script afterwards and stops if the check fails.
Design: [`docs/design.md`](docs/design.md). Deviations from the registrations: [`CHANGELOG.md`](CHANGELOG.md).

## Data access

| Data | Access |
| --- | --- |
| BrainMap (Sleuth) | Account via the BrainMap database application form |
| Natural Scenes Dataset | NSD Data Access Agreement; raw NSD files are never redistributed |
| OASIS-3 | Data use agreement via NITRC |
| PubMed | Open |

## Use of AI tools

Title/abstract screening and contrast identification were assisted by large language models
(two independent raters). All inclusions and extracted contrasts were verified by the author;
AI–author agreement on a random 20% sample was κ = [to be filled after screening].
An AI assistant also helped draft code; the author ran, read and checked every script.
Coordinates were never transcribed by an AI.
