# Changelog

Deviations from the protocol (`docs/registration-1-rq1.md`) and from the project plan, dated (YYYY-MM-DD), with the reason for each.

## 2026-11-08: RQ3 means and SDs read from PMC tables by script, pilot of 10 studies (RQ3)

**Now:** as in RQ1, `rq3_stimulation/extract_pmc.py` copies each mean and SD from a named cell of the paper's PMC table XML. An AI assistant chose the cells and wrote the study facts, montages and RoB 2 ratings in `rq3_stimulation/extraction_spec.yaml`. No person or model typed a mean or SD. The output is in `rq3_stimulation/draft/` and is not yet part of the analysis: `effects.csv`, `montages.csv` and `rob2.csv` are unchanged until the author answers `draft/review.csv`.

**Rules the spec follows (the team decided the first; the others are the assistant's, for review):**
- Each eligible episodic-memory test in a study, at the first test after the stimulation protocol ends. For a multi-session study that is the first assessment after the last session. Later follow-ups are left out.
- One measure per test: delayed recall for list-learning tests, else the paper's primary measure (for example d' over accuracy).
- When several active arms share one sham group, the sham n is split evenly between the comparisons, so its participants are not counted twice.

**Pilot results:** 12 effects from 6 of 10 studies, with 7 montages. Recomputed g for Honma 2026 (PFC-PPC vs sham, day 1) is 0.161 against the paper's 0.16. The other 4 studies give no usable means and SDs in tables. One tables only change from baseline with SE; the others report results only in figures or pooled in text.

**Limits:**
- The RQ1 extraction limits apply: the choice of cell is an AI judgment, and a wrong choice gives a correct number for the wrong arm or test.
- RoB 2 ratings come from methods excerpts, not whole papers. Most studies are rated "some concerns" because randomisation details or registration were not found.
- Montage details missing from the text (for example peak-to-peak vs peak current) are flagged on the sheet.
- If the full set matches the pilot, about 4 in 10 studies will have no table data. Figures, change scores and author contact are not handled yet.

## 2026-11-08: no second-rater check on RQ3 extraction (RQ3)

**Was (plan §12, design §10):** the RQ3 extraction check required `checked_by` on at least 20% of effect rows, filled by a second rater.

**Now:** the check no longer requires `checked_by`. The column stays, and is filled only if someone does check a row.

**Why:** the second rater was dropped for RQ1 (2026-11-07), and the team decided to drop this rule for RQ3 too.

**Limits:** no second person checks any extracted number. Every value still comes from a named table cell copied by script, and the author reviews each row.

## 2026-11-08: AI check of the full-text proposals before the author reviews them (RQ3)

**Now:** as in RQ1, an AI assistant checked all 96 asi1-mini proposals, and the author reviews its check on `rq3_stimulation/screening/full_text_check.csv`. She answers yes or no for each paper. Yes keeps the suggestion and no reverses it. The sheet gives the suggested population, design, stimulation, memory test and N, with reasons, a link to the text that was read, and the asi1-mini proposal. Her answers count for PRISMA. She answered yes to all 96, relayed by the team, so 86 studies are included and 10 excluded at full text, and `make rq3-check-screen` passes.

**Why:** the team asked to mirror the RQ1 method.

**Results:** the check suggests 86 include (57 high, 23 medium, 6 low confidence) and 10 exclude (1 high, 8 medium, 1 low). It agrees with asi1-mini on 73 of the 96 papers. Of the 72 proposed eligible, it keeps 68. Of the 23 proposed ineligible, it keeps 18, mostly papers excluded for non-significant results, or for source, DRM or self-reference memory tests that the criteria allow. It decides the 1 invalid reply (`pmid:38056370`, exclude, low). The excludes are mainly secondary or pooled reanalyses of samples reported elsewhere, one duplicate record (`pmid:38854074` of `pmid:40800986`), and face-inversion and spatial-navigation outcomes. The reasoning flags possible shared samples (for example `pmid:36660288` and `pmid:38007663`, `pmid:32280093` and `pmid:29375290`, `pmid:31660693` and `pmid:35034949`) and severity checks for AD samples.

**Limits:**
- The RQ1 check limits apply: the assistant read excerpts (participants, design, sham, memory tests and N), not whole papers or supplements. It saw asi1-mini's proposal, and the judgments were written by hand in one pass, so the sheet is the record of them.
- A yes decides eligibility only. No effect size has been extracted, and nothing enters `effects.csv` until data are taken from each paper.
- Many includes carry a check (severity, delay, sham arm, shared sample) that only the full paper can settle.
- 67 records were not retrieved, so these results cover free full texts only.

