# Screening methodology

This document explains **why** the tool behaves the way it does, so each design choice can be challenged.

## 1. Source and scope

- Source: UN Security Council Consolidated List (XML), downloaded from the official UN endpoint.
- Screened names per listed party: primary name, name in original script, every alias.
- Each run records the list's `dateGenerated` value in the output (`list_version`) so a result can be tied to the
  exact list version used.

## 2. Name normalization

Applied identically to listed names and customer names:

1. Unicode normalization (NFKC), lowercase.
2. Transliteration of Armenian and Cyrillic characters to Latin.
3. Removal of accents and diacritics; punctuation becomes a space.
4. Folding of frequent spelling variants (e.g. Mohammed / Mohamed / Muhammad -> one token).
5. Removal of the particles `al` / `el`, which are written inconsistently.

Rationale: most false negatives in name screening come from transliteration and spelling differences, not from
genuinely different names.

## 3. Name score (0-100)

`name_score = max( token_sort_ratio, 0.95 x token_set_ratio )`

- `token_sort_ratio` is insensitive to word order ("Testov Ivan" = "Ivan Testov") and tolerant of spelling variants.
- `token_set_ratio` catches a **missing middle name or patronymic**, which is very common in real customer data.
  It is capped at 95 because a subset match is weaker evidence than a full-name match, and it is applied only
  when both names have at least two tokens, so a single common token never produces a high score.

## 4. Decision rules

| Name score | Base status |
|---|---|
| >= `--match` (default 90) | POTENTIAL MATCH |
| >= `--review` (default 80) | REVIEW |
| below | CLEAR |

Date-of-birth corroboration (year level, because UN records often hold only a year or a range):

- DOB **match**: REVIEW is upgraded to POTENTIAL MATCH.
- DOB **mismatch**: POTENTIAL MATCH is downgraded to REVIEW. **A mismatch never clears a hit**, since listed
  dates of birth can be approximate, incomplete or deliberately varied.
- DOB missing on either side: no change.

## 5. Thresholds are a risk-appetite decision

Lower thresholds reduce the risk of missing a true match but increase false positives and review workload.
Defaults are illustrative. In production they should be calibrated on historical data, approved by the
compliance function and documented, with periodic below-the-line testing.

## 6. Known gaps

No country/nationality, document-number or address signals; no alias-quality weighting; no Arabic or CJK
transliteration; UN list only. See the roadmap in the README.
