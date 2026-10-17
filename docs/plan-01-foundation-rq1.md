# Foundation + RQ1 (map) Implementation Plan

> Execution: task by task, in order. Steps use checkbox (`- [ ]`) syntax for tracking. Each task ends with its tests passing and a commit.

**Goal:** A reproducible repo that runs the RQ1 pipeline end to end (search → dual-AI screening → extraction checks → ALE → frozen masks), with a check after every stage.

**Architecture:** Plain Python scripts run from the repo root as modules (`python -m tools.screen`), driven by a Makefile whose stage targets end with `python -m checks.check_<stage>`. Shared logic lives in `tools/`; RQ1-specific logic in `rq1_map/` and `masks/`. Config in YAML; secrets and large data in environment variables.

**Tech Stack:** Python 3.12, uv, NiMARE 0.22.x, nilearn 0.14.x, nibabel, pandas, scikit-learn (κ), openai (OpenAI-compatible client for Gemini and Ollama), pypdf, PyYAML, requests, matplotlib, pytest.

**Spec:** `docs/design.md` (sections 3, 5, 6, 7, 8). Research definitions: `From_Convergence_to_Consequence.md` §8.1.

## Global Constraints

- Commits authored `Tanisha Handoo <tanishahandoo2002@gmail.com>`; no AI attribution lines (the local `commit-msg` hook enforces this).- Python 3.12; exact pins in `requirements.txt` compiled by `uv pip compile` from `requirements.in`.
- Large or non-shareable data under `$C2C_DATA`; never in git. API keys only in env vars (`GEMINI_API_KEY`, `NCBI_API_KEY` optional); `NCBI_EMAIL` env var required by the search.
- Ollama models stored on the external drive (`OLLAMA_MODELS=$C2C_DATA/ollama`), model `qwen2.5:7b-instruct` (~4.7 GB, fits 8 GB RAM).
- Checks test process, never results (spec §3.1). A check never asserts a hypothesis outcome.
- Seeds come from config; every stage appends software versions to `results/versions.txt`.
- ALE: sample-size kernels, cluster-forming p < .001, cluster-level FWE p < .05, `n_iters: 5000` (tests use ≤ 200), Lancaster Talairach→MNI.
- ≥ 20 experiments target; 17–19 warns; < 17 fails. H1b only if each contrast group ≥ 17.
- Screening: both AI raters at temperature 0; disagreement → unsure; seeded 20% of agreed excludes to human; AI–human κ < 0.6 → every record needs a human decision.

## Review Focus

1. **API failure mid-run** (Gemini 429, Ollama not running): a network/API error must stop or skip that record without writing a decision; only invalid JSON after one retry becomes "unsure". Test in Task 4.
2. **Records missing DOI or abstract:** de-duplication must not merge two records just because both DOIs are empty; screening must still send title-only records. Test in Task 3.
3. **Foci at or past the brain edge / mislabelled Talairach:** listed as outliers needing sign-off, not silently dropped and not a crash. Test in Task 7.
4. **Same subject group entered twice** (two contrasts from one sample): extraction check fails naming the group. Test in Task 7.
5. **Re-running mask build after freeze:** must refuse to overwrite frozen masks unless `--refreeze` is passed, and then require a new `CHANGELOG.md` entry dated today. Test in Task 10.

---

### Task 1: Repo foundation, environment and check harness

**Files:**
- Create: `requirements.in`, `requirements.txt`, `pytest.ini`, `Makefile`, `README.md`, `CHANGELOG.md`
- Create: `config/rq1.yaml`, `config/screening.yaml`
- Create: `tools/common.py`, `checks/signoffs.py`, `checks/human_signoffs.csv`, `checks/check_setup.py`
- Test: `tests/test_common.py`, `tests/test_signoffs.py`

**Interfaces:**
- Produces:
  - `tools.common.load_config(name: str) -> dict` — reads `config/<name>.yaml`; expands `${VAR}` from env; raises `KeyError` naming a missing env var.
  - `tools.common.data_dir(*parts: str) -> pathlib.Path` — `$C2C_DATA/<parts>`, created if missing; raises `RuntimeError` if `C2C_DATA` unset.
  - `tools.common.record_versions(stage: str) -> None` — appends `date, stage, python, nimare, nilearn, nibabel, pandas, openai` to `results/versions.txt`.
  - `checks.signoffs.has_signoff(step: str, item: str) -> bool`; `checks.signoffs.missing(step: str, items: list[str]) -> list[str]`.
  - `checks/human_signoffs.csv` header: `date,step,item,who,result,note` (`result` ∈ `pass|error`).

