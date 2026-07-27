# crowdin-qa-pipeline

Automated localization QA pipeline using Crowdin's GitHub integration and GitHub Actions. When Crowdin pushes translated files to the repository, a Python QA script runs automatically and flags issues before they reach production.

## How it works

```
Crowdin (source sync) → GitHub push to main → GitHub Actions → QA checks → Pass / Fail
```

1. Crowdin watches `source/en.json` for changes and syncs translations automatically
2. When translations are ready, Crowdin pushes translated files to `locales/`
3. The push triggers the GitHub Actions workflow
4. `scripts/run_qa.py` checks every translation file under `locales/`
5. The workflow fails if any issues are found, passes if the files are clean

> The source upload is handled by Crowdin's native GitHub integration — not a script. This reflects how localization pipelines work in production, where the TMS owns the sync layer and CI owns the quality gate.

## QA checks

The script runs the following checks on every `.po`, `.xliff`, `.xlf`, and `.json` file it finds:

- **Untranslated strings** — target is empty
- **Placeholder mismatches** — `{name}`, `%s`, `%(key)s` present in source but missing or extra in target
- **Identical source/target** — string was not translated (with exceptions for known terms: `OK`, `PDF`, `SMS`, `PIN`, `ID`)

For JSON files, the script automatically locates the source file under `source/` using the same filename, and compares each key's value against the translation.

## Supported formats

| Format    | Extension        |
| --------- | ---------------- |
| JSON      | `.json`          |
| PO / POT  | `.po`            |
| XLIFF 1.2 | `.xliff`, `.xlf` |
| XLIFF 2.0 | `.xliff`, `.xlf` |

## Repository structure

```
crowdin-qa-pipeline/
├── .github/
│   └── workflows/
│       └── l10n-qa.yml     # GitHub Actions workflow
├── scripts/
│   └── run_qa.py           # QA runner
├── source/
│   └── en.json             # Source strings (Crowdin watches this)
├── locales/
│   ├── ar/                 # Arabic translations (pushed by Crowdin)
│   ├── fr/                 # French translations (pushed by Crowdin)
│   ├── es/                 # Spanish translations (pushed by Crowdin)
│   └── pl/                 # Polish translations (pushed by Crowdin)
├── requirements.txt
└── README.md
```

## Languages

| Code | Language |
| ---- | -------- |
| `ar` | Arabic   |
| `fr` | French   |
| `es` | Spanish  |
| `pl` | Polish   |

## Running locally

```bash
pip install -r requirements.txt

# Check all translation files
python scripts/run_qa.py locales/

# Check a single file
python scripts/run_qa.py locales/ar/content.json
```
