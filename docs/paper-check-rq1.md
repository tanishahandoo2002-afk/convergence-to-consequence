# RQ1 paper check (2026-10-27), for the author's review

Each BrainMap experiment was checked against its paper wherever a free full text could be found. The check covered:
- the population;
- the task phase;
- the exact contrast;
- N;
- the coordinate space;
- every focus.

This was done by an AI assistant on request, and the author reviews it. Nothing here counts as signed off until she enters `contrast_verified_by` and the outlier sign-offs (see "What the author does" at the end).

## How the foci were compared

Each paper's table was compared with the foci BrainMap stores (`rq1_map/coordinates.csv`):
- **Talairach-reported foci** (Eldridge) are identical to BrainMap's.
- **MNI-reported foci,** including SPM "Talairach" from the MNI template, are stored by BrainMap after an MNI-to-Talairach transform. They were matched after NiMARE's `mni2tal`, and every one lies within 1.9 mm. The leftover difference is between BrainMap's transform and NiMARE's.

No focus was typed in by hand.

## Papers read (9 of 26)

| Exp | Paper | Source | Result |
| --- | --- | --- | --- |
| bm001 | Duzel 2001, Hum Brain Mapp | PMC6872004 | **Removed.** It re-reports the Duzel 1999 PET data: the same 11 subjects and identical peaks. One experiment per subject group. |
| bm002 | Duzel 1999, PNAS | PMC15598 | Keep, success. Old > new in the episodic task (Table 3, 2 foci match). PET blocks of 85% old vs 85% new items, all trials: **block-level, flagged.** |
| bm003 | Eldridge 2000, Nat Neurosci | author copy, MIT | Keep, recollection. Correct R > correct K at test (Table 1, 15 foci identical). **N corrected 12 → 11** (one subject excluded for motion). |
| bm009 | Kensinger & Schacter 2007, Neuropsychologia | author copy, Schacter lab | Keep, but **swap contrasts** (see below). N = 19, test phase, all 47 foci match. |
| bm012 | Dobbins et al. 2003, Neuropsychologia | author copy, Schacter lab | Keep, recollection. Source hit > miss (Table 2, 24 foci match). **3 recency foci removed** (see below). N = 11 confirmed. |
| bm016 | Henson et al. 1999, J Neurosci | PMC6782715 | Keep, recollection. Both contrasts are at test: correct R > correct N (Table 2) and R > K (Table 4); 16 foci match. BrainMap's label "(Retrieval + Encoding)" is wrong. |
| bm020 | Vilberg & Rugg 2007, Neuropsychologia | PMC1933497 | Keep, recollection (Table 3, 13 foci match). **N corrected 14 → 28**: two experiments of 14, analysed together. |
| bm023 | Yonelinas et al. 2005, J Neurosci | PMC6725129 | Keep, recollection. R > high-confidence familiarity at test (Table 2, 26 foci match). |
| bm024 | Johnson S C et al. 2006, Neurobiol Aging | PMC2627778 | Keep, success. Previously learned > novel drawings in the 77-person healthy reference group (Table 3, 7 foci match). **N = 77 is right**; the 14 in the review was the age-matched control group. **Flag:** only 5 items, each trained 30 times, presented in short runs, so this is an overlearned, block-like old > new contrast. |

## Changes waiting on the author's yes

1. **Kensinger 2007: use the plain success contrast.**
   - *What BrainMap gave us:* the two "successful recognition" contrasts are hits > misses *exclusively masked* by false recognition (Tables 3 and 4: "successful but not false"). That masking removes every region that also responds to false alarms, so neither is a plain success contrast.
   - *The plain contrast:* hits > misses as a conjunction across negative and neutral items (Table 2 top), which BrainMap calls "Overall Recognition, Neutral + Negative". The first review wrongly excluded it as an emotion contrast.
   - *Proposed:* use it, plus the visually specific contrast (same > similar, recollection-like).
   - *To apply:* open `/Volumes/C2C/kensinger_fix.work` in Sleuth (only those two contrasts are shown), export it as `/Volumes/C2C/kensinger_fix.txt` (GingerALE text, Talairach), and its foci replace bm009's.
