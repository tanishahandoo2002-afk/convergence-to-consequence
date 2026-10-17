# RQ2 + RQ3 Pre-Data Implementation Plan

> Execution: task by task, in order. Steps use checkbox (`- [ ]`) syntax. Each task ends with its tests passing and a commit.

**Goal:** Everything in RQ2 and RQ3 that can be built and verified before data access arrives: the R environment, NSD trial labelling and session extraction (on synthetic data), the RQ2 models, the RQ3 search/screening setup, effect sizes and the RQ3 meta-regression, each with known-answer tests.

**Architecture:** Same pattern as plan 01: plain scripts, a check after every stage, Makefile targets. R code lives in one file per analysis with functions plus a `main()` that runs only when the script is called with `--run`; R tests `source()` the file and use `stopifnot`. NSD access is behind one injectable `fetch(key) -> bytes` function so tests never touch the network.

**Tech Stack:** Python (existing venv: nibabel, numpy, pandas, scipy), R 4.5 with renv (lme4, metafor, clubSandwich, robvis).

**Spec:** `docs/design.md` §9 (RQ2), §10 (RQ3). Research definitions: plan §8.2, §8.3.

## Global Constraints

- Commits authored `Tanisha Handoo <tanishahandoo2002@gmail.com>`, no AI attribution lines.
- No NSD file is downloaded until Tanisha has submitted the NSD Data Access Agreement form. All RQ2 tests use synthetic data.
- `responses.tsv` column names are not publicly documented; they live in `config/rq2.yaml` and `check_rq2` fails with the list of real columns if they differ.
- Betas: `nsddata_betas/ppdata/subjNN/func1pt8mm/<beta_dir>/betas_sessionSS.nii.gz`, int16 with value = percent signal change × 300, 750 trials per session. b3 = `betas_fithrf_GLMdenoise_RR`, b2 = `betas_fithrf`.
- Per-voxel z-scoring within session is done on mask voxels only (z-scoring is voxel-wise, so this is exact and keeps RAM low).
- RQ2 model simplification order: `(1 + x | subject)` → `(1 + x || subject)` → `(1 | subject)` → drop `(1 | image)`.
- RQ3 effect sizes: parallel = Hedges' g (`escalc("SMD")`); crossover = change-score SMD (`escalc("SMCC")`) at r = .5, sensitivity .3 and .7; sign so positive = better memory.
- RQ3 model: `rma.mv(yi, vi, random = ~ 1 | study_id/es_id)`, CR2 robust tests via clubSandwich; number of sessions is a covariate in every model.
- Checks test process, never results.

## Review Focus

1. **Session with missing responses or a missing run** (fewer than 750 rows): the check fails naming subject/session; extraction never silently mis-aligns betas and labels. Test in Task 3.
2. **Image seen for the first time in a later session vs within session:** viewing number and delay are computed across the participant's whole history, not per session. Test in Task 2.
3. **A trial whose mask voxels are all zero / NaN** (edge of FOV): mean is NaN, flagged in the data-quality report, not converted to 0. Test in Task 3.
4. **Effect reported only as t (parallel design):** converted, not dropped; a row with neither means/SDs nor t is an error. Test in Task 7.
5. **Model that fails to converge at every simplification step:** recorded as failed in the results table, not stopping the other models. Test in Task 5.

---

### Task 1: R environment and R test runner

**Files:** Create `renv.lock`, `.Rprofile` (renv activate), `tests/R/run_all.R`; Modify `Makefile`, `checks/check_setup.py`, `.gitignore` (add `renv/library/`, `renv/staging/`)

- [ ] **Step 1:** `Rscript -e 'install.packages("renv"); renv::init(bare=TRUE)'` then `renv::install(c("lme4","metafor","clubSandwich","robvis","jsonlite"))` and `renv::snapshot()`. Expected: `renv.lock` lists the five packages.
- [ ] **Step 2:** `tests/R/run_all.R` sources every `tests/R/test_*.R` and exits non-zero on the first error, printing `R tests: N files passed`.
- [ ] **Step 3:** Makefile `test`: `.venv/bin/pytest -q && Rscript tests/R/run_all.R`. `check_setup` adds: `Rscript -e 'library(lme4); library(metafor); library(clubSandwich)'` succeeds.
- [ ] **Step 4:** `make test` → pytest passes, R runner prints `0 files passed`. Commit.

