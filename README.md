# sanctions-toolkit

[![CI](https://github.com/ara-avetisyan-git/aml-sanctions-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/ara-avetisyan-git/aml-sanctions-toolkit/actions)

Small, auditable command-line tools for working with the **UN Security Council Consolidated Sanctions List**:

| Command | What it does | Compliance use case |
|---|---|---|
| `download` | Fetches the official XML, validates it, saves it with the list's generation date | Reproducible, dated evidence of which list version was used |
| `export` | Flattens the XML into a CSV (names, aliases, DOB, nationality, regime, listing date) | Loading into Excel / BI / a screening system |
| `diff` | Compares two list versions: added, removed, changed (Markdown + CSV report) | Trigger for re-screening the customer base; change log for the MLRO |
| `screen` | Fuzzy-screens a customer CSV, with Armenian / Cyrillic transliteration and DOB corroboration | First-line name screening with an explainable decision |

Built by an AML/CFT compliance practitioner: the point is not only the code, but the **decision logic** behind it,
documented in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Install

```bash
git clone https://github.com/ara-avetisyan-git/aml-sanctions-toolkit.git
cd aml-sanctions-toolkit
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

## Usage

```bash
# 1. Download the current list (saved to data/raw/consolidated_<date>.xml)
sanctions-toolkit download

# 2. Export to CSV
sanctions-toolkit export --input data/raw/consolidated_2026-10-28.xml --output un_list.csv

# 3. What changed between two downloads?
sanctions-toolkit diff --old data/raw/consolidated_2026-10-27.xml \
                       --new data/raw/consolidated_2026-10-28.xml \
                       --report-md changes.md --report-csv changes.csv

# 4. Screen customers (CSV: customer_id,name[,date_of_birth])
sanctions-toolkit screen --list data/raw/consolidated_2026-10-28.xml \
                         --customers examples/customers_synthetic.csv \
                         --output screening_results.csv \
                         --review 80 --match 90
```

Try it without internet using the synthetic data in `tests/data/` (all names are fictional):

```bash
sanctions-toolkit screen --list tests/data/sample_old.xml \
                         --customers examples/customers_synthetic.csv \
                         --output /tmp/results.csv
```

## Screening output

One row per hit (or one `CLEAR` row per customer without hits):
`status`, `name_score`, `matched_name`, `matched_name_kind` (primary / original_script / alias),
`dob_check` (match / mismatch / n/a), `un_reference`, `regime`, `listed_on`, `list_version`.

Statuses: `POTENTIAL MATCH` -> `REVIEW` -> `CLEAR`. **Nothing is auto-cleared on a date-of-birth mismatch**:
it only downgrades a potential match to review.

## Limitations (read before using for anything real)

- **Demonstration project.** Not a replacement for a production screening solution, and not legal advice.
- **UN list only.** Real programmes also need EU, OFAC, UK and national lists (e.g. the Armenian domestic list).
- Names in scripts other than Latin, Cyrillic and Armenian (e.g. Arabic, Chinese) are not transliterated; such
  names are screened through their Latin-script primary names and aliases.
- Matching is name-based with year-level DOB corroboration; no country, ID-document or address matching yet.
- The UN XML structure is parsed defensively, but always check the first live run against the official list.
- Use **synthetic data only** in this repository. Never commit real customer data.

## Project structure

```
src/sanctions_toolkit/
  un_loader.py   download + XML parsing
  normalize.py   transliteration, accent stripping, variant folding, DOB years
  diff.py        version comparison and reports
  screening.py   fuzzy matching and decision rules
  cli.py         command-line interface
tests/           pytest suite with synthetic UN-style XML
docs/            methodology
```

## Roadmap

- EU consolidated list and OFAC SDN loaders behind the same interface
- Scheduled GitHub Action that downloads the list daily and publishes the diff
- Alias quality weighting (strong vs weak a.k.a.), country / nationality signals
- Arabic transliteration

## License

MIT. Author: Ara Avetisyan, AML/CFT compliance - [LinkedIn](https://www.linkedin.com/in/ara-avetisyan-1795802a)