- [ ] **Step 1:** `requirements.in`: `nimare~=0.22`, `nilearn~=0.14`, `nibabel`, `pandas`, `scikit-learn`, `openai`, `pypdf`, `pyyaml`, `requests`, `matplotlib`, `pytest`. Run `uv venv --python 3.12 && uv pip compile requirements.in -o requirements.txt && uv pip sync requirements.txt`. Expected: install succeeds (needs ~1 GB free; if the internal disk is full, create the venv on the external drive and symlink `.venv`).
- [ ] **Step 2:** `pytest.ini` with `pythonpath = .` and `testpaths = tests`.
- [ ] **Step 3: Write failing tests**
  - `test_load_config_expands_env`: write a temp yaml `{a: "${X}"}`, set `X=1` → `{"a": "1"}`.
  - `test_load_config_missing_env_raises`: unset var → `KeyError` whose message contains the var name.
  - `test_data_dir_requires_env`: `C2C_DATA` unset → `RuntimeError`.
  - `test_signoffs`: temp CSV with one row `step=s,item=a` → `has_signoff("s","a")` is True, `missing("s",["a","b"]) == ["b"]`.
  (Tests point the modules at temp files via a `path` keyword argument defaulting to the real location.)
- [ ] **Step 4:** Run `pytest -q` → FAIL (modules missing). Implement. Run → PASS.
- [ ] **Step 5:** `config/screening.yaml`:
  ```yaml
  seed: 20261019
  human_exclude_sample: 0.20
  second_rater_sample: 0.20
  kappa_min: 0.6
  raters:
    gemini: {base_url: "https://generativelanguage.googleapis.com/v1beta/openai/", model: "gemini-2.5-flash", api_key_env: GEMINI_API_KEY}
    qwen:   {base_url: "http://localhost:11434/v1", model: "qwen2.5:7b-instruct", api_key_env: null}
  ```
  `config/rq1.yaml`: `seed`, `pubmed_query` (plan §8.1 step 3: fMRI AND (episodic OR recognition OR recall OR source memory) AND (retrieval OR remember), written out in PubMed syntax), `ale: {voxel_thresh: 0.001, cluster_alpha: 0.05, n_iters: 5000, n_cores: 1}`, `min_experiments: 20`, `hard_min_experiments: 17`, `h1b_min_per_group: 17`, `spotcheck_frac: 0.20`, `failsafe_counts: [10, 20, 40]`, `failsafe_n_iters: 1000`, `parcels: {md_url: "https://evlab.squarespace.com/s/allParcels-MD-HE197.nii", md_sha256: null}`.
- [ ] **Step 6:** `checks/check_setup.py`: asserts `C2C_DATA` is set and writable; `git config user.email` == `tanishahandoo2002@gmail.com`; `.git/hooks/commit-msg` exists and is executable; Ollama answers `GET /api/tags` and lists the configured model; if `GEMINI_API_KEY` is set, the configured Gemini model appears in the endpoint's model list (otherwise a warning). Each failure prints what to do.
- [ ] **Step 7:** `Makefile` targets now: `setup` (uv sync + `python -m checks.check_setup`), `test` (`pytest -q`). Later tasks add `rq1-search`, `rq1-screen`, `rq1-check-screen`, `rq1-extract-check`, `rq1`, `masks`, `all`.
- [ ] **Step 8:** `README.md`: title, one-paragraph summary, how to run (`make setup`, env vars), data-access list, and the AI-use disclosure sentence from plan §8.6 with κ as a placeholder `κ = [to be filled after screening]`. `CHANGELOG.md`: heading plus "Deviations from registrations, dated." Run `make test` → PASS.
- [ ] **Step 9: Commit** `git add -A && git commit -m "Add project foundation: environment, config, check harness"`

### Task 2: Publish to GitHub as tanishahandoo2002-afk

**Human gate:** Tanisha runs `gh auth login` (GitHub.com, HTTPS, browser) and confirms `gh auth status` shows `tanishahandoo2002-afk` as the active account.

