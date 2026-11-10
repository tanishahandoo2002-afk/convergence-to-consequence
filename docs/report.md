# From Convergence to Consequence: results

*Tanisha Handoo. Draft of 2026-11-10.*

> **Drafting note.** At the team's request, this report was drafted by an AI assistant from the committed
> scripts' outputs and `CHANGELOG.md`. The plan (§8.6) limited AI to language editing, so this is a
> deviation (`CHANGELOG.md`, 2026-11-10). The author has not yet revised the interpretation. Every number
> comes from a script output or a CHANGELOG entry that cites one.

## Question

Meta-analyses place an episodic-retrieval network in the hippocampus, posterior parietal cortex and medial
prefrontal cortex, and that network is increasingly used as a stimulation target. This project asked
whether a curated map of the network (RQ1) predicts memory for single events in 7T fMRI (RQ2) and whether
the memory effects of tDCS/tACS depend on how much of the electric field reaches it (RQ3). Both tests compare
the map with a domain-general control network: the multiple-demand parcels, with the memory map removed.

## RQ1: the map

**Data.** PubMed gave 1,309 records (1,306 after duplicates). Of these, 1,016 were excluded at title and
abstract, 154 full texts could not be retrieved and 106 were excluded at full text, leaving 30 papers. With
BrainMap, the ALE has 57 experiments and 826 foci. Seventeen BrainMap experiments (242 foci) could not be
checked against their papers.

**Map.** The ALE (cluster-forming p < .001, cluster-level FWE p < .05, 5,000 iterations) gives 8 clusters,
with peaks in:

| Cluster | Peak (MNI) | Label | Size (mm³) |
| --- | --- | --- | --- |
| 1 | -8, -48, 32 | posterior cingulate | 2,560 |
| 2 | -2, -26, 30 | posterior cingulate | 2,200 |
| 3 | -48, -60, 32 | angular gyrus | 7,536 |
| 4 | -26, -28, -12 | left hippocampus | 1,712 |
| 5 | -6, -74, 40 | precuneus | 1,552 |
| 6 | -10, 12, -2 | left caudate | 856 |
| 7 | -6, 54, 2 | paracingulate gyrus | 2,264 |
| 8 | -62, -24, -10 | posterior middle temporal gyrus | 1,120 |

**H1a** (hippocampus, posterior parietal and medial prefrontal convergence) is supported in the main map.
Two caveats apply:
- The hippocampus, paracingulate and middle temporal clusters disappear from the map built without the 17
  unchecked experiments. That map keeps the posterior cingulate, angular, precuneus and caudate clusters and
  adds a superior frontal one.
- In the fail-safe test, every cluster survives 40 added null experiments, except the caudate cluster, which
  is lost at 20.

**H1b** (recollection vs familiarity) was not run: 16 and 8 experiments, against the 17 per group required.

## RQ2: single trials in the Natural Scenes Dataset

**Data.** Eight participants, 284 sessions and 750 trials per session. Each frozen mask was mapped into
each participant's native space, and the mean signal in each mask was taken per trial from the
`betas_fithrf_GLMdenoise_RR` betas (b3). The models are logistic mixed models with participant and image
random effects. The robustness set is: the b2 betas, leave-one-participant-out, the top-50% map, the Yeo
control mask, the map without unchecked experiments, and a within-session permutation test.

| Hypothesis | Estimate (log-odds per SD) | 95% CI | p | b2 betas |
| --- | --- | --- | --- | --- |
| H2a: map signal, hits vs misses | 0.641 | 0.210 to 1.072 | .0036 | 0.617 (0.232 to 1.002) |
| H2b: map minus control, hits vs false alarms | 0.447 | 0.294 to 0.601 | 1.1e-8 | 0.590 (0.450 to 0.730) |
| H2c: map signal x log delay | -0.228 | -0.263 to -0.193 | 3e-37 | -0.122 (-0.153 to -0.090) |

- **H2a is supported.** Higher map signal goes with remembering a seen image. The pooled estimate holds when
  each participant is left out in turn (0.503 to 0.756), with the top-50% map (0.609) and with the map without
  unchecked experiments (0.798). By participant, the permutation test gives p = .001 for 4 of 8 on b3 and
  p < .05 for 6 of 8 on b2. The per-participant model p-values are smaller than the permutation p-values, so
  the permutation p is the one to use for single participants.
- **H2b is supported.** The map separates hits from false alarms more than the control network does. The
  control coefficient is negative (-0.175 on b3), so control signal is, if anything, higher on false alarms.
  The difference is positive in all 8 participants, with p < .05 in 7. It holds with the Yeo control mask
  (0.324).
- **H2c is supported.** The map's link with remembering weakens as the delay since the last view grows. At
  the median delay, the map signal does not reliably predict hits (0.107, p = .60). The interaction on b2 is
  about half its b3 size, so its strength depends on the beta version, though its direction does not.
