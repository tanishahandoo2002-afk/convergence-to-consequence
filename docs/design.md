# Design: From Convergence to Consequence (implementation)

Source plan: `From_Convergence_to_Consequence.md` (research questions, hypotheses, eligibility and models are defined there and not repeated here). This document fixes **how** the plan is implemented and **how each step is validated**. Dates in the plan are ignored; work proceeds at its own pace.

## 1. Decisions

| Topic | Decision |
|---|---|
| Structure | Plain scripts + Makefile; each stage target ends with its check script (Approach A) |
| Repo location | `~/convergence-to-consequence` (standalone; GitHub `tanishahandoo2002-afk/convergence-to-consequence`) |
| Large data | Under `$C2C_DATA` (external drive); never committed |
| NSD access | Stream each session file from the public S3 bucket `natural-scenes-dataset` into RAM; keep only the trial table. Only after the NSD Data Access Agreement form is submitted |
| SimNIBS | Local install on the external drive |
| Screening AI | Two independent raters: Gemini API and a local Qwen model via Ollama, both through the OpenAI-compatible chat endpoint; disagreement = "unsure" |
| Control network | Multiple-demand parcels (Fedorenko et al., 2013) primary; Yeo 2011 frontoparietal + ventral attention as registered sensitivity mask |
| RQ2 permutation | Within-session label shuffles (1,000) on a fast statistic: per-participant fixed-effects logistic slope, not a full glmer refit. Stated in registration 2 |
| Commits | Author `Tanisha Handoo <tanishahandoo2002@gmail.com>` (repo-local config); local `commit-msg` hook rejects AI attribution lines; contributors verified via GitHub API after first push |

## 2. Constraints

- Mac: 8 GB RAM, ~3 GB free internal disk → nothing large on the internal disk.
- No data access yet (BrainMap, NSD, OASIS-3, OSF all pending). Everything that needs no access (foundation, PubMed search, screening tooling, all known-answer tests) is built first.
- Human-only steps (access requests, registrations, Rayyan, second rater, supervisor review, screening decisions, contrast confirmation, visual checks) are supported by tooling and recorded, never automated away.

## 3. Validation principles

1. **Checks test process, never results.** A null or unexpected finding never fails a check; a broken pipeline always does.
2. **Every stage has a check script** (`checks/check_<stage>.py`, plain `assert`s with readable messages). `make <stage>` runs the stage then its check; a failed check stops `make`.
3. **Known-answer tests** (`tests/`: pytest for Python, plain R scripts with `stopifnot` for R): every analysis runs on synthetic data with a planted answer before it touches real data, plus a null case.
4. **Human sign-offs** are rows in `checks/human_signoffs.csv` (`date, step, item, who, result, note`). Checks that depend on a human step fail until the row exists.
5. **Freeze enforcement.** `masks/FROZEN.sha256` holds the hash of every frozen mask. Any RQ2/RQ3 stage verifies the hashes before running.
6. **Reproducibility.** One YAML config per analysis in `config/`, fixed seeds in config, software versions written to `results/versions.txt` on every run, every figure made by a script. `make all` from a fresh clone is the pre-preprint test.
7. **Deviations** from either registration are logged in `CHANGELOG.md` with date and reason.

## 4. Repository layout

```
convergence-to-consequence/
├── README.md               what, why, how to run, AI-use statement, registration links
├── Makefile                setup test rq1 masks rq2-pilot rq2 rq3-screen rq3-fields rq3 figures all
├── requirements.txt        exact Python pins (uv venv, Python 3.12)
├── renv.lock               exact R pins (lme4, metafor, clubSandwich, robvis)
├── config/                 rq1.yaml rq2.yaml rq3.yaml screening.yaml
├── tools/                  shared: pubmed_search.py screen.py kappa.py prisma.py versions.py
├── checks/                 check_<stage>.py, human_signoffs.csv
├── tests/                  known-answer tests
├── registrations/
├── rq1_map/
│   ├── search/  screening/  (criteria.md, AI decisions, human decisions, kappa)
│   ├── experiments.csv  coordinates.csv
│   ├── run_ale.py
│   └── results/
├── masks/                  build_masks.py, frozen masks (MNI), FROZEN.sha256
├── rq2_nsd/                to_native.py extract_trials.py models.R results/
├── rq3_stimulation/
│   ├── search/  screening/  effects.csv  montages.csv  rob2.csv
│   ├── effect_sizes.R  models.R
│   ├── simnibs/            run_montages.py, fields.csv
│   └── results/
├── integration.R
├── figures/
├── docs/design.md
└── CHANGELOG.md
```

## 5. Foundation

- `make setup`: creates the uv venv from `requirements.txt`, restores `renv.lock`, checks Ollama model and SimNIBS paths from config, writes `results/versions.txt`.
- `make test`: runs all known-answer tests.
- **Check:** `$C2C_DATA` exists and is writable; required tools resolve; git author for the repo is Tanisha's identity.

## 6. Shared tools