- [ ] **Step 1:** `gh auth status` → active account is `tanishahandoo2002-afk`. If not, stop.
- [ ] **Step 2:** `gh repo create tanishahandoo2002-afk/convergence-to-consequence --public --source . --push --description "Meta-analytic episodic-retrieval network tested on 7T single trials and tDCS/tACS trials"`. Run `gh auth setup-git` first so the push uses her credentials.
- [ ] **Step 3: Verify** `gh api repos/tanishahandoo2002-afk/convergence-to-consequence/contributors --jq '.[].login'` → exactly `tanishahandoo2002-afk`. `git log --format='%an %ae%n%b' | grep -iE 'co-authored|generated with'` → no output.
- [ ] **Step 4:** Switch `gh` back to `vaibhav375` only if the user asks (`gh auth switch`).

### Task 3: PubMed search, record import and de-duplication

**Files:**
- Create: `tools/pubmed_search.py`, `tools/import_records.py`, `checks/check_search.py`
- Test: `tests/test_search.py`, `tests/fixtures/efetch_sample.xml`, `tests/fixtures/sample.ris`

**Interfaces:**
- Consumes: `load_config`, `record_versions`.
- Produces:
  - Record columns (all search/import outputs): `record_id, source, pmid, doi, title, abstract, year`. `record_id` = `pmid:<n>` if PMID else `doi:<doi>` else `src:<source>:<row>`.
  - `tools.pubmed_search.parse_efetch(xml: str) -> list[dict]`
  - `tools.pubmed_search.search(query: str, email: str, api_key: str | None) -> list[dict]` (esearch with `usehistory=y`, efetch in batches of 200, ≤ 3 requests/s without key).
  - `tools.import_records.read_ris(path) -> list[dict]` (tags `TI`/`T1`, `AB`, `DO`, `PY`/`Y1`, `AN` for PMID if present).
  - `tools.import_records.dedupe(records: list[dict]) -> tuple[list[dict], int]` — duplicate if same non-empty PMID, or same non-empty lower-cased DOI, or same normalised title (lowercase, alphanumerics only) **and** same year.
  - CLI `python -m tools.pubmed_search rq1` writes `rq1_map/search/pubmed_<YYYYMMDD>.csv`, appends `date,source,query,hits,file` to `rq1_map/search/search_log.csv`, then writes `rq1_map/search/records.csv` (all sources deduped) and appends `duplicates_removed` to the log.

- [ ] **Step 1: Write failing tests**
  - `test_parse_efetch`: fixture with 2 articles (one without abstract, one with DOI in `ArticleIdList`) → 2 dicts with expected pmid/doi/title/year; missing abstract → `""`.
  - `test_dedupe_empty_doi_not_merged`: two records with `doi=""`, different titles → both kept, removed = 0.
  - `test_dedupe_same_doi_case_insensitive`: `10.1/AB` vs `10.1/ab` → one kept, removed = 1.
  - `test_dedupe_title_needs_same_year`: same title, years 2010/2012 → both kept.
  - `test_read_ris`: fixture with 2 entries → titles, DOIs, years parsed.
- [ ] **Step 2:** `pytest tests/test_search.py -v` → FAIL. Implement (stdlib `xml.etree.ElementTree`, `requests`). Run → PASS.
- [ ] **Step 3:** `checks/check_search.py rq1`: every file in the log exists; each `pubmed_*.csv` row count equals the logged `hits`; `records.csv` has unique `record_id`, unique non-empty PMIDs and DOIs.
- [ ] **Step 4:** Makefile `rq1-search: python -m tools.pubmed_search rq1 && python -m checks.check_search rq1`. Live run (needs network and `NCBI_EMAIL`): `make rq1-search` → check passes; note the hit count.
- [ ] **Step 5: Commit** (code, fixtures, search log and CSVs: these hold only published metadata).

### Task 4: Dual-AI title/abstract screening

**Files:**
- Create: `tools/screen.py`, `rq1_map/screening/criteria.md`
- Test: `tests/test_screen.py`

