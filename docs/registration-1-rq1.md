# OSF Registration 1 (draft): RQ1, a curated ALE meta-analysis of successful episodic retrieval

> **Draft for Tanisha to review, edit and submit herself. Not yet registered.**
> Items marked **[OPEN]** need her decision. Each comes with a proposed default she can accept or change.
> Section numbers like "plan §8.1" refer to `From_Convergence_to_Consequence.md`; "spec" is `docs/design.md`.
> Suggested OSF template: *Generalized Systematic Review Registration*. The sections below map onto it.

---

## 1. Title and authors

**Title:** From convergence to consequence (part 1): a curated activation likelihood estimation meta-analysis of successful episodic retrieval

**Authors:** Tanisha Handoo (Amity University). **[OPEN]** Add the supervisor (and second rater, if they will be a co-author) with affiliations and ORCID iDs.

**Project repository:** https://github.com/tanishahandoo2002-afk/convergence-to-consequence

## 2. Background and aim

Meta-analyses of fMRI and PET studies describe a "recollection network" that is reliably active when people successfully retrieve past events: the hippocampus, posterior parietal cortex (precuneus/posterior cingulate, angular gyrus) and medial prefrontal cortex. These maps are widely used as regions of interest and as targets for brain stimulation, yet are rarely validated.

This registration covers the first part of a three-part project. It builds a curated, sample-size-weighted ALE map of successful episodic retrieval in healthy adults. The map, and a domain-general control network defined from it, are frozen before any later data are touched. They are then tested for predictive validity on single-trial 7T fMRI (Natural Scenes Dataset) and for causal relevance in a tDCS/tACS meta-analysis. Those tests are covered by registration 2.

## 3. Research question and hypotheses

**RQ1.** Where does activity converge across published experiments for successful episodic retrieval?

- **H1a (confirmatory check):** significant convergence in (i) the hippocampus, (ii) posterior parietal cortex (precuneus/posterior cingulate and/or angular gyrus) and (iii) medial prefrontal cortex.
  - **[OPEN] How H1a is judged.** Proposed: H1a is supported for a region if at least one significant cluster (cluster-level FWE p < .05) overlaps that region's Harvard-Oxford mask (maximum-probability atlas, 25% threshold), using these labels:
    - (i) left or right hippocampus;
    - (ii) precuneous cortex, posterior cingulate gyrus, or angular gyrus;
    - (iii) frontal medial cortex or paracingulate gyrus.
  - Each region is reported separately.
- **H1b (exploratory):** recollection-based contrasts converge more than familiarity-based contrasts in the hippocampus and angular gyrus. This is tested only if each group has at least 17 experiments (see §9.4).

**What would count against the map:** no significant convergence in one or more of the three regions. Every outcome is reported, whatever the result.

## 4. Eligibility criteria

| Include | Exclude |
| --- | --- |
| Whole-brain fMRI or PET | ROI-only analyses (including small-volume corrections reported without whole-brain results) |
| Healthy adults (18+). For studies of patients with a separate healthy-adult group, only that group's contrasts | Patient-only samples; children or adolescents |
| A retrieval-phase contrast for *successful* episodic retrieval: hits > correct rejections (old/new effect); remembered > forgotten **at retrieval**; source-correct > source-incorrect; "remember" > "know" | Encoding contrasts (including subsequent-memory effects); semantic or working memory; retrieval vs. rest or vs. a control task only; pattern-similarity or connectivity analyses without an activation contrast |
| Peak coordinates in MNI or Talairach space | No coordinates reported, and none obtainable from the authors |
| Peer-reviewed journal article | Reviews, meta-analyses, protocols, conference abstracts |

**[OPEN] Familiarity contrasts and H1b.** H1b needs familiarity-based contrasts, such as "know" > miss, or familiar > new with no recollection. None of the four accepted contrast types above is a familiarity contrast. Proposed:
- Familiarity contrasts are eligible **only for the H1b analysis**, not for the main map.
- The main map uses the four accepted types.
- The extraction sheet already records `contrast_type` as success, recollection or familiarity.

**[OPEN] Languages.** Proposed: English only, stated as a limitation.

## 5. Information sources and search

**5.1 BrainMap (starting set).** Sleuth query of the BrainMap functional database, exported in GingerALE text format. Each exported experiment is checked against §4.
- **[OPEN] Exact Sleuth query, to fill in from the Sleuth interface once the account is active.** Proposed fields:
  - Behavioral Domain = Cognition.Memory.Explicit;
  - Paradigm Class = Episodic Recall *or* Recognition;
  - Experiment Context = Normal Mapping;
  - Subject Diagnosis = Normals;
  - Contrast = activations only.
- Record the BrainMap database version and the export date.

**5.2 PubMed top-up.** BrainMap may miss recent papers, so it is topped up with a PubMed search via NCBI E-utilities, run by `tools/pubmed_search.py`, which logs the date, query and hit count automatically. Draft query (`config/rq1.yaml`):