**`tools/pubmed_search.py`** — NCBI E-utilities (esearch + efetch) with the query from config. Writes `search/pubmed_<date>.csv` (PMID, DOI, title, abstract, year) and appends query, date and hit count to `search/search_log.csv`. Importers for BrainMap Sleuth exports (GingerALE text) and Scopus/PsycINFO (RIS/CSV) write the same columns.
*Check:* log row exists for every search file; row count equals logged hit count; no duplicate PMID/DOI after de-duplication (duplicates removed are counted for PRISMA).

**`tools/screen.py`** — for each record, sends title + abstract and the RQ's `criteria.md` (eligibility table verbatim) to each configured rater, temperature 0, requests JSON `{"decision": "include|exclude|unsure", "reason": "..."}`. Both raters use the OpenAI-compatible chat API (Gemini base URL; Ollama `localhost:11434/v1`), so one code path with `base_url` and `model` from `config/screening.yaml`. Logs per record: rater, exact model id (Ollama tag + digest), prompt SHA-256, timestamp, raw reply. Resumable (skips records already decided). Invalid JSON is retried once, then recorded as "unsure".
Merge rule: both include → include (human verifies); both exclude → exclude, with a seeded random 20% sent to the human; any disagreement → unsure (human decides).
Full-text stage: the same script proposes the contrast table and sample size from paper text; the human confirms each in the extraction sheet.

**`tools/kappa.py`** — Cohen's κ for Gemini–Qwen, each AI–human, human–second rater (on the overlapping records).
*Check:* every include/unsure has a human decision; the 20% exclude sample is fully reviewed; second-rater overlap ≥ 20% of records; if AI–human κ < 0.6, the check fails until every record has a human decision (plan §12 rule).

**`tools/prisma.py`** — PRISMA 2020 counts computed from search and screening logs, drawn as a figure.
*Check:* counts reconcile at every box.

## 7. RQ1 — the map

**Extraction sheets**
- `experiments.csv`: `exp_id, study_id, doi, subject_group, table_or_figure, contrast, contrast_type (success|recollection|familiarity), n, mean_age, space (MNI|TAL), source (brainmap|table_tool), contrast_verified_by`.
- `coordinates.csv`: `exp_id, x, y, z`.
- Coordinates come from BrainMap exports or a table-extraction tool, never typed by an AI.
- Several eligible contrasts from the same subject group are pooled into one `exp_id`.

*Check (`check_rq1_extraction.py`):* schema and types; `n ≥ 5`; space valid; every exp has ≥ 1 focus; each `subject_group` appears once; every focus (after Talairach → MNI) lies within the MNI brain mask, outliers listed and required in the sign-off; ≥ 20 experiments (warning between 17 and 20, failure below 17); a seeded 20% spot-check sample exists with a sign-off row; if any spot-check error is logged, all rows require sign-off.

**`run_ale.py`** (NiMARE)
- Talairach → MNI with Lancaster (`tal2icbm`), applied once in code.
- ALE with sample-size-based kernels; Monte Carlo FWE: voxel-level cluster-forming p < .001, cluster-level FWE p < .05, `n_iters` from config (5,000; tests use fewer); seed from config.
- Cluster table with peak coordinates, size and atlas labels (Harvard-Oxford).
- Jackknife (leave-one-experiment-out) per cluster; fail-safe N by adding generated null experiments until each cluster disappears (Acar et al., 2018 approach).
- H1b subtraction runs only if each contrast group has ≥ 17 experiments; otherwise logs "not run, k = …".

*Known-answer test:* 25 synthetic experiments with foci jittered around one point plus random foci → a significant cluster containing that point; 25 random-only experiments → no significant cluster.
*Check:* output files exist; parameters in outputs equal config; jackknife covers every experiment; versions recorded.

## 8. Masks

**`masks/build_masks.py`**
- Memory map: binarised thresholded ALE map.
- Memory top-50%: voxels in the memory map at or above the median ALE value (for RQ2 robustness).
- Control (primary): multiple-demand parcels minus any memory-map voxels.
- Control (sensitivity): Yeo 2011 7-network frontoparietal + ventral attention minus memory-map voxels.
- Downloaded parcel files have their source URL and checksum recorded.
- Writes `FROZEN.sha256`.

*Check:* each mask is binary, non-empty and inside the brain; memory and control masks do not overlap; hashes match `FROZEN.sha256`. A sign-off row records the date the masks were frozen; they are uploaded with registration 2.

## 9. RQ2 — NSD

**`to_native.py`** — nsdcode maps each frozen mask from MNI to each participant's `func1pt8mm` space (nearest neighbour). Downloads only the transform files. Saves an overlay image per participant for a visual check.
*Check:* frozen hashes match; every native mask non-empty; one sign-off row per participant (8).