**Interfaces:**
- Consumes: record columns (Task 3); `config/screening.yaml`.
- Produces:
  - `tools.screen.build_messages(criteria: str, record: dict) -> list[dict]` — system message = criteria + instruction to answer only JSON `{"decision": "include"|"exclude"|"unsure", "reason": "<one sentence>"}`; user message = title + abstract (abstract may be empty).
  - `tools.screen.parse_reply(text: str) -> dict | None` — accepts plain JSON or JSON inside a ``` fence; returns None if invalid or decision not in the three values.
  - `tools.screen.screen_record(client, model: str, messages: list[dict]) -> dict` — temperature 0; one retry on invalid JSON; then `{"decision": "unsure", "reason": "invalid reply"}`. API/network exceptions propagate (never converted to a decision).
  - `tools.screen.merge(a: pd.Series, b: pd.Series, seed: int, frac: float) -> pd.DataFrame` — index `record_id`; columns `gemini, qwen, merged, needs_human`. Rule: both include → include, needs_human True; both exclude → exclude, needs_human True for a seeded `frac` sample (rounded up) else False; anything else → unsure, needs_human True.
  - Decision log `rq1_map/screening/ai_<rater>.csv`: `record_id, rater, model, prompt_sha256, timestamp, decision, reason, raw`.
  - CLI `python -m tools.screen rq1 --stage title_abstract [--rater gemini|qwen]` — resumable (skips record_ids already in the log); writes `rq1_map/screening/merged.csv` when both logs cover all records.

- [ ] **Step 1:** `criteria.md`: plan §8.1 eligibility table verbatim, plus the four accepted contrast types.
- [ ] **Step 2: Write failing tests**
  - `test_parse_reply_plain`, `test_parse_reply_fenced` → dict; `test_parse_reply_bad_decision` (`"maybe"`) → None; `test_parse_reply_not_json` → None.
  - `test_screen_record_retries_then_unsure`: fake client returns `"nope"` twice → decision `unsure`, called exactly 2 times.
  - `test_screen_record_api_error_propagates`: fake client raises `RuntimeError` → raises; nothing returned.
  - `test_merge_rule`: 4 records (inc/inc, exc/exc, inc/exc, unsure/exc) → merged `include, exclude, unsure, unsure`.
  - `test_merge_exclude_sample_seeded`: 10 agreed excludes, frac 0.2 → exactly 2 needs_human; same seed → same 2 records.
  - `test_resume_skips_logged`: log already has record 1 → fake client called only for record 2.
  - `test_title_only_record`: abstract `""` → user message contains the title and no `None`.
- [ ] **Step 3:** `pytest tests/test_screen.py -v` → FAIL. Implement with `openai.OpenAI(base_url=..., api_key=...)` (Ollama: `api_key="ollama"`). Run → PASS.
- [ ] **Step 4:** Live smoke test on 5 records with each rater: `python -m tools.screen rq1 --stage title_abstract --rater qwen --limit 5` → 5 log rows with valid decisions. Then full runs.
- [ ] **Step 5: Commit** code, criteria, AI logs.

### Task 5: Human decisions, κ, PRISMA and the screening check

**Files:**
- Create: `tools/kappa.py`, `tools/prisma.py`, `checks/check_screening.py`
- Test: `tests/test_kappa_prisma.py`

**Interfaces:**
- Consumes: `merged.csv` (Task 4), `records.csv` and `search_log.csv` (Task 3).
- Produces:
  - Human file `rq1_map/screening/human_decisions.csv`: `record_id, stage (title_abstract|full_text), rater (author|second), decision (include|exclude), reason, date`. Second-rater sample list `second_rater_sample.csv` = seeded 20% of `records.csv`, created by `python -m tools.kappa rq1 --make-second-rater-sample` (refuses to overwrite).
  - `tools.kappa.kappa(a: pd.Series, b: pd.Series) -> tuple[float, int]` — Cohen's κ on shared index (unsure counts as its own category), and n overlap.
  - CLI writes `rq1_map/screening/kappa.csv`: `pair, kappa, n` for gemini–qwen, gemini–author, qwen–author, author–second.
  - `tools.prisma.counts(rq: str) -> dict` with keys `identified, duplicates_removed, screened, excluded_title_abstract, full_text_assessed, excluded_full_text, included`; `tools.prisma.draw(counts: dict, out: Path)` — matplotlib box diagram.

- [ ] **Step 1: Write failing tests**
  - `test_kappa_perfect` → 1.0; `test_kappa_known`: a=`[1,1,0,0]`, b=`[1,0,0,0]` → 0.5; `test_kappa_uses_overlap_only`: different indexes → n = overlap.
  - `test_prisma_reconciles`: synthetic files → `identified - duplicates_removed == screened`, `screened - excluded_title_abstract == full_text_assessed`, `full_text_assessed - excluded_full_text == included`.
- [ ] **Step 2:** Run → FAIL. Implement (`sklearn.metrics.cohen_kappa_score`). Run → PASS.
- [ ] **Step 3:** `checks/check_screening.py rq1`: every `needs_human` record has an author decision; every record in `second_rater_sample.csv` has a second-rater decision; if gemini–author or qwen–author κ < `kappa_min`, every record must have an author decision (message cites plan §12); PRISMA counts reconcile. Makefile `rq1-check-screen`.
- [ ] **Step 4: Commit.**

### Task 6: Full-text contrast proposal

**Files:**
- Modify: `tools/screen.py` (add full-text stage)
- Test: `tests/test_screen.py` (add)

**Interfaces:**
- Consumes: `screen_record`, PDFs at `$C2C_DATA/rq1/pdfs/<record_id with : replaced by _>.pdf`.
- Produces:
  - `tools.screen.pdf_text(path) -> str` (pypdf, all pages).
  - `tools.screen.parse_contrast(text: str) -> dict | None` — JSON `{"eligible": bool, "table": str, "contrast": str, "contrast_type": "success"|"recollection"|"familiarity", "n": int, "reason": str}`.
  - CLI `python -m tools.screen rq1 --stage full_text --rater gemini` writes `rq1_map/screening/contrast_proposals.csv`. Proposals only; coordinates are never requested from the model.

- [ ] **Step 1: Failing tests:** `test_parse_contrast_valid`; `test_parse_contrast_bad_type` → None; `test_parse_contrast_n_not_int` → None.
- [ ] **Step 2:** Run → FAIL → implement → PASS. Smoke test on one PDF.
- [ ] **Step 3: Commit.**

### Task 7: Extraction sheets, Sleuth import and extraction check

**Files:**
- Create: `rq1_map/experiments.csv`, `rq1_map/coordinates.csv` (headers only), `rq1_map/coords.py`, `rq1_map/import_sleuth.py`, `rq1_map/spotcheck.py`, `checks/check_rq1_extraction.py`
- Test: `tests/test_extraction.py`

**Interfaces:**
- Produces:
  - `experiments.csv` columns: `exp_id, study_id, doi, subject_group, table_or_figure, contrast, contrast_type, n, mean_age, space, source, contrast_verified_by`. `coordinates.csv`: `exp_id, x, y, z`.
  - `rq1_map.coords.to_mni(experiments: pd.DataFrame, coordinates: pd.DataFrame) -> pd.DataFrame` — returns coordinates with x, y, z in MNI; rows whose experiment `space == "TAL"` converted with `nimare.utils.tal2mni`.
  - `rq1_map.import_sleuth.read_sleuth(path) -> tuple[pd.DataFrame, pd.DataFrame]` — parses GingerALE text (`// Reference=`, `// Subjects=`, `// MNI`/`// Talairach` header, tab-separated foci, blank-line separated experiments) into the two sheets with `source="brainmap"` and empty `contrast_verified_by`.
  - `checks.check_rq1_extraction.validate(experiments, coordinates, cfg) -> tuple[list[str], list[str]]` — (errors, warnings).
  - `rq1_map.spotcheck.make_sample(experiments, seed, frac) -> list[str]` → `rq1_map/spotcheck_sample.csv` (refuses to overwrite).
  - Sign-off steps used: `rq1_spotcheck` (item = exp_id), `rq1_outlier_focus` (item = `exp_id:x,y,z`).

