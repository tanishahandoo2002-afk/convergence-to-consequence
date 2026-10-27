# Decisions (2026-10-27): proposed, then agreed in full

These were prepared on request by an AI assistant, using the judgement a neuroimaging meta-analyst would apply. They were **proposals** until the author agreed to all of them, without changes, on 2026-10-27. The pipeline enforces this, because every extraction row needs `contrast_verified_by` filled in by her. Code changes some of them need are listed but not yet made.

## 1. BrainMap eligibility review (RQ1)

**Searches.** Run separately, then combined:
- Context = Normal Mapping;
- Diagnosis = Normals;
- Behavioral Domain = Cognition.Memory.Explicit;
- Paradigm Class = one of Cued Explicit Recognition/Recall, Paired Associate Recall, Free List Word Recall.

Vocabulary version 706, 2026-10-27. Together they matched 471 contrasts in 96 papers.

**Review.** One decision per contrast, in `rq1_map/brainmap_review_proposed.csv`:

| Decision | Contrasts | Studies | Used in |
| --- | --- | --- | --- |
| S: retrieval success (hits > CR, hits > misses, old > new at test, block-level retrieval success) | 14 | | main map |
| R: recollection (remember > know, source correct > incorrect, recollection > familiarity, remember-hits > CR) | 21 | 16 | main map and H1b (recollection) |
| F: familiarity (know > new, familiarity-strength effects, item-only hits > misses) | 9 | 8 | H1b (familiarity) only |
| X: excluded | 427 | | |
| **Main map (S + R)** | **35** | **26** | |

**Why contrasts were excluded:** retrieval vs baseline, rest or a control task; encoding or subsequent-memory effects; reverse-direction contrasts; task or material comparisons; emotion effects; semantic, working-memory or famous-face tasks; hits vs false alarms; patient groups; n < 5; or a label too vague to judge.

**21 contrasts are marked `verify_in_paper`.** For each, the label alone doesn't settle the eligibility question, for example whether "old > new" uses correct trials only, or whether a "retrieval success" contrast is trial-level or a block design. The author checks these against the papers.

**Reviewed workspaces for Sleuth.** These keep only the chosen contrasts, so the export pools only eligible foci for each subject group:
- `/Volumes/C2C/reviewed_main.work`
- `/Volumes/C2C/reviewed_recollection.work`
- `/Volumes/C2C/reviewed_familiarity.work`

To apply: open each in Sleuth and export it (GingerALE text, Talairach as before) under the same name with a `.txt` extension.

**Consequence for H1b.** BrainMap gives 16 recollection and 8 familiarity studies. Unless the PubMed top-up adds at least 9 familiarity studies, H1b doesn't run under its 17-per-group rule, and that is reported as such.

## 2. PubMed top-up starts in 2008

- **Evidence:** BrainMap's matched papers number 5–12 a year from 1998 to 2008, then 2 (2009), 1 (2010) and 2 (2012). Its eligible studies end in 2008. So the top-up covers 2008 onward, with the 2008 overlap kept deliberately.
- **Size:** 1,309 PubMed records from 2008 onward (1,683 for all years), on 2026-10-27.
- **Overlap:** papers found by both BrainMap and PubMed are matched by author, year and title at the full-text stage, and counted once.

## 3. Criteria wording (`rq1_map/screening/criteria.md`)

Keep the eligibility table, and add the three interpretation rules this review needed. They are already written into `criteria.md`, and are easy to revert if she disagrees:
- **Retrieval phase only:** "remembered > forgotten" counts only when measured at retrieval. Subsequent-memory effects are encoding.
- **Hits > false alarms is excluded.** It contrasts true and false memory, not successful and unsuccessful retrieval.
- **Block-level designs are eligible:** retrieval-success designs that manipulate target density across blocks count as success contrasts, are flagged, and are tested in a sensitivity analysis that leaves them out.

## 4. The four design decisions

**4.1 One experiment per subject group, and H1b.**
- *Proposed:* strict pooling for the main map; for H1b, a group may give one recollection and one familiarity experiment, from the separate recollection and familiarity workspaces.
- *Why:* the two H1b maps are estimated separately, so a group appearing in both doesn't double-count within either map.
- *Code change:* H1b reads its own two extraction sheets, instead of filtering one sheet by `contrast_type`.

**4.2 Crossover effect size (RQ3).**
- *Proposed:* standardise crossover effects by the raw-score SD pooled across conditions (metafor `SMCRP`, i.e. d_av), not the change-score SD (`SMCC`). The assumed correlation r (.5, with .3 and .7 as sensitivity values) still enters the sampling variance.
- *Why:* SMCC inflates crossover g by 1/√(2(1−r)) relative to between-group g (×1.29 at r = .7). Pooling it with parallel-design effects would bias any moderator that differs between designs (Morris & DeShon, 2002).
- *Code change:* `rq3_stimulation/effect_sizes.R`.

**4.3 H2b model form (RQ2).**
- *Proposed:* fit H2b in wide form, `correct ~ z_memory + z_control + random effects`, and test β_memory − β_control with a Wald test. Do not stack each trial twice.
- *Why:* it tests the same hypothesis, without duplicated rows that make the interaction's standard error too small. Each signal is still z-scored within participant, so the comparison doesn't depend on scale.
- *Code change:* `rq2_nsd/models.R`.

**4.4 Centring the delay in H2c (RQ2).**
- *Proposed:* centre `log_delay_s` at the median log delay of old trials, pooled across participants and fixed from the data before modelling.
- *Why:* the memory-signal main effect then means the effect at a typical delay rather than at 1 s, and centring avoids rescaling warnings that would force needless simplification.
- *Code change:* `rq2_nsd/models.R`.

## 5. Other open items

| Item | Proposed |
| --- | --- |
| How H1a is judged | A significant cluster overlaps the Harvard-Oxford hippocampus; precuneous/posterior cingulate/angular gyrus; frontal medial/paracingulate (≥1 voxel), each region reported separately |
| Familiarity contrasts | H1b only, never the main map |
| Languages | English only, stated as a limitation |
| Scopus | Added if Amity library access allows; otherwise PubMed only, stated |
| H1b subtraction threshold | Voxel-level p < .001, minimum cluster 200 mm³, labelled exploratory |
| Second rater; authors | The author's decision |

## Sign-off

**Agreed: all proposals in sections 1–5, without changes.** Date: 2026-10-27. Any later change goes in `CHANGELOG.md`.

## Applied so far (2026-10-27)

- **The review is in the data.** The reviewed contrasts were exported from Sleuth with every ineligible contrast hidden: `/Volumes/C2C/reviewed_{main,recollection,familiarity}_v2.txt`. Each file holds exactly the reviewed contrasts: 35 main (26 subject groups, 397 foci); 21 recollection (16 groups, 276 foci); 9 familiarity (8 groups, 76 foci).
- **Main map in the sheets.** The main export is imported into `rq1_map/experiments.csv` and `coordinates.csv`. `contrast_type` is pre-filled from the review (14 recollection, 12 success). `contrast_verified_by` is blank until the author checks each row.
- **Johnson S C, 2006: resolved.** N = 77 is right: it is the healthy reference group. The 14 in the review was the age-matched control group. See `docs/paper-check-rq1.md`.
- **Still open for the author:** the 7 foci outside the brain mask; and drawing the 20% spot-check sample once the set is final.
