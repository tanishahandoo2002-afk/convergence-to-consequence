# Changelog

Deviations from the protocol (`docs/registration-1-rq1.md`) and from the project plan, dated (YYYY-MM-DD), with the reason for each.

## 2026-11-07: full-text proposals read from PMC instead of PDFs (RQ1)

**Was:** asi1-mini proposed the contrast table and N from PDFs stored in `$C2C_DATA/rq1/pdfs`.

**Now:** a stored PDF is still used if there is one. Otherwise the text comes from PMC's open-access XML through NCBI's API, and it is read and not saved. This gave text for 136 of the 290 records. The other 154 are listed in `rq1_map/screening/full_text_not_retrieved.csv`.

**Why:** no PDFs exist and the team does not want stored copies. Publisher sites show bot checks, which are not bypassed.

**Results:** `rq1_map/screening/contrast_proposals.csv` holds 86 proposed eligible, 49 proposed ineligible and 1 invalid reply (`pmid:28803854`, a malformed key in an otherwise readable reply, left for the author).

**Limits:**
- These are proposals from a model not calibrated on full texts. Several proposed contrasts do not look eligible from their labels alone. Nothing has been entered in `experiments.csv`.
- The accepted bulk yes covers title/abstract only. It does not verify any contrast, and `contrast_verified_by` stays blank until the author confirms each one against its paper.
- The team decided to count the 154 records with no text as "reports not retrieved". No one will seek them through a library or the authors, and PRISMA reports them as their own count. They are not assessed, so an eligible study among them is lost to the map.
- Open-access papers are not a random subset. Availability can track journal, funder and year, so the map may not represent the whole literature, and more than half of the records sought were not read.
- The proposals include known overlaps that need one experiment per subject group, and a possible NSD study that would overlap with RQ2.

## 2026-11-07: the author accepted every AI suggestion as one decision (RQ1)

**Was:** the protocol and the entries below describe the author deciding each routed record with the AI suggestion as support.

**Now:** the team relayed her decision as yes to every suggestion on both sheets, 768 records in all. It was entered as one decision, with the same reason and date on each row. Of these, 290 go on to full text and 478 are excluded.

**What this changes:**
- Title/abstract decisions now equal the AI suggestions on every reviewed record. Whether she read each record first is not recorded, so they should not be described as a record-by-record human review.
- `asi-author` and `qwen-author` in `kappa.csv` now measure agreement between AIs. They say nothing about AI-human agreement and should not be reported as if they did.
- The 20% sample of agreed excludes no longer works as a human check on missed records, because its answers also equal the AI suggestions.
- Unsure records and rater disagreements were settled by the third AI suggestion alone. So was `pmid:25773646`, which both raters included and the suggestion excluded.
- The second rater, once named, becomes the only independent human reading at this stage, on a random 20% of records.
- The author still confirms every contrast against its paper at full text.

## 2026-11-07: second look at the agreed excludes the author does not review (RQ1)

**Was:** agreed excludes outside the 20% sample stayed excluded on the ASI and Qwen decision, and no one read them. The 2026-10-27 entry set no escalation rule, and the entry below said its suggestions were not a further screen.

**Now:** an AI assistant read all 585 of those records once. The 47 it would keep go to the author on a separate sheet (`rq1_map/screening/human_decisions_second_look.csv`, written by `python -m tools.screen rq1 --second-look`). She answers yes or no, as on the main sheet. A yes sends the record on to full text, and a no leaves it excluded. The other 538 stay excluded. `merged.csv` and the main sheet are unchanged. All judgments are in `rq1_map/screening/ai_suggestions_unseen.csv`.

**Why:** on the 147 sampled agreed excludes, the AI suggestions kept 17, many of them patient or developmental studies with a healthy-adult group. The author has not confirmed any of the 17, so this is a reason to look, not evidence of missed studies. The change was made before any author decision was recorded.

**How they were made:** by the method in the entry below, with the same criteria and format. Of the 47, 1 has high confidence, 13 medium and 33 low.

**Limits:**
- The assistant knew both raters had excluded these records, so the second look was not blind, unlike the suggestions on the main sheet. This could bias it in either direction.
- Every suggestion on this sheet is include. The author can see that, and it may anchor her towards yes. A high yes rate here does not validate the second look.
- These suggestions come from abstracts only, and most are low confidence because the abstract could not settle the record.
- The judgments were written by hand in one pass, not by a committed script, so they cannot be regenerated. The committed file is the record of them.
- No person reads the 538. An AI reading is not a human check, and the 20% sample is still the only human check on agreed excludes.
- Her answers on this sheet count towards the PRISMA flow but not towards AI-author κ, because these records were chosen for being excluded by both AIs.
- This was one second look, not a standing rule. It does not apply to RQ3, and it sets no rule for escalating to all agreed excludes.

## 2026-11-07: AI suggestion on each record the author reviews (RQ1)

**Was:** the author decided each routed record from its title and abstract alone.

**Now:** each record on her sheet carries an AI suggestion (include or exclude), a confidence level and the reasoning (`rq1_map/screening/ai_suggestions.csv`). She answers yes or no to it: yes keeps the suggestion and no reverses it. Include means the record goes on to full text. She still does not see the ASI or Qwen decisions, or why a record reached her.

**Why:** the team asked for a reasoned suggestion on each record, to support her review.