- [ ] **Step 1: Write failing tests**
  - `test_tal2mni_applied_only_to_tal`: one MNI and one TAL experiment → MNI row unchanged, TAL row changed.
  - `test_duplicate_subject_group_error`: two rows same `subject_group` → error message contains the group name.
  - `test_n_must_be_int_ge_5`: `n="24 (12F)"` and `n=3` → two errors.
  - `test_experiment_without_foci_error`.
  - `test_outside_brain_listed`: focus `(0,-20,10)` inside, `(90,0,0)` outside → only the outside one listed as needing `rq1_outlier_focus` sign-off.
  - `test_count_thresholds`: 16 exps → error; 18 → warning only; 20 → neither.
  - `test_unverified_contrast_error`: empty `contrast_verified_by` → error.
  - `test_spotcheck_error_requires_all`: any `rq1_spotcheck` row with `result=error` → every exp_id needs a sign-off.
  - `test_read_sleuth`: fixture with 2 experiments (one MNI, one Talairach) → 2 experiment rows, correct foci counts and spaces.
- [ ] **Step 2:** Run → FAIL. Implement (brain mask: `nilearn.datasets.load_mni152_brain_mask(resolution=2)`; a focus is outside if its voxel is 0 or off-grid). Run → PASS.
- [ ] **Step 3:** CLI `python -m checks.check_rq1_extraction` prints warnings, exits 1 on errors, and reports missing spot-check / outlier sign-offs. Makefile `rq1-extract-check`.
- [ ] **Step 4: Commit.**