### Task 2: NSD trial labels

**Files:** Create `config/rq2.yaml`, `rq2_nsd/labels.py`; Test `tests/test_rq2_labels.py`

**Interfaces — Produces:**
- `config/rq2.yaml`: `seed`, `subjects: [1..8]`, `beta_dirs: {b3: betas_fithrf_GLMdenoise_RR, b2: betas_fithrf}`, `trials_per_session: 750`, `s3_base: https://natural-scenes-dataset.s3.amazonaws.com/`, `extreme_z: 6`, `pilot: {subject: 1, sessions: [1, 2, 3]}`, `behav_columns: {session: SESSION, run: RUN, trial: TRIAL, image: 73KID, time: TIME, is_old: ISOLD, is_correct: ISCORRECT, rt: RT, missing: MISSINGDATA, memory_recent: MEMORYRECENT}` with a comment that names must be checked against the Data Manual.
- `rq2_nsd.labels.label_trials(behav: pd.DataFrame, cols: dict) -> pd.DataFrame` — input: one participant's full `responses.tsv`. Output columns: `session, run, trial, image, viewing (1-3), is_old (0/1), response_old (0/1 or NA), outcome (hit|miss|fa|cr|NA), rt, log_delay_s (NA for first viewing), memory_recent`. Rows sorted chronologically (session, run, trial). `viewing` and `log_delay_s` computed over the whole participant history by image; `time` is a MATLAB datenum (days), delay = (t − t_prev) × 86400 s, `log_delay_s = log10(delay)`. Missing response (missing flag 1 or rt NA) → `response_old`, `outcome` = NA.
- Outcome rule: is_old & correct → hit; is_old & !correct → miss; !is_old & !correct → fa; !is_old & correct → cr.

- [ ] **Step 1: Failing tests**
  - `test_outcomes`: 4 rows covering the four (is_old, is_correct) combinations → `hit, miss, fa, cr`; `response_old == [1, 0, 1, 0]`.
  - `test_viewing_and_delay_across_sessions`: image 5 shown in session 1 (time 100.0), session 1 again (100.0 + 60/86400), session 3 (110.0) → viewing `[1, 2, 3]`; `log_delay_s` `[NA, log10(60), log10(10*86400 − 60)]` within 1e-6.
  - `test_missing_response`: missing flag 1 → outcome NA, viewing still counted.
  - `test_chronological_order`: shuffled input rows → output sorted by session, run, trial.
- [ ] **Step 2:** Run → FAIL. Implement. Run → PASS. Commit.

### Task 3: Session extraction (streamed, synthetic-tested)

**Files:** Create `rq2_nsd/extract_trials.py`, `checks/check_rq2.py`; Test `tests/test_rq2_extract.py`

**Interfaces:**
- Consumes: `label_trials`, `load_config`, `data_dir`, `masks.build_masks.verify_frozen`.
- Produces:
  - `rq2_nsd.extract_trials.fetch(url: str) -> bytes` — HTTPS GET, streamed into memory, raises on non-200.
  - `rq2_nsd.extract_trials.decode_betas(gz_bytes: bytes) -> nib.Nifti1Image` — gunzip in memory, `Nifti1Image.from_bytes`.
  - `rq2_nsd.extract_trials.mask_means(betas_img, masks: dict[str, np.ndarray]) -> pd.DataFrame` — per mask: take mask voxels (n_vox × n_trials) as float32, divide by 300, z-score each voxel across trials (ddof=0; zero-variance voxels → NaN), mean over voxels ignoring NaN (all-NaN → NaN). Columns `sig_<mask>`; one row per trial in volume order. Also column `n_vox_<mask>` = voxels with finite z.
  - `rq2_nsd.extract_trials.extract_session(subject: int, session: int, labels: pd.DataFrame, masks: dict, beta: str, cfg: dict, fetch=fetch, pilot: bool = False) -> pd.DataFrame` — asserts the session has exactly `trials_per_session` label rows and volumes; joins trial means to labels by order; adds `subject, session, beta`. With `pilot=True` drops `is_old, response_old, outcome, rt, log_delay_s, viewing, memory_recent` before returning.
  - `rq2_nsd.extract_trials.write_session(df, out_dir: Path, subject, session, manifest: Path, key: str)` — writes `subjNN_sessSS.csv` via temp file + `os.replace`; appends `subject, session, key, n_trials, timestamp` to the manifest.
  - CLI `python -m rq2_nsd.extract_trials --beta b3 [--subjects 1 2] [--pilot]`: verifies frozen masks, loads native masks from `$C2C_DATA/rq2/native_masks/subjNN_<mask>.nii.gz`, skips sessions already in the manifest, writes to `$C2C_DATA/rq2/<beta>/` (pilot: `$C2C_DATA/rq2/pilot/`). Native-mask creation (nsdcode) is deferred to the data-access plan.
  - `checks.check_rq2.check_tables(out_dir: Path, cfg) -> tuple[list[str], pd.DataFrame]` — errors and a data-quality table (per subject/session: n trials, n missing responses, n NaN signal, n |sig| > `extreme_z`).