2. **Dobbins 2003: drop the recency contrast.** "Recency hit > miss" compares correct and incorrect choices of which of two *studied* words came later. It is none of the accepted contrast types, so its 3 foci were removed and the source contrast stays.
3. **Duzel 2001 removed** as a duplicate, and the N corrections above.

Items 2 and 3 are already applied in the sheets and the review CSV, and are easy to revert. Item 1 needs the export.

## Foci outside the brain mask (5 of 7 checked)

Each checked one matches its paper. They are real peaks near the edge of the brain that the Talairach-to-MNI conversion moves just outside the 2 mm mask, so the proposal is to sign each one off as "pass":

| Focus | Paper's value | Region |
| --- | --- | --- |
| bm009: 44, 40, 31 | Table 4 | R superior frontal gyrus, BA 9 (drops out if change 1 is applied) |
| bm009: −49, 44, −6 | Table 4 | L middle frontal gyrus, BA 11 (drops out if change 1 is applied) |
| bm009: 50, 38, 22 | Tables 2 and 4 | R middle frontal gyrus, BA 46 |
| bm016: −56.73, 21.85, 24.31 | Table 2: −60, 27, 21 | L middle frontal gyrus, BA 46 |
| bm024: 5.87, 41.93, 57 | Table 3: 8, 52, 54 | R medial prefrontal |

**Not checked (no free full text):** bm007 (Fliessbach 2006) at −3, 65, 34, and bm017 (Peters 2007) at −20, −16, −32.

## Papers not read: no free copy found (17)

No free copy was found on PubMed Central, OpenAlex, Google Scholar or the labs' sites. ScienceDirect, OUP and the Max Planck repository block automated access. Each needs the PDF (Amity library) and one question answered:

| Exp | Paper | Question |
| --- | --- | --- |
| bm004 | Dolan 2000 | High- vs low-target-density blocks: confirm the block design (stays in, flagged). |
| bm005 | Cansino 2002 | Source correct > incorrect at retrieval: confirm N = 17 and test phase. |
| bm006 | Daselaar 2001 | "Retrieval success vs attempt": is it hits > correct rejections, or block-level? |
| bm007 | Fliessbach 2006 | Is old > new restricted to correct trials? Check focus −3, 65, 34. |
| bm008 | Hofer 2007 | Correct recognition > correct rejection: confirm N and test phase. |
| bm010 | Watanabe 2008 | Hits > correct rejections for music: confirm N = 18. |
| bm011 | Daselaar 2006 | Recollection contrast measured at retrieval, from confidence ratings? |
| bm013 | Johnson J D 2007 | Recollection contrast measured at retrieval? |
| bm014 | Montaldi 2006 | "Recollected > F3": confirm it is recollection hits > strongest familiarity. |
| bm015 | Fenker 2005 | Remember > know and remember > new at test: confirm. |
| bm017 | Peters 2007 | "Source Encoding … Retrieval": is this at retrieval (keep) or encoding (exclude)? Check focus −20, −16, −32. |
| bm018 | Sharot 2004 | Remember > know at test: confirm. |
| bm019 | Suchan 2008 | Recollection > correct rejection: confirm N = 10. |
| bm021 | Weis 2004 | Hit with correct source > hit with wrong source: confirm. |
| bm022 | Woodruff 2005 | Remember-hits compared with correct rejections or with misses? |
| bm025 | Henke 1997 | "Recall old − recall new": is it correct trials only? |
| bm026 | de Zubicaray 2007 | Cued recall hit > correct rejection and hit > miss: confirm. |

## What the author does

1. Read this file and say yes or no to changes 1–3.
2. Export `kensinger_fix.work` from Sleuth (change 1).
3. Get the PDFs above. With the PDFs in `/Volumes/C2C/papers/`, the assistant can run the same check on them.
4. Confirm the 5 outlier sign-offs.

Then `contrast_verified_by` and the sign-off rows are filled in her name, and `python -m checks.check_rq1_extraction` is rerun.