### Task 8: ALE, cluster table and jackknife

**Files:**
- Create: `rq1_map/run_ale.py`, `checks/check_rq1_ale.py`
- Test: `tests/test_ale.py`

**Interfaces:**
- Consumes: `to_mni`, `validate`, `load_config("rq1")`.
- Produces:
  - `rq1_map.run_ale.build_dataset(experiments, coordinates_mni) -> nimare.dataset.Dataset` — one study per `exp_id`, `sample_sizes` metadata from `n`, space `mni152_2mm`.
  - `rq1_map.run_ale.run(dset, ale_cfg: dict, seed: int) -> nimare.results.MetaResult` — `ALE()` then `FWECorrector(method="montecarlo", voxel_thresh, n_iters, n_cores)`; seeds numpy before correction.
  - `CLUSTER_MAP = "z_desc-size_level-cluster_corr-FWE_method-montecarlo"` (assert present in `cres.maps`; if NiMARE renamed it, fail with the list of available keys).
  - `rq1_map.run_ale.cluster_table(cres) -> pd.DataFrame` — clusters at cluster-level p < .05: id, peak x/y/z, peak z, size mm³, Harvard-Oxford label at peak.
  - `rq1_map.run_ale.jackknife(cres) -> pd.DataFrame` — `nimare.diagnostics.Jackknife(target_image=CLUSTER_MAP)`; per cluster × experiment contribution.
  - Outputs in `rq1_map/results/`: `ale_stat.nii.gz`, `ale_cluster_fwe_z.nii.gz`, `clusters.csv`, `jackknife.csv`, `params.json` (config used + n experiments + nimare version).
  - CLI `python -m rq1_map.run_ale`; refuses to run if `validate` returns errors.

- [ ] **Step 1: Write failing known-answer tests** (n_iters=100, seed fixed)
  - `test_planted_cluster_found`: 25 synthetic experiments (n=20 each), 3 foci jittered ±4 mm around (-24,-18,-18) plus 5 random in-brain foci each → `cluster_table` non-empty and some cluster's extent contains (-24,-18,-18).
  - `test_noise_only_no_cluster`: 25 experiments of 8 random in-brain foci → `cluster_table` empty.
  - `test_jackknife_covers_all`: on the planted dataset, jackknife has a column per experiment.
- [ ] **Step 2:** Run `pytest tests/test_ale.py -v` → FAIL. Implement. Run → PASS (expect minutes, not seconds).
- [ ] **Step 3:** `checks/check_rq1_ale.py`: output files exist; `params.json` ALE values equal config; jackknife covers every exp_id; `results/versions.txt` has an `rq1_ale` row. An empty cluster table is reported, not failed.
- [ ] **Step 4:** Makefile `rq1: rq1-extract-check` → `python -m rq1_map.run_ale && python -m checks.check_rq1_ale`.
- [ ] **Step 5: Commit.**

### Task 9: Fail-safe N and the H1b subtraction

**Files:**
- Modify: `rq1_map/run_ale.py`
- Test: `tests/test_ale.py` (add)

