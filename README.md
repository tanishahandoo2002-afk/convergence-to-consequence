# From Convergence to Consequence

Does the brain's episodic-retrieval network predict and causally support memory?

This project builds a curated activation likelihood estimation (ALE) map of successful episodic
retrieval (RQ1), then tests it two ways against a domain-general control network: on single trials
of 7T fMRI from the Natural Scenes Dataset (RQ2), and on published sham-controlled tDCS/tACS trials
with electric-field modelling (RQ3).

*Tanisha Handoo, B.Sc. Neurosciences & Neuropsychology, Amity University.*

## Status

Every stage has been run, including the RQ2 robustness run on the b2 betas.
The results are written up in [`docs/report.md`](docs/report.md).
A personal project, not a publication: no preprint or OSF registration. The protocol is in
[`docs/registration-1-rq1.md`](docs/registration-1-rq1.md).

Results are written to `rq2_nsd/results/`, `rq3_stimulation/results/` and `results/` and are not
committed. The main estimates, and every deviation from the protocol, are in [`CHANGELOG.md`](CHANGELOG.md).

## How to run

```bash
export C2C_DATA=/Volumes/<drive>/c2c_data      # large and non-shareable data
export NCBI_EMAIL=<contact email for NCBI E-utilities>
export ASI_API_KEY=<key>                        # AI screening rater 1 (asi1-mini)
OLLAMA_MODELS=$C2C_DATA/ollama ollama serve     # AI screening rater 2 (qwen2.5:7b-instruct)
make setup    # environment + setup check (Python venv via uv, R packages via renv::restore())
make test     # known-answer tests on synthetic data (Python and R)
```

| Stage | Command | Needs |
| --- | --- | --- |
| RQ1 search, screening, ALE | `make rq1-search`, `make rq1-screen`, `make rq1-check-screen`, `make rq1` | PubMed, ASI key, Ollama |
| Masks (frozen) | `make masks` | RQ1 results |
| RQ2 native masks | `python -m rq2_nsd.to_native`, then `python -m checks.check_rq2 --native` | NSD access, frozen masks, overlay sign-offs |
| RQ2 blind pilot, extraction, models | `make rq2-pilot`, `make rq2` | native masks |
| RQ2 b2 robustness (extraction, models, comparison with b3) | `make rq2-b2` | RQ2 b3 results |
| RQ3 search, screening | `make rq3-search`, `make rq3-screen`, `make rq3-check-screen` | PubMed, ASI key, Ollama |
| RQ3 electric fields | `make rq3-fields` | SimNIBS 4.6 |
| RQ3 effect sizes, models | `make rq3-es`, `make rq3` | extraction sheets, field values |
| Integration (H2b next to H3b) | `make integration` | RQ2 and RQ3 results |
| Explainer page (charts, brain images) | `make page` → `webpage/build/c2c.html` | every stage's results |

A full extraction streams every NSD session once and takes many hours; re-runs skip sessions already
listed in the manifest.

Requires Python 3.12 and R 4.5.

Every stage target runs its check script afterwards and stops if the check fails.
Design: [`docs/design.md`](docs/design.md). Deviations from the protocol: [`CHANGELOG.md`](CHANGELOG.md).

## Data access

| Data | Access |
| --- | --- |
| BrainMap (Sleuth) | Account via the BrainMap database application form |
| Natural Scenes Dataset | NSD Data Access Agreement; raw NSD files are never redistributed |
| OASIS-2 | Open access under the OASIS data use terms; one T1 scan is used, kept outside the repo |
| PubMed | Open |

## Natural Scenes Dataset

RQ2 uses the Natural Scenes Dataset: Allen, St-Yves, Wu, Breedlove, Prince, Dowdle, Nau, Caron,
Pestilli, Charest, Hutchinson, Naselaris and Kay, "A massive 7T fMRI dataset to bridge cognitive
neuroscience and artificial intelligence", *Nature Neuroscience* 25, 116-126 (2021),
doi:[10.1038/s41593-021-00962-x](https://doi.org/10.1038/s41593-021-00962-x).
Collection of the NSD dataset was supported by NSF IIS-1822683 and NSF IIS-1822929.
No NSD file, trial table or image is in this repository.

## Use of AI tools

Title/abstract screening used two independent large language model raters, plus a third AI
suggestion on each record routed to the author. The author accepted every suggestion as one
decision, so these decisions equal the AI suggestions (`CHANGELOG.md`, 2026-11-07).
No second human rater took part, so no human reliability measure is reported for screening.
Extracted contrasts were chosen by an AI assistant, and the author accepted its suggestions as one
decision, without a recorded paper-by-paper check. 17 BrainMap experiments stay in unverified,
because their papers could not be accessed, and a verified-only map is produced alongside the main one.
An AI assistant also helped draft code; the author ran, read and checked every script.
At the team's request, an AI assistant drafted `docs/report.md` from the scripts' outputs.
Coordinates came from BrainMap exports or were read by a script from PMC tables, from those same
AI-chosen rows (`CHANGELOG.md`, 2026-11-07). No person or model typed them.
