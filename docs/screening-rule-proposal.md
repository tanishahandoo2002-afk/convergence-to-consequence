# Proposal: a safety-based gate for AI-assisted screening

> **Status: considered, not adopted (2026-10-19).** The registered κ ≥ 0.6 rule stays. Both AI raters fall below it, so the author screens every title and abstract herself. The proposal below would have saved only about a quarter of that work, at the cost of 100 extra blind labels, paid API use and a non-standard rule to defend. The PubMed top-up will instead be limited to the years BrainMap covers thinly, which cuts the pile far more.
>
> The AI raters still run, as a safety net: any record the author excludes that an AI kept (include or unsure) gets a second look (`tools/second_look.py`, enforced by `checks/check_screening.py`). κ is reported as plan §8.1 asks. This document is kept as a record of the reasoning.

*Original draft follows.*

## Why change the gate

Plan §12 says: if AI–human agreement is κ < 0.6, the author screens every record herself.

The 30-record calibration (`rq1_map/screening/calibration/`) gave:

| Rater | κ | Agreement | Says "unsure" | Eligible records it excluded |
| --- | --- | --- | --- | --- |
| gemini-3.8-flash | 0.441 | 67% | 13% | **0 of 7** |
| qwen2.5:7b-instruct | 0.376 | 67% | 10% | 1 of 7 |
| qwen2.5:3b-instruct | 0.006 | 47% | 33% | 3 of 7 (dropped) |

Both usable raters fail the κ gate, mainly because they **over-include**: Gemini marked 6 ineligible or unclear records as include. In this design that error is harmless. Every AI "include" and "unsure" goes to the author anyway, so over-inclusion only adds reading time.

The error that loses studies is a **false exclusion that nobody checks**. That happens only when both raters exclude a record and it isn't in the author's 20% spot-check. κ mixes the two errors together, so it is the wrong gate for this design. In the calibration, 10 records were excluded by both raters, and none of them was eligible.

## Proposed rule

1. **Two raters, as now.** gemini-3.8-flash and qwen2.5:7b-instruct, temperature 0, every decision logged with model, prompt hash and raw reply.
2. **Routing, as now.** Any include, any unsure, and any disagreement go to the author. When both raters exclude a record, it counts as an agreed exclude.
3. **Spot-check, as now.** The author checks a seeded random 20% of agreed excludes.
4. **New gate before the full run.** Enlarge the calibration set to about 130 records: the existing 30 plus 100 new ones from the same query and seed procedure. The author labels the new 100 **blind**, without seeing any AI output. The full run may use AI exclusions only if:
   - no eligible record among the calibration records is an agreed exclude; and
   - the report states the 95% upper bound on the miss rate. With 0 misses among *k* eligible records, the bound is about 3/*k*. With about 30 eligible records (roughly 23% of 130, the rate seen so far), that is about 10%.

   If the gate fails, the plan §12 fallback applies: the author screens every record.
5. **Escalation during the full run.** If the 20% spot-check finds even one eligible record among agreed excludes, the author screens all agreed excludes. This mirrors the coordinate spot-check rule in plan §12.
6. **κ is still reported** (AI–AI, each AI–author, author–second rater), as plan §8.1 asks. It just isn't the gate.

## What it saves, honestly

In the calibration, a third of records (10 of 30) were agreed excludes. Applied to the 1,681 RQ1 records, that's about 560 agreed excludes. The author checks about 110 of them (the 20% sample) and reads roughly 1,230 records in all, instead of 1,681. That's a saving of about a quarter, not a large one. The main gain is that screening stays reproducible and every exclusion stays documented.

## Caveats to state in the registration

- **The first 30 reference labels are not blind.** They began as AI proposals that were reviewed and confirmed (see `LABELS_PROVENANCE.md`). That's why the gate relies on 100 new, blind-labelled records.
- **Thirty eligible records is still a small number.** A 10% upper bound on the miss rate is an honest limit, not a guarantee. The 20% spot-check and the escalation rule cover the rest.
- **The full Gemini run needs billing.** The free tier allows 20 requests a day for this model, which is about 84 days for 1,681 records. Qwen 7B takes about 42 s per record on this laptop, about 20 hours in total.

## Decisions for the author

1. Adopt this gate, or keep κ ≥ 0.6?
2. Size of the blind calibration set: 100 new records (proposed), or another size?
3. Escalation threshold: escalate on one eligible record found in the spot-check (proposed), or on more than one?

If adopted, the code needs a small addition: the calibration report would also give the number of eligible records among agreed excludes, and the miss-rate bound. That will be planned and tested separately.
