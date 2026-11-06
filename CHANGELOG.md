# Changelog

Deviations from the protocol (`docs/registration-1-rq1.md`) and from the project plan, dated (YYYY-MM-DD), with the reason for each.

## 2026-11-06: agreed design decisions, applied in code

The author agreed these on 2026-10-27 (`docs/decisions-proposed.md` §4).

- **RQ3 crossover effect size. Was:** change-score SMD (`SMCC`). **Now:** raw-score SD pooled across conditions (`SMCRP`, d_av). **Why:** `SMCC` inflates crossover g relative to parallel designs, which would bias any moderator that differs between designs. The assumed r (.5, with .3 and .7) still enters the sampling variance, and slightly affects the small-sample correction.
- **RQ2 H2b model form. Was:** long format, each trial stacked once per network, tested by a signal × network interaction. **Now:** one row per trial, `correct ~ z_memory + z_control` plus random effects, with a Wald test of β_memory − β_control. **Why:** same hypothesis, without the duplicated rows that make the interaction's standard error too small. Random slopes for both signals come first in the simplification order.
- **RQ2 H2c delay. Was:** `log_delay_s` uncentred, so the memory-signal main effect meant the effect at a delay of 1 s. **Now:** centred at the median log delay of old trials, pooled across participants and written to `h2c_delay_centre.txt`. **Why:** the main effect then means the effect at a typical delay, and centring avoids rescaling warnings that would force needless simplification.

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