## 2026-11-08: RQ3 full texts from PMC and free PDFs (RQ3)

**Was:** the RQ1 full-text method reads PMC's open-access text only, and counts every other record as not retrieved.

**Now:** RQ3 follows RQ1, with asi1-mini proposing eligibility, population, design, stimulation, memory test and N for each paper (`rq3_stimulation/screening/trial_proposals.csv`, `make rq3-full-text`). When PMC has no text, the tool also tries each open-access PDF that OpenAlex lists for the PMID. The PDF is read in memory and not saved, and the `source` column records the link. Records with neither are counted as not retrieved (`full_text_not_retrieved.csv`). RQ1 is unchanged.

**Why:** the team asked to look for free copies online before counting a record as not retrieved.

**Results:** text was found for 96 of the 163 records, 86 from PMC and 10 from free PDFs (4 bioRxiv preprints, 3 gredos.usal.es, and one each from nature.com, macau.uni-kiel.de and kar.kent.ac.uk). The other 67 are not retrieved. asi1-mini proposes 72 eligible and 23 ineligible, and gave 1 invalid reply (`pmid:38056370`).

**Limits:**
- The RQ1 full-text limits apply: the model is not calibrated on full texts, and open-access papers are not a random subset.
- A preprint can differ from the published paper, so data from the 4 bioRxiv texts need checking against the published version where one exists.
- Publisher pages that answer with a bot check or HTML are skipped, not bypassed. One repository (osti.gov) refused the connection.

## 2026-11-08: second look at the agreed excludes the author does not review (RQ3)

**Was:** the 167 agreed excludes outside the 20% sample stayed excluded on the ASI and Qwen decision, and the RQ1 second look said it did not apply to RQ3.

**Now:** the team asked for the same second look as RQ1. An AI assistant read all 167 once. The 32 it would keep go to the author on a separate sheet (`rq3_stimulation/screening/human_decisions_second_look.csv`, written by `python -m tools.screen rq3 --second-look`). She answers yes or no, as on the main sheet. The other 135 stay excluded. All judgments are in `rq3_stimulation/screening/ai_suggestions_unseen.csv`. She answered yes to all 32, relayed by the team, so 163 records go to full text and 186 are excluded at title/abstract.

**Why:** the author accepted 6 include suggestions among the 42 sampled agreed excludes, so both AI raters miss records she counts as eligible. Unlike RQ1, this was decided after her main-sheet answers were recorded.

**How they were made:** by the method of the RQ3 main-sheet suggestions, with the same criteria and format. Of the 32, 10 have high confidence, 12 medium and 10 low. Many are healthy-adult memory studies (DRM, source memory, object-location recall) that both raters excluded.

**Limits:** the RQ1 second-look limits apply here: the look was not blind, every suggestion on the sheet is include, the judgments were written by hand in one pass, no person reads the 135, and her answers count towards PRISMA but not towards AI-author κ. `make rq3-check-screen` now fails only on the PRISMA reconcile, until full-text decisions exist (163 assessed, 0 decided).

## 2026-11-08: author accepts every AI suggestion (RQ3)

**Now:** the author answered yes to all 182 AI suggestions on her RQ3 sheet, relayed by the team, as in RQ1. 218 records are excluded at title/abstract and 131 go to full text (`python -m tools.prisma rq3`). Her decisions agree with ASI at κ = 0.610 and with Qwen at κ = 0.287 (n = 182, `kappa.csv`). Because she accepted the 6 include suggestions among the 42 sampled agreed excludes, both AI raters missed records she counts as eligible; the 167 unreviewed agreed excludes stay excluded unless the team asks for a second look.

**Limits:** `make rq3-check-screen` fails on the PRISMA reconcile until full-text decisions exist (131 assessed, 0 decided).

## 2026-11-07: AI suggestion on each record the author reviews (RQ3)

**Now:** RQ3 title/abstract screening follows the RQ1 method. The ASI and Qwen raters screened all 349 records (κ = 0.439, `rq3_stimulation/screening/kappa.csv`). The merge sends 182 to the author: 55 agreed includes, 85 disagreements and a 20% sample of 42 of the 209 agreed excludes. Each record on her sheet (`rq3_stimulation/screening/human_decisions.csv`) carries an AI suggestion, a confidence level and the reasoning (`rq3_stimulation/screening/ai_suggestions.csv`). She answers yes or no to it, as in RQ1.

**Why:** the team asked for the same review support as RQ1.