**Interfaces:**
- Produces:
  - `rq1_map.run_ale.noise_experiments(k: int, template_n: list[int], foci_per_exp: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]` — k experiments with random in-brain foci, sample sizes drawn from the real `n` values.
  - `rq1_map.run_ale.failsafe(experiments, coordinates_mni, clusters, cfg) -> pd.DataFrame` — for each count in `failsafe_counts`, adds that many noise experiments, reruns with `failsafe_n_iters`, records per original cluster whether its peak is still inside a significant cluster. Output `failsafe.csv`. Code comment: `# Simplification: fixed counts, not a search for the exact break point; add bisection if a reviewer asks for an exact FSN.`
  - `rq1_map.run_ale.h1b(experiments, coordinates_mni, cfg) -> str` — if recollection and familiarity groups each ≥ `h1b_min_per_group`, runs `ALESubtraction` (n_iters from config) and writes `h1b_subtraction_z.nii.gz`; otherwise writes `h1b_status.txt` = `not run: recollection k=…, familiarity k=…` and returns that text.

- [ ] **Step 1: Failing tests:** `test_noise_experiments_in_brain` (all foci inside mask, k rows, seeded reproducible); `test_h1b_gate`: 10 + 20 experiments → status starts with `not run` and names both k values.
- [ ] **Step 2:** Run → FAIL → implement → PASS. Wire both into the `rq1_map.run_ale` CLI; check script requires `failsafe.csv` and either the subtraction map or `h1b_status.txt`.
- [ ] **Step 3: Commit.**

### Task 10: Masks and the freeze

**Files:**
- Create: `masks/build_masks.py`, `checks/check_masks.py`
- Test: `tests/test_masks.py`

**Interfaces:**
- Consumes: `rq1_map/results/ale_cluster_fwe_z.nii.gz`, `ale_stat.nii.gz`; config `parcels`.
- Produces (all in MNI 2 mm, `masks/`):
  - `memory.nii.gz` = cluster-FWE map > 0; `memory_top50.nii.gz` = memory voxels with ALE stat ≥ median ALE stat within memory; `control_md.nii.gz` = MD parcels (`allParcels-MD-HE197.nii`, any parcel > 0, resampled nearest-neighbour) minus memory; `control_yeo.nii.gz` = Yeo 2011 7-network (thick) networks 4 (ventral attention) and 6 (frontoparietal) minus memory.
  - `masks/FROZEN.sha256` in `sha256sum` format; `masks/sources.csv` (`file, url, sha256, date`).
  - `masks.build_masks.top_half(stat_img, mask_img) -> Nifti1Image`; `subtract(a_img, b_img) -> Nifti1Image`; `freeze(paths: list[Path], refreeze: bool) -> None`; `verify_frozen() -> list[str]` (names of files whose hash differs or is missing).
  - `freeze` raises `RuntimeError` if `FROZEN.sha256` exists and `refreeze` is False; with `refreeze=True` requires a `CHANGELOG.md` line starting with today's date (`YYYY-MM-DD`).

- [ ] **Step 1: Failing tests** (synthetic 10×10×10 images)
  - `test_top_half_at_most_half`: voxel count ≤ ceil(n/2) and ⊆ mask.
  - `test_subtract_disjoint`: result ∩ b is empty.
  - `test_freeze_refuses_second_run`; `test_refreeze_requires_changelog_today`.
  - `test_verify_detects_change`: modify one byte after freezing → its name returned.
- [ ] **Step 2:** Run → FAIL → implement → PASS. Download the MD parcels file, record its sha256 in `config/rq1.yaml` and `masks/sources.csv`; later runs verify that hash.
- [ ] **Step 3:** `checks/check_masks.py`: each mask binary, non-empty, inside the MNI brain mask; memory ∩ control_md = memory ∩ control_yeo = ∅; `verify_frozen()` empty; a `masks_frozen` sign-off row exists. Makefile `masks: python -m masks.build_masks && python -m checks.check_masks`; `all: test rq1 masks`.
- [ ] **Step 4: Human gate:** Tanisha views the masks over the MNI template (`nilearn.plotting.plot_roi`, PNGs written to `masks/qc/`) and adds the `masks_frozen` sign-off. Masks are uploaded with registration 2.
- [ ] **Step 5: Commit** masks, hashes, QC images.

---

## Not in this plan

R environment (`renv.lock`) and SimNIBS setup move to the RQ2 and RQ3 plans, where they are first needed. Spec §5 lists them under `make setup`; `check_setup` gains those checks then.