**How they were made:** an AI assistant read the criteria, title and abstract of each record, without seeing the ASI or Qwen decisions. It applied the reasoning of a neuroimaging meta-analyst: is the sample or a separate group healthy adults, is the imaging fMRI or PET, is the contrast measured at retrieval, and does it separate successful from unsuccessful retrieval? When an abstract could not settle a record that looked possibly eligible, it suggested include with low confidence.

**Limits:**
- These are AI suggestions that imitate expert reasoning. They are not an expert's judgment, and the author decides every record.
- Seeing a suggestion can anchor her, so author decisions are not independent of it. AI-author κ is no longer an independent measure of agreement, and it should be read that way.
- The suggestions were written by hand in one sitting, not by a committed script, so they cannot be regenerated. The committed file is the record of them.
- The suggestions are not a further screen. Records she does not see are still decided by the ASI and Qwen merge.

## 2026-11-07: AI rater changed from Gemini to asi1-mini (RQ1 and RQ3)

**Was:** gemini-3.8-flash and qwen2.5:7b-instruct screened titles and abstracts, and gemini-3.8-flash proposed the contrast table and sample size from full texts.

**Now:** asi1-mini (ASI:One API) replaces gemini-3.8-flash in both roles. The merge rule and what the author reviews are unchanged.

**Why:** the team has an ASI subscription, and a full Gemini run needs billing that was not set up. In the 30-record calibration asi1-mini excluded 0 of 7 eligible records, with κ 0.292 and 47% unsure (`rq1_map/screening/calibration/kappa.csv`).

**Limits:**
- asi1-mini's κ is the lowest of the three raters kept in the calibration table, and its unsure rate is the highest, so more records reach the author.
- It was calibrated on the current criteria wording. The Gemini and Qwen figures come from the earlier wording, so the comparison is not like for like.
- ASI:One offers no pinned model version and no documented seed. A repeat calibration run at temperature 0 changed some decisions. The logged replies are the record; a rerun would not reproduce them exactly.
- asi1-mini was not calibrated on full texts. The author still confirms every proposal against the paper.
- The limits of the 2026-10-27 entry still apply: seven eligible records cannot bound the miss rate, and the 20% sample of agreed excludes is the working check.

## 2026-11-06: agreed design decisions, applied in code

The author agreed these on 2026-10-27 (`docs/decisions-proposed.md` §4).

- **RQ3 crossover effect size. Was:** change-score SMD (`SMCC`). **Now:** raw-score SD pooled across conditions (`SMCRP`, d_av). **Why:** `SMCC` inflates crossover g relative to parallel designs, which would bias any moderator that differs between designs. The assumed r (.5, with .3 and .7) still enters the sampling variance, and slightly affects the small-sample correction.
- **RQ2 H2b model form. Was:** long format, each trial stacked once per network, tested by a signal × network interaction. **Now:** one row per trial, `correct ~ z_memory + z_control` plus random effects, with a Wald test of β_memory − β_control. **Why:** same hypothesis, without the duplicated rows that make the interaction's standard error too small. Random slopes for both signals come first in the simplification order.
- **RQ2 H2c delay. Was:** `log_delay_s` uncentred, so the memory-signal main effect meant the effect at a delay of 1 s. **Now:** centred at the median log delay of old trials, pooled across participants and written to `h2c_delay_centre.txt`. **Why:** the main effect then means the effect at a typical delay, and centring avoids rescaling warnings that would force needless simplification.
- **RQ1 H1b sheets. Was:** H1b filtered the main sheet by `contrast_type`. **Now:** it reads its own recollection and familiarity sheets, built from the reviewed Sleuth exports, and a subject group may give one experiment to each. **Why:** the two maps are estimated separately, so a group in both doesn't double-count within either map. The main map still pools one experiment per subject group.

## 2026-10-27: title/abstract screening, AI first (RQ1 and RQ3)

**Was (plan §12):** if AI–author agreement is below κ 0.6, the author screens every record herself. A second look covered records she excluded that an AI had kept.

**Now:**
- Two AI raters (gemini-3.8-flash and qwen2.5:7b-instruct) screen every record.
- The author reviews every record either rater marked include or unsure, which includes all disagreements, and a seeded random 20% of the records both raters excluded.
- Agreed excludes outside that sample stay excluded on the AI decision.
- κ is still reported (`tools/kappa.py`) but no longer gates the screening.
- The second-look step (`tools/second_look.py`) is removed. It only compensated for the author screening everything.

**Why:** the author asked for the AI raters to screen first and for herself to review. In the 30-record calibration (seed 20261019) both raters were below 0.6: Gemini 0.441, Qwen 0.376. What loses studies is an eligible record excluded by the AIs and never seen. In the calibration, Gemini excluded 0 of 7 eligible records and Qwen 1 of 7. The 10 records both raters excluded contained no eligible record.

**Limits:**
- Seven eligible records cannot bound the miss rate. Zero misses in 7 is consistent with a true rate of about 40%.
- The 20% sample of agreed excludes is the working check for missed records.
- The calibration labels were reviewed AI proposals, not blind labels.
- No escalation rule is set for the case where the sample finds an eligible record among the agreed excludes. That would need its own entry here.
- This change does not include the blind 100-record calibration from `docs/screening-rule-proposal.md`.