- [ ] **Step 1: Failing tests** (synthetic 4×4×4×750 int16 volume, gzip-compressed bytes, fake fetch returning them)
  - `test_decode_roundtrip`: decode(gzip(img bytes)) has the same data.
  - `test_mask_means_zscored`: a voxel with values 300·[1,2,3,…] → z-scored mean per trial equals the closed-form z; constant voxel → excluded (n_vox drops by 1).
  - `test_all_nan_trial_mean_is_nan`: mask whose only voxel is constant → `sig_` all NaN (not 0).
  - `test_extract_session_rejects_wrong_trial_count`: labels with 749 rows → `ValueError` naming subject and session.
  - `test_pilot_drops_outcomes`: pilot output has none of the outcome columns, has `sig_memory`.
  - `test_write_session_atomic_and_manifest`: file exists, no `.tmp` left, manifest has one row; second write of same session appends nothing if skipped by the CLI check helper `done_sessions(manifest) -> set[tuple[int,int]]`.
  - `test_check_tables_quality_report`: two synthetic session files, one with 3 NaN signals → report row shows 3; a 749-row file → error.
- [ ] **Step 2:** Run → FAIL. Implement. Run → PASS. Makefile `rq2-pilot`, `rq2` (extract + `python -m checks.check_rq2`). Commit.

### Task 4: Behaviour-file check (columns and alignment)

**Files:** Modify `checks/check_rq2.py`; Test `tests/test_rq2_labels.py` (add)

**Interfaces — Produces:** `checks.check_rq2.check_behaviour(behav: pd.DataFrame, cols: dict, expected_images: pd.Series | None) -> list[str]`:
- every configured column exists (else one error listing the real columns);
- each session has `trials_per_session` rows;
- if `expected_images` (73k ids from the experimental design, chronological) is given, they equal the `image` column row by row (first mismatch reported);
- for within-session repeats, Spearman ρ between computed delay and `memory_recent` ≥ 0.9.

- [ ] **Step 1: Failing tests:** `test_missing_column_lists_real_columns`; `test_image_order_mismatch_reported` (swap two rows → error names the first mismatching trial); `test_delay_agrees_with_memory_recent` (consistent synthetic → no error; reversed memory_recent → error).
- [ ] **Step 2:** Run → FAIL → implement → PASS. Commit.

### Task 5: RQ2 models (R) with known-answer tests

**Files:** Create `rq2_nsd/models.R`; Test `tests/R/test_rq2_models.R`