**How they were made:** an AI assistant read the RQ3 criteria and each record's title and abstract, without seeing the ASI or Qwen decisions. When an abstract could not settle a record that looked possibly eligible, it suggested include with low confidence. Where two records looked like the same study or the same sample, the reasoning says so, so that full text can check for double counting.

**Limits:**
- The RQ1 limits apply here too: these are AI suggestions, they can anchor her decisions, and they were written by hand, so the committed file is the only record of them.
- Of the 42 sampled agreed excludes, the AI suggests include for 6, two of them with high confidence (pmid:26200716, pmid:25697588). If she agrees, both AI raters missed eligible records, and the 167 agreed excludes that nobody reviews may hold more.

## 2026-11-07: SimNIBS installed on the internal disk (RQ3)

**Was:** the design put SimNIBS on the external drive.

**Now:** SimNIBS 4.6.0 is installed in `~/Applications/SimNIBS-4.6`, from the official installer. Its checksum matched the release, and it is signed by the SimNIBS developer and notarized by Apple. Subject data and outputs stay on the external drive.

**Why:** the team chose the internal disk, because the USB stick has dropped out several times and SimNIBS would fail whenever it did.

**Limits:**
- This release's arm64 build ships three Intel-only helpers that `charm` uses (`CAT_Surf2Sphere`, `CAT_WarpSurf`, `mmg3d_O3`; SimNIBS issue #675). They run through Rosetta on this Mac, and the head model build will show whether `charm` completes.
- The install uses about 2.2 GB of the Mac's limited free space.

## 2026-11-07: older-adult head model from OASIS-2, not OASIS-3 (RQ3)

**Was:** the plan built the older-adult head model from an OASIS-3 T1.

**Now:** it uses OASIS-2 session `OAS2_0181_MR1`, MPRAGE run 1 (`config/rq3.yaml`). The subject is female, 74, CDR 0.5, MMSE 26, nWBV 0.733, at her first visit. Only this session was extracted, and the scan stays in `$C2C_DATA` under the OASIS terms.

**Why:** there is no OASIS-3 access, and OASIS-2 is open. RQ3's clinical trials are in MCI and early Alzheimer's disease, so the team chose a subject with very mild dementia (CDR 0.5) rather than a healthy older adult. Among the 20 first-visit CDR 0.5 subjects aged 70 to 80 in the downloaded half of OASIS-2, she has a typical MMSE and atrophy rather than an extreme value.

**Limits:**
- One person's anatomy stands in for a clinical group, so field estimates will not generalise to every patient.
- Only half of OASIS-2 (`OAS2_RAW_PART2`) was screened for a subject.
- The scan is 1.25 mm in one direction, which `charm` accepts but which is coarser than its preferred 1 mm.

## 2026-11-07: RQ2 keeps the main memory map, with a verified-only sensitivity check

**Now:** RQ2's primary memory mask stays the main ALE map, which includes the 17 unverified BrainMap experiments, as planned. Two masks are added and frozen with the others: `memory_verified`, from the ALE without those experiments, and `control_md_verified`, its paired control. `rq2_nsd/models.R` refits H2a, H2b and H2c with them as a `verified_only` robustness variant.

**Why:** the team chose this. The left hippocampus, paracingulate and middle temporal clusters appear only in the main map, so RQ2 needs to show whether its results depend on them.

**Limits:**
- A difference between the two fits cannot say whether the unverified experiments add signal or error.
- `control_md` and `control_md_verified` differ slightly, because each excludes its own memory mask, so H2b is not an identical comparison across the two fits.
- These variants are not run yet, because RQ2 needs the NSD data and native-space masks.
- The team relayed the author's acceptance of the freeze sign-off. Its note says an AI assistant viewed 3 of the 6 QC images and ran the mask check, and that she accepted this in bulk. Each image shows only a few slices.

## 2026-11-07: sign-offs accepted as one decision (RQ1)

**Now:** the team relayed the author's acceptance of 13 suggested sign-offs on `rq1_map/pmc_draft/signoff_review.csv`: 5 foci outside the brain mask and the 8 spot-checked experiments. They are in `checks/human_signoffs.csv` with `who = author`, and each note says it was checked by an AI assistant and accepted in bulk.

**Limits:**
- `human_signoffs.csv` records no human check of these items. The spot-check does not act as a human check on coordinates or row choices.
- For the 4 PMC experiments, the assistant only reread the numbers by script, which cannot catch a wrong choice of rows.
- The 4 BrainMap experiments rest on the assistant's earlier comparison with the papers.

## 2026-11-07: 17 BrainMap experiments kept unverified (RQ1)