**`extract_trials.py`**
- Per session: stream the b3 file (`betas_fithrf_GLMdenoise_RR`) over HTTPS from the S3 bucket into memory, decode with nibabel, convert to percent signal change, z-score each voxel within the session, average within each native mask per trial.
- Writes one trial table per session to `$C2C_DATA/rq2/<beta_version>/subjXX_sessYY.csv` in a single atomic write; appends to a manifest (S3 key, trials, time). Re-runs skip finished sessions.
- `--beta b2` repeats for the robustness version.
- Labels from `responses.tsv` + experimental design: image id, viewing number, old/new, response, outcome (hit/miss/FA/CR), RT, log delay from trial timestamps. Missing responses are excluded and counted.
- `--pilot` mode (subject 1, first sessions): outcome, old/new and response columns are not written; reports only trial counts, missing values and onset-signal distributions.
- First task in implementation (spike): test whether partial HDF5 reads over HTTP reduce download size enough to be worth it; otherwise whole-file streaming as above.

*Check:* 750 trials per session; image order from the design matches `responses.tsv` row by row; computed delay agrees in rank with NSD's trials-since-last-view for within-session repeats; data-quality report lists missing responses and extreme values (|z| > config threshold) and how they were handled as registered.

**`models.R`** (lme4)
- H2a, H2b, H2c as in plan §8.2, pooled and per participant; odds ratios with 95% CIs.
- Non-convergence simplification order: drop slope–intercept correlation → drop random slope → drop image intercept. The model actually used is logged.
- Robustness: b2 vs b3; leave-one-participant-out; top-50% map; Yeo control mask; permutation test (1,000 within-session shuffles, fast per-participant statistic).

*Known-answer test:* simulated trials (8 participants, image random effects) with a planted map-signal slope → estimated slope's CI contains it; null simulation → slope CI contains 0.
*Check:* convergence status logged for every model; residual/diagnostic plots written; trial counts per participant and outcome reported.

**Data rule:** trial tables stay in `$C2C_DATA`; only summary results and figures are committed until the NSD terms are confirmed to allow sharing derived values.

## 10. RQ3 — stimulation meta-analysis

**Search and screening:** shared tools with RQ3 `criteria.md` (plan §8.3 step 2) and query; PROSPERO/OSF overlap check recorded as a sign-off; PRISMA from logs.

**Extraction**
- `effects.csv`: fields from plan §7.2 plus `higher_is_better` and `design (parallel|crossover)`.
- `montages.csv`: `montage_id, electrodes (10-10 names), sizes_cm, current_mA, type (tDCS|tACS)`; each effect references a `montage_id`.
- `rob2.csv`: one row per study, one column per RoB 2 domain.

**`effect_sizes.R`** (metafor `escalc`): Hedges' g for parallel designs; change-score standardised mean difference for crossover/within designs at r = .5, re-run at .3 and .7; sign set so positive g = better memory.
*Known-answer test:* g for hand-worked examples matches to 3 decimals.
*Check:* SD > 0; Ns consistent; recomputed g matches any reported g within tolerance (else flagged); every study fully rated in RoB 2; second-rater 20% sign-off present.

**`simnibs/run_montages.py`**
- For each montage: SimNIBS session on the Ernie head model, field mapped to MNI, mean field magnitude inside each frozen mask → `fields.csv` (tACS: peak amplitude).
- Clinical-arm montages repeated on an older-adult head model built with `charm` from an OASIS-3 T1.
- Fallback if SimNIBS is unworkable: electrode-to-mask distance, labelled as a proxy in every output.

*Known-answer tests:* doubling the current doubles the field (linearity); a reference F3–Fp2 1 mA montage on Ernie lands within the published range.
*Check:* frozen hashes match; every montage has a field value for every mask; no zero or NaN fields.

**`models.R`** (metafor `rma.mv`, random effects for effect within study; clubSandwich CR2 tests)
- H3a: g ~ field_map + sessions. H3b: g ~ field_map + field_control + sessions, Wald test of the difference between the two coefficients. H3c: g ~ test_type + sessions. H3d: g ~ field_map × group + sessions.
- Bias and robustness: funnel plot, PET-PEESE, multilevel Egger (SE as moderator), leave-one-study-out, r sensitivity.
- Fewer than 8 clinical trials → clinical arm descriptive only.

*Known-answer test:* simulated effects with a planted field slope → recovered within CI.
*Check:* models converge; k and number of studies reported for every estimate.

## 11. Integration

`integration.R`: one table and one figure placing the map-vs-control comparison from RQ2 (H2b) and RQ3 (H3b) side by side, with CIs. Interpretation and writing are the author's.

## 12. Order of work

1. Foundation (setup, Makefile, check harness, git/GitHub).
2. RQ1: PubMed search, dual-AI screening, extraction, ALE (BrainMap added when access arrives).
3. Masks frozen → registration 2.
4. In parallel: RQ2 known-answer tests, native masks, blind pilot; RQ3 search and screening.
5. RQ2 full extraction and models.
6. RQ3 extraction, effect sizes, field modelling, models.
7. Integration.

Each step gets its own implementation plan and is only started after the previous step's checks pass.

## 13. Out of scope for the code

Writing the registrations, preprints and README narrative; screening and extraction judgements; access applications. The code supports and records these; the author does them.