- In pooled H2b, the image random effect was estimated at zero and was dropped, keeping the participant slopes.
  This was a logged deviation from the simplification order (`CHANGELOG.md`, 2026-11-09).

## RQ3: stimulation meta-analysis

**Data.** PubMed gave 349 records. Of these, 186 were excluded at title and abstract, 67 full texts could not
be retrieved and 10 were excluded at full text, leaving 86 studies. 45 studies gave usable means and SDs, for
92 effects (Hedges' g, positive = better memory). Each montage's field was modelled in SimNIBS 4.6 on the Ernie
head, as the mean field magnitude inside each frozen mask. The field models use the 61 effects from 33 studies
whose montage could be modelled. The models are three-level, with CR2 robust tests and the number of sessions
as a covariate. Results are at r = .5; r = .3 and .7 change no conclusion.

- **Overall effect:** g = 0.211 (95% CI 0.112 to 0.310). Leaving out one study at a time gives 0.158 to
  0.222. The multilevel Egger slope is 0.845 (p = .09). The PET intercept is -0.024 (-0.315 to 0.267), and the
  PEESE intercept 0.073 (-0.100 to 0.246). After adjusting for small-study effects, the evidence for an
  overall benefit is weak.
- **H3a is not supported:** the field-in-map slope is 0.311 g per V/m (-2.900 to 3.521, p = .82).
- **H3b is not supported:** map minus control field is 0.448 (-14.7 to 15.6, p = .94).
- **H3c (exploratory):** compared with recall, recognition is -0.205 (p = .11) and source memory -0.216
  (p = .09). This points in the predicted direction, but neither difference is reliable.
- **H3d (exploratory):** 9 clinical studies (15 effects) had fields. The field x group term is 10.3
  (-44.4 to 65.1, p = .53).
  - With the clinical fields taken from an older-adult head built from an OASIS-2 scan, it is 9.5
    (-53.5 to 72.5, p = .59).
  - That head's fields are 1.09-1.33 times Ernie's, which runs against what atrophy would predict. Its mesh
    skipped the cortical-surface step, so this is a sensitivity check only.

The modelled mask means span 0.003-0.172 V/m. A slope "per V/m" therefore extrapolates far beyond the data:
across the observed range, the H3a CI is about ±0.5 g. RQ3 cannot rule out a field effect of the size of the
overall effect. It finds no evidence for one.

## Together

| | Map minus control | 95% CI | Scale |
| --- | --- | --- | --- |
| RQ2, H2b | 0.447 | 0.294 to 0.601 | log-odds, hit vs false alarm, per SD of signal |
| RQ3, H3b | 0.448 | -14.7 to 15.6 | Hedges' g per V/m |

The two rows are on different scales and are not compared numerically (figure: `results/integration.png`).

The map does better than the control network for prediction, but not detectably for stimulation:
- Its signal tracks whether a single image is remembered and separates true from false "old" responses,
  and does both better than the control network.
- Its link to memory is strongest for recent items.
- In the stimulation trials, how much of the field reaches the map does not explain which trials improved
  memory.

For choosing stimulation targets, the published tDCS/tACS trials give no support for aiming fields at this
network rather than at general task regions. Three caveats apply:
- The montages deliver small, similar mask-averaged fields.
- Many trials are small.
- One head model stands in for every participant.

## Limitations

- **Screening and extraction relied on AI.** Title/abstract screening, full-text proposals and contrast
  choices came from AI raters and an AI assistant, and the author accepted the suggestions as one decision
  rather than item by item. There was no second human rater. Agreement between the two AI raters was
  κ = 0.303 (RQ1) and 0.439 (RQ3). The quality of the included set rests on these AI judgements.
- **Unchecked BrainMap data.** 17 of the 57 RQ1 experiments were not checked against their papers. Three of
  the eight clusters depend on them.
- **RQ2 scope.** The NSD task is continuous recognition of natural scenes in 8 participants, with up to about
  a year between views. The map comes from studies of other materials and tasks.
- **RQ3 fields.** Fields come from one young head (and one older head for the sensitivity check). 18 montages
  had no field, because an electrode position or the current was not reported. Off-head returns were placed
  on the head model, and effects read from figures carry digitising error.
- **Not run.** H1b had too few experiments. The HDF5 partial-read test was not run, as h5py is not installed.

## Reproducing

`make all` from a fresh clone rebuilt the masks voxel for voxel and wrote byte-identical RQ2, RQ3 and
integration results (`CHANGELOG.md`, 2026-11-10). The NSD trial tables and the OASIS scan stay outside the
repository. RQ2 uses the Natural Scenes Dataset (Allen et al., 2021, *Nature Neuroscience* 25, 116-126).
Collection of the NSD dataset was supported by NSF IIS-1822683 and NSF IIS-1822929.