**Was:** the extraction check failed unless every experiment had a verified contrast, every focus outside the brain mask had a sign-off, and the spot-check could reach any experiment.

**Now:** the 17 BrainMap experiments whose papers the author cannot access stay in the analysis, marked `Not verified (paper not accessible)`. For these only, the check gives warnings instead of errors, outlier sign-offs are not required, and the spot-check leaves them out. `rq1_map/run_ale.py` also writes a verified-only map and cluster table next to the main results.

**Why:** the team chose to keep the data rather than drop it.

**Limits:**
- Nobody has compared these contrasts, sample sizes or foci with their papers. They rest on BrainMap's coding, and the review of the 9 papers that could be read found errors in BrainMap's labels, N and contrasts.
- They make up 17 of 57 experiments and 242 of 826 foci.
- Two foci outside the brain mask stay unchecked: `bm007` (-3, 65, 34) and `bm017` (-20, -16, -32).
- `bm017`'s label is unclear about encoding vs retrieval, so it may not be an eligible contrast.
- The main map should be read next to the verified-only map. A result that appears only in the main map depends on unverified data.

## 2026-11-07: the author accepted the extraction suggestions as one decision (RQ1)

**Was:** the entries below say the author would confirm each contrast against its paper before it entered `experiments.csv`.

**Now:** the team relayed that she went with every AI suggestion on the extraction sheets. It was entered as one decision. 32 PMC experiments are added to `experiments.csv` and `coordinates.csv`, and 8 BrainMap experiments are accepted. 18 included papers are dropped at this stage, 6 by a suggested no and 12 that could not be extracted, which changes PRISMA to 106 excluded at full text and 30 included. All are marked `Tanisha Handoo (accepted AI check)` in `contrast_verified_by`.

**Limits:**
- That label means she accepted an AI check. Whether she read each paper is not recorded, so these contrasts should not be described as verified by a human against the paper.
- Her answers now equal the AI suggestions at every stage: title/abstract, full text and extraction. No independent human decision exists for any included or excluded record.
- The 17 BrainMap experiments whose papers she cannot access stay unverified, with blank `contrast_verified_by`. The extraction check fails until that is resolved.
- The five new outlier foci, the spot-check and these 17 are not signed off.

## 2026-11-07: AI suggestions on the extraction review sheets (RQ1)

**Now:** each row of `rq1_map/pmc_draft/review.csv` and `brainmap_review.csv` carries an AI suggestion (yes or no), a confidence level and a reason, added at the team's request to make review easier. The `agree` column stays blank for the reviewer's own answer, and a suggestion alone changes nothing.

**Limits:**
- The same AI assistant chose the table rows and wrote these suggestions, so it is judging its own work. They are no independent check, and they may anchor the reviewer.
- On the 17 BrainMap rows with no free full text, the suggestion rests on the BrainMap label only.

## 2026-11-07: coordinates read from PMC tables by script, for the author to review (RQ1)

**Was:** the author typed coordinates from each paper, and the protocol said an AI was never used to read or transcribe them. The entry on the AI check below repeats that.

**Now:** `rq1_map/extract_pmc.py` reads coordinates directly from each paper's PMC table XML. An AI assistant chose the table rows for each contrast (`rq1_map/extraction_spec.yaml`), and read those tables to do so. No person or model typed a number. The result is in `rq1_map/pmc_draft/`, and it is not yet part of the analysis: `experiments.csv` and `coordinates.csv` are unchanged, and `contrast_verified_by` is blank until she reviews each row of `rq1_map/pmc_draft/review.csv`.

**Why:** the team asked for the assistant to do this work, with the author reviewing it. Reading from XML removes typing errors, and the extraction can be rerun.

**Results:** 38 experiments and 495 foci from 36 of the 48 included papers (25 success, 13 recollection). Six foci fall outside the brain mask and need outlier sign-offs. Twelve papers could not be extracted: eight have their peaks in supplements, one has no peak table in the XML, one has only ROI statistics, one does not say which regions are reversed, and one pools encoding with retrieval. They still count as included in PRISMA until she decides.