```
("fMRI"[tiab] OR "functional magnetic resonance"[tiab] OR "functional MRI"[tiab]
 OR "positron emission tomography"[tiab] OR "PET"[tiab])
AND ("episodic memory"[tiab] OR "Memory, Episodic"[MeSH] OR "recognition memory"[tiab]
 OR "source memory"[tiab] OR "associative memory"[tiab] OR recall[tiab])
AND (retrieval[tiab] OR remember*[tiab] OR recollection[tiab] OR "old/new"[tiab])
```

- **[OPEN] Final search string.** Tanisha reviews it, and the supervisor or a librarian if possible.
- **[OPEN] Year cutoff.** Proposed: the top-up covers publication years from the first year in which BrainMap's coverage of this domain thins out, judged from the year distribution of the Sleuth export, and that cutoff year is stated here before the search runs. For scale, the draft query returned 1,681 records for all years on 2026-10-18; about 850 from 2015 onward and about 600 from 2018 onward. If BrainMap access is not granted, the top-up covers all years and becomes the only source (plan §13 fallback).
- **[OPEN] Scopus.** Proposed: added if Amity library access allows, with exports imported and de-duplicated by `tools/import_records.py`. If not, PubMed alone, stated as a limitation.
- Reference lists of included papers and of recent reviews are hand-searched; additions are logged as "other sources" in the PRISMA flow.

## 6. Screening

**6.1 Title/abstract stage.**
- **The author screens every record herself, blind to the AI decisions.** Plan §12 says that if AI–author agreement is below κ 0.6, the author screens everything. A pre-registration calibration (§6.3) put both AI raters below 0.6.
- **Two AI raters screen every record independently:** gemini-3.8-flash via the Gemini API, and qwen2.5:7b-instruct run locally via Ollama.
  - Settings: temperature 0, the eligibility criteria above as the prompt (`rq1_map/screening/criteria.md`), and JSON output.
  - Each decision is logged with the model identifier, a SHA-256 hash of the prompt, a timestamp and the raw reply.
- **Second look.** Every record the author excluded that either AI marked include or unsure is listed (`tools/second_look.py`). The author re-reads each one and records a resolution (exclusion confirmed, or included). The pipeline check refuses to continue until every listed record is resolved.
- **Second rater.** A second rater (**[OPEN]** name) screens a seeded random 20% of all records, blind to the author's and the AIs' decisions. Disagreements are resolved by discussion.
- **Agreement reported:** Cohen's κ for Gemini–Qwen, each AI–author, and author–second rater.

**6.2 Full-text stage.**
- The author assesses each remaining full text against §4.
- An AI (gemini-3.8-flash) proposes which table holds the retrieval-success contrast and the sample size. The author confirms or corrects every proposal against the paper; the sheet records who verified each one.
- The AI is never used to read or transcribe coordinates.
- Reasons for full-text exclusion are recorded for the PRISMA 2020 flow diagram, which is generated from the logs, not typed by hand.

**6.3 Calibration done before registration (disclosed).**
- **Sample:** on 2026-10-18, 30 records were drawn at random (seed 20261019) from the draft PubMed query to choose the local model and the wording of the prompt.
- **Results:**

  | Rater | κ | Eligible records it excluded |
  | --- | --- | --- |
  | gemini-3.8-flash | 0.441 | 0 of 7 |
  | qwen2.5:7b-instruct | 0.376 | 1 of 7 |
  | qwen2.5:3b-instruct | 0.006 | 3 of 7 (dropped) |

- **Caveat:** the reference labels were AI-proposed and then reviewed and confirmed by the team, so they are not blind (`LABELS_PROVENANCE.md`).
- **Effect on the procedure:** the calibration changed the choice of model and the wording of the criteria; no eligibility criterion changed.
- **Effect on the sample:** these 30 records are screened again in the main screen like any other record.

## 7. Data extraction

**7.1 Sheets.** One row per experiment in `experiments.csv`, with these fields:
- study ID, DOI, subject group;
- table or figure, and the exact contrast;
- contrast type (success, recollection or familiarity);
- N and mean age;
- coordinate space and source;
- who verified the contrast.

Foci go in `coordinates.csv`, one row per focus.

**7.2 Coordinates.** Coordinates are taken from BrainMap exports or extracted from tables with a table-extraction tool, never retyped by an AI.
- A seeded random 20% of experiments is spot-checked against the PDFs. If any error is found, every experiment is checked.
- Foci falling outside the MNI brain mask after conversion are listed and individually checked against the paper. None is dropped automatically.

**7.3 One experiment per subject group.**
- If a paper reports several eligible contrasts from the same participants, their foci are pooled into a single experiment, so that no group counts twice (Turkeltaub et al., 2012).
- **[OPEN] Pooling and H1b.** Pooling means a group that reports both a recollection and a familiarity contrast enters the main map once. Proposed:
  - for H1b only, such a group may contribute one recollection experiment and one familiarity experiment, because the two H1b maps are estimated separately;
  - the main map keeps strict pooling.

  The alternative, strict pooling everywhere, makes reaching 17 experiments per H1b group less likely.

**7.4 Authors are contacted once** for missing coordinates. Studies still lacking coordinates are excluded and listed.

## 8. Coordinate space

