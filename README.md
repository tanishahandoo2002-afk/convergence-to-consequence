# From Convergence to Consequence

Does the brain's episodic-retrieval network predict and causally support memory?

This project builds a curated activation likelihood estimation (ALE) map of successful episodic
retrieval (RQ1), then tests it two ways against a domain-general control network: on single trials
of 7T fMRI from the Natural Scenes Dataset (RQ2), and on published sham-controlled tDCS/tACS trials
with electric-field modelling (RQ3).

*Tanisha Handoo, B.Sc. Neurosciences & Neuropsychology, Amity University.*

## Status

RQ1 pipeline built; RQ2 and RQ3 analysis code built and tested on simulated data, waiting for data access.
Registrations: to be added.

## How to run

```bash
export C2C_DATA=/Volumes/<drive>/c2c_data      # large and non-shareable data
export NCBI_EMAIL=<contact email for NCBI E-utilities>
export GEMINI_API_KEY=<key>                     # AI screening rater 1
OLLAMA_MODELS=$C2C_DATA/ollama ollama serve     # AI screening rater 2 (qwen2.5:7b-instruct)
make setup    # environment + setup check (Python venv via uv, R packages via renv::restore())
make test     # known-answer tests on synthetic data (Python and R)
```

| Stage | Command | Needs |
| --- | --- | --- |
| RQ1 search, screening, ALE | `make rq1-search`, `make rq1-screen`, `make rq1-check-screen`, `make rq1` | PubMed, Gemini key, Ollama |
| Masks (frozen) | `make masks` | RQ1 results |
| RQ2 blind pilot, extraction, models | `make rq2-pilot`, `make rq2` | NSD access, native masks |
| RQ3 search, screening | `make rq3-search`, `make rq3-screen`, `make rq3-check-screen` | PubMed, Gemini key, Ollama |
| RQ3 effect sizes, models | `make rq3-es`, `make rq3` | extraction sheets, field values |

Requires Python 3.12 and R 4.5.

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