**Limits:**
- This departs from the rule that no AI handles coordinates. The script only copies numbers, but the choice of rows is an AI judgment, and a wrong choice gives correct numbers for the wrong contrast.
- Choices made on the assistant's judgment are stated row by row on the review sheet, including peaks left out as small-volume corrected, uncorrected or negative. Other reviewers might choose differently.
- The XML can lose formatting. Table shading and italics are not visible, so rows marked only that way may be misread.
- `pmid:27155127` lists selected peaks only and has N = 136, so including it could bias the map. The sheet says so.
- The H1b sheets are not extended, because familiarity has 8 experiments, below the gate of 17, and none of the new contrasts is familiarity.
- Of the 25 BrainMap experiments, 17 have no free full text, including both unchecked outlier foci, so the assistant could not check them. `rq1_map/pmc_draft/brainmap_review.csv` lists what she must confirm from her own access.

## 2026-11-07: second rater dropped (RQ1)

**Was:** a blind second rater screened a seeded 20% of records, and author-second κ was reported. The entry below recorded them as anonymous.

**Now:** there is no second rater for RQ1 screening. `second_rater_sample.csv` and the blank `second_rater_decisions.csv` are removed, and the screening check asks for second-rater decisions only where a sample exists.

**Why:** the planned rater gave their answers together with the author, so they were not independent, and they could not cover the 106 sampled records she never answered. The team chose to drop the step rather than report a κ of 1.0.

**Limits:**
- No independent human reading of title/abstract decisions exists. Those decisions come from the AI raters and AI suggestions, accepted by the author.
- The screening check now passes without a second rater, so a pass does not show human reliability.
- RQ3 is not decided by this entry.

## 2026-11-07: second rater anonymous, and the author accepted the 48 suggested includes (RQ1)

**Second rater. Was:** to be named in the registration. **Now:** they take part anonymously and are not named in the project's records or on GitHub. Their decisions appear only under `rater = second`. **Why:** the rater asked for this. **Limits:** readers cannot verify who they are or what experience they have. They have not yet screened any record, and to stay blind they should not open this repository, which holds the AI and author decisions, until they finish.

**Full-text sheet. Now:** the team relayed the author's yes to all 48 suggested includes on `rq1_map/screening/full_text_check.csv`, and then to all 88 suggested excludes. Each was entered as one decision, with the same reason and date on each row of that group.

**Limits:**
- These decisions equal the AI suggestions. Whether she read each paper first is not recorded, so they should not be described as a paper-by-paper human full-text review.
- The 88 excludes rest on an AI reading of excerpts, without supplements or tables published as images. A study could be lost if its usable table was in one of those places.
- The 48 include 26 with medium or low confidence, some of which the sheet says to exclude if no peaks are found, or which depend on a supplement that the AI did not read.
- The "included" count in PRISMA can fall. A paper with no usable coordinates, or one sharing a subject group with another, cannot enter the map, and any such change needs its decision corrected.
- This yes does not verify a contrast. `contrast_verified_by` stays blank and nothing enters `experiments.csv` until she confirms each contrast against its paper.

## 2026-11-07: AI check of the full-text proposals before the author reviews them (RQ1)

**Was:** the author would check each asi1-mini proposal against its paper with no intermediate step.

**Now:** an AI assistant checked all 136 proposals first, and the author reviews its check on `rq1_map/screening/full_text_check.csv`. She answers yes or no for each paper. Yes keeps the suggestion and no reverses it. The sheet gives the suggested table, contrast, type and N, with reasons and a PMC link. Her answers count for PRISMA.

**Results:** the check suggests 48 include (22 high, 20 medium, 6 low confidence) and 88 exclude (47 high, 41 medium). Of the 86 proposed eligible, it agrees with 45 and rejects 41. Of the 49 proposed ineligible, it keeps 3, and it rejects the 1 invalid reply. It differs from the proposal on N for 4 papers. It first differed on a fifth, `pmid:23026757`, but the extraction pass showed the check was wrong and the proposal's N of 18 was right, so the sheet was corrected.

**Why:** the team asked for it, to reduce the author's work. The disagreement with asi1-mini also shows that its proposals could not be used unchecked.

**Limits:**
- The assistant read excerpts, not whole papers: participants, analysis methods, sentences on retrieval contrasts, and table captions, headers and subheadings without values.
- Supplements were not read, and tables published only as images were not seen. Nine suggested includes depend on a supplement, and these need her direct check.
- The assistant saw asi1-mini's proposal for each paper, so the check was not independent of it.
- The judgments were written by hand in one pass, not by a committed script, so they cannot be regenerated. The sheet is the record of them.
- A yes on this sheet decides eligibility only. It does not verify a contrast, so `contrast_verified_by` stays blank until she confirms each contrast in the paper, and nothing enters `experiments.csv` until then.
- No coordinate was recorded. Coordinates are still entered by hand from the paper, and are not transcribed by an AI.
- 154 records were not retrieved, so these results cover open-access papers only.

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