**Interfaces — Produces (R functions):**
- `fit_simplified(formulas: list, data, family = binomial)` — tries each formula in order with `glmer` (control `bobyqa`, maxfun 2e5); a fit counts as converged when it has no convergence warning and is not singular in the slope term. Returns `list(fit, formula_used, converged)`; if all fail, `fit = NULL, converged = FALSE`.
- `h2_formulas(outcome, terms)` — the four-step list from Global Constraints, e.g. for H2a `hit ~ sig_memory + (1 + sig_memory | subject) + (1 | image)` … `hit ~ sig_memory + (1 | subject)`.
- `fit_h2(trials)` — H2a on old trials (`hit` = outcome == hit); H2b on trials answered old, long format over `network ∈ {memory, control_md}`, `correct ~ sig * network`; H2c `hit ~ sig_memory * log_delay_s` on old trials with a delay. Pooled and per participant (per participant drops the subject terms). Returns a data frame `model, subject (all|1..8), term, estimate, se, or, ci_low, ci_high, p, formula_used, converged`.
- `robustness(trials)` — H2a refit (a) leaving out each participant in turn, (b) with `sig_memory_top50` in place of `sig_memory`, and H2b refit (c) with `control_yeo` in place of `control_md`. Same output columns plus `variant`. The b2-vs-b3 comparison is the same functions run on the b2 tables.
- `perm_test(trials, n_perm, seed)` — per participant: fixed-effects logistic slope of hit on `sig_memory` (old trials); labels shuffled within session; p = (1 + #(|perm| ≥ |obs|)) / (n_perm + 1).
- `main()` with `--run --input <dir> --output rq2_nsd/results/`: reads all session CSVs, runs everything, writes `h2_results.csv`, `permutation.csv`.

- [ ] **Step 1: Failing R tests** (simulate 8 subjects × 1,500 trials, 2,000 images, subject and image random intercepts, subject slope SD 0.1, `seed 1`)
  - `planted`: true H2a slope 0.4 → pooled estimate's 95% CI contains 0.4 and excludes 0.
  - `null`: slope 0 → CI contains 0.
  - `h2c`: planted interaction −0.2 → CI contains −0.2.
  - `all_fail`: a formula list containing only a nonsense random term on a 1-level factor → `converged == FALSE`, no error thrown, other models still returned.
  - `lopo`: `robustness()` returns 8 leave-one-out H2a rows plus the top-50% and Yeo variants.
  - `perm`: planted data with n_perm 200 → p < 0.05 for all subjects; null → p > 0.01 for most (≥ 6 of 8).
- [ ] **Step 2:** Run `Rscript tests/R/run_all.R` → FAIL. Implement. Run → PASS. Commit.

### Task 6: RQ3 search and screening setup

**Files:** Create `config/rq3.yaml`, `rq3_stimulation/screening/criteria.md`; Modify `Makefile`

- [ ] **Step 1:** `config/rq3.yaml`: `seed`, `pubmed_query` (tDCS/tACS × episodic memory outcomes × sham, from plan §8.3 step 3, marked draft), `r_values: {primary: 0.5, sensitivity: [0.3, 0.7]}`, `min_clinical_trials: 8`.
- [ ] **Step 2:** `criteria.md`: plan §8.3 step 2 eligibility verbatim plus the exclusions.
- [ ] **Step 3:** Makefile `rq3-search`, `rq3-screen`, `rq3-check-screen` mirroring the RQ1 targets with `rq3`. Smoke: query hit count via esearch only (not committed). Commit.

### Task 7: RQ3 effect sizes (R) and extraction check

**Files:** Create `rq3_stimulation/effects.csv`, `rq3_stimulation/montages.csv`, `rq3_stimulation/rob2.csv` (headers), `rq3_stimulation/effect_sizes.R`, `checks/check_rq3_extraction.py`; Test `tests/R/test_rq3_effect_sizes.R`, `tests/test_rq3_extraction.py`

**Interfaces — Produces:**
- `effects.csv` columns: `es_id, study_id, population (healthy|MCI|AD), diagnostic_criteria, design (parallel|crossover), stim (tDCS|tACS), montage_id, timing (encoding|retrieval|offline), sessions, test_name, test_type (recall|recognition|source), followup_days, n_active, n_sham, m_active, sd_active, m_sham, sd_sham, t_value, higher_is_better (1|0), reported_g, extracted_by, checked_by`.
- `montages.csv`: `montage_id, anode, cathode, other_electrodes, size_cm2, current_mA, type`. `rob2.csv`: `study_id, d1_randomisation, d1b_carryover, d2_deviations, d3_missing, d4_measurement, d5_selection, overall` with values `low|some|high` (`d1b` only for crossover).
- R `compute_es(effects, r)` → adds `yi, vi`: parallel with means/SDs → `escalc("SMD")`; parallel with only `t_value` → `d = t·sqrt(1/n1 + 1/n2)`, Hedges-corrected, `vi` from the SMD formula; crossover → `escalc("SMCC", m1i=active, m2i=sham, sd1i, sd2i, ni=n_active, ri=r)`; sign flipped when `higher_is_better == 0`.
- `checks.check_rq3_extraction.validate(effects, montages, rob2) -> tuple[list[str], list[str]]`: schema/enums; SD > 0; each row has means+SDs or t; crossover rows have `n_active == n_sham`; every `montage_id` exists; every study has a complete RoB 2 row (`d1b` required for crossover studies); `checked_by` non-empty on ≥ 20% of rows.

- [ ] **Step 1: Failing tests**
  - R `hedges_parallel`: m 10 vs 9, SD 2/2, n 20/20 → g = 0.4901 (± 1e-4).
  - R `direction`: same with `higher_is_better = 0` → g = −0.4901.
  - R `t_only`: t = 1.5811, n 20/20 → g = 0.4901 (± 1e-3).
  - R `crossover_r_changes_vi`: vi at r .7 < vi at r .3.
  - Python: `test_row_without_means_or_t_error`; `test_unknown_montage_error`; `test_crossover_needs_d1b`; `test_checked_by_20_percent`.
- [ ] **Step 2:** Run → FAIL → implement → PASS. Commit.

### Task 8: RQ3 meta-regression (R) with known-answer tests

**Files:** Create `rq3_stimulation/models.R`; Test `tests/R/test_rq3_models.R`

**Interfaces — Produces:**
- `fit_rq3(es, fields)` — merges `fields.csv` (`montage_id, head_model, field_map, field_control`) on montage (head model `ernie`), fits H3a `~ field_map + sessions`, H3b `~ field_map + field_control + sessions` with `Wald_test(constraints = constrain_equal(c("field_map","field_control")), vcov = "CR2")`, H3c `~ test_type + sessions`, H3d `~ field_map * group + sessions` (`group = healthy` vs `clinical`), skipped with a reason if clinical studies < `min_clinical_trials`. Returns `model, term, estimate, se, ci_low, ci_high, p_cr2, k_effects, k_studies, note`.
- `bias(es)` — PET (`~ sqrt(vi)`), PEESE (`~ vi`), multilevel Egger (`sqrt(vi)` as moderator in `rma.mv`), leave-one-study-out estimates; funnel plot to `results/funnel.png`.
- `main()` with `--run`: r = .5 primary, re-run for .3 and .7, writes `rq3_stimulation/results/`, and draws the RoB 2 traffic-light and summary plots from `rob2.csv` with robvis (`rob_traffic_light`, `rob_summary`, tool `"ROB2"`).

- [ ] **Step 1: Failing R tests** (simulate 30 studies, 1–3 effects each, `field_map ~ U(0.05, 0.4)`, `field_control` independent, true g = 0.1 + 1.0·field_map, study SD 0.1, within SD 0.05)
  - `h3a_planted`: field_map CI contains 1.0 and excludes 0.
  - `h3b_difference`: Wald test p < 0.05 (true control slope 0).
  - `h3d_skipped`: only 5 clinical studies → H3d row has note `skipped: 5 clinical studies < 8`.
  - `egger_null`: no small-study effect simulated → multilevel Egger slope CI contains 0.
- [ ] **Step 2:** Run → FAIL → implement → PASS. Commit.

### Task 9: Wiring and README

- [ ] Makefile `rq3-es`, `rq3` (effect sizes + extraction check + models); `all` extended with `rq2`, `rq3`. README "How to run" lists the new targets and the R requirement. `make test` → all Python and R tests pass. Commit.

---

## Deferred to the data-access plan

Native masks via nsdcode (needs NSD transform files); the real pilot and full extraction; the experimental-design file reader feeding `check_behaviour(expected_images=…)`; SimNIBS field modelling (needs several GB of disk on the external drive); `integration.R` (needs both result sets).