Talairach coordinates are converted to MNI with the Lancaster tal2icbm transform as implemented in NiMARE (`nimare.utils.tal2mni`). It is applied once, in code, to every experiment marked Talairach.

## 9. Analysis

**9.1 ALE.** NiMARE 0.22.1 (Python 3.12):
- activation likelihood estimation with sample-size-based Gaussian kernels (Eickhoff et al., 2009), in MNI152 2 mm space;
- inference by Monte Carlo cluster-level family-wise error correction, with cluster-forming threshold p < .001 (voxel level) and cluster-level FWE p < .05;
- 5,000 iterations, random seed 20261019.

**9.2 Minimum size.** The target is at least 20 experiments. With 17–19 the analysis is run and the limited power is stated. Below 17 the ALE is not run, and the plan §13 fallback applies (widen to the source-memory and recall contrasts already listed).

**9.3 Reporting.** A cluster table: peak MNI coordinates (the voxel-level ALE z maximum within each cluster), peak z, cluster volume, and Harvard-Oxford label at the peak, checked by eye. Unthresholded and thresholded maps are shared on OSF and NeuroVault.

**9.4 H1b (exploratory, gated).** Run only if both the recollection group and the familiarity group have at least 17 experiments:
- a separate ALE for each group, and an ALE subtraction (recollection − familiarity) in NiMARE with 5,000 iterations;
- **[OPEN] Thresholding of the subtraction.** Proposed: the NiMARE `ALESubtraction` z map at voxel-level p < .001 with a minimum cluster size of 200 mm³, reported as exploratory.

Otherwise, the counts are reported and the subtraction is not run.

## 10. Robustness

- **Leave-one-experiment-out jackknife:** the contribution of each experiment to each cluster (NiMARE `Jackknife`). A cluster driven mainly by one experiment is flagged.
- **Fail-safe check:** null experiments are added in sets of 10, 20 and 40. Each has random foci inside the brain, a sample size drawn from the included experiments, and the median number of foci per included experiment. The ALE is rerun with 1,000 iterations, and the report says whether each cluster's peak survives. This follows Acar et al. (2018) at fixed counts rather than searching for the exact break point.

## 11. Masks for parts 2 and 3

The following are built from the RQ1 result. They are frozen with SHA-256 hashes before any NSD or stimulation-trial data are accessed, and registered with registration 2:
- **memory map:** the significant clusters;
- **memory top-50%:** voxels at or above the median ALE value within the memory map;
- **primary control network:** multiple-demand parcels (Fedorenko et al., 2013; `allParcels-MD-HE197`) minus the memory map;
- **sensitivity control network:** Yeo et al. (2011) 7-network salience/ventral-attention plus control networks, minus the memory map.

If the memory map is empty, this is reported, and parts 2 and 3 are re-planned in registration 2.

## 12. Status of the data at registration

**[OPEN] Update on the day of submission.** As of this draft:
- **PubMed search:** run only to count hits (1,681 on 2026-10-18) and to draw the 30-record calibration sample in §6.3. The official search runs after registration.
- **Calibration sample:** those 30 titles and abstracts were screened by AI and labelled.
- **Not yet accessed:** no full texts, no coordinates, no BrainMap data (account pending).
- **No ALE has been run** on real data. The pipeline was tested only on synthetic data.

## 13. Deviations

Every change from this registration will be logged with its date and reason in `CHANGELOG.md` and reported in the paper.

## 14. Use of AI tools

Title/abstract screening and contrast identification were assisted by large language models (two independent raters). All inclusions and extracted contrasts were verified by the author; AI–author agreement was κ = [to be filled after screening]. An AI assistant also helped draft analysis code; the author ran, read and checked every script. Coordinates were never transcribed by an AI.

## 15. Data and code

- **Code:** public on GitHub, archived on Zenodo with a DOI at the preprint.
- **Extraction sheets, screening logs, PRISMA flow and the ALE maps:** public on OSF. They contain only published information.

## 16. References to cite

Eickhoff et al. (2009, 2012, 2016); Turkeltaub et al. (2012); Acar et al. (2018); Müller et al. (2018); Fedorenko, Duncan & Kanwisher (2013); Yeo et al. (2011); Page et al. (2021, PRISMA 2020); Rugg & Vilberg (2013); Salo et al. (NiMARE).

---

### Checklist of [OPEN] items for Tanisha

1. Authors, supervisor, ORCID iDs (§1)
2. How H1a is judged: atlas regions and overlap rule (§3)
3. Familiarity contrasts only for H1b (§4)
4. Language restriction (§4)
5. Exact BrainMap Sleuth query (§5.1)
6. Final PubMed string (§5.2)
7. PubMed year cutoff, from BrainMap coverage (§5.2)
8. Scopus, if library access allows (§5.2)
9. Second rater's name (§6.1)
10. Pooling rule for H1b (§7.3)
11. H1b subtraction threshold (§9.4)
12. Status of the data on the submission date (§12)

*Note for implementation: if items 3 or 10 are adopted, the code needs small changes before the ALE is run. The main ALE (`rq1_map/run_ale.py`) currently pools every contrast type, and the extraction check allows each subject group exactly once. These changes get planned and tested once the registration text is final.*
