# Project 9: Financial Fraud and Transaction Monitoring

A Python 3.9 / Streamlit dashboard for exploring fictional USD bank transactions and explainable monitoring rules. The default dataset contains 500 records across 30 accounts and 30 days in January 2025; the UI supports 250–10,000 records. A fixed seed reproduces the dataset. Eight unusually large payments and a twelve-payment account burst are deliberately included for demonstration; these are scenarios, not labeled fraud outcomes.

## Run

From this existing project folder on macOS:

```sh
cd /Users/brodyzychowski/Documents/fraud-monitor
source venv/bin/activate
python --version
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501). Stop with Ctrl+C. The existing Python 3.9 virtual environment and Git repository are preserved; no environment recreation is needed. Dependency versions match the installed environment.

## Monitoring methodology

- Amount greater than or equal to the configurable threshold: **40 points**.
- Per-account count greater than or equal to the frequency threshold in the configurable trailing window: **40 points**.
- Both rules apply: **20 additional points**, for a maximum of 100.
- Flag when score is greater than or equal to the selected cutoff (default 40).

The frequency window includes both endpoints and the current payment. All simultaneous payments count together; later timestamps never affect earlier scores. Credits and debits both count as account activity. Every row reports rule contributions, its window count, score, and a plain-language explanation. Weights are illustrative, not trained or calibrated probabilities. Raising the cutoff above 40 requires both rules to flag a record. Real deployments need calibrated rules, investigator review, privacy controls, and outcome validation.

## Financial analyses and charts

1. **Daily cash flow:** credit inflows, debit outflows, and net flow, displayed in a time-series chart. Net flow is not an account balance.
2. **Account concentration:** each account's share of gross transaction value, top-five concentration, top-ten value chart, and detailed table. Gross value includes credits and debits.
3. **Channel exposure:** total and flagged transaction value, flagged counts, and percentage flagged by channel, with a comparative bar chart. Flagged value is not confirmed fraud or loss.

Sidebar controls recalculate scores and analyses. Account and flagged-only review filters affect only the transaction table and downloadable CSV. All records are fictional; there is no external data connection or real customer information.

## Validation and tests

```sh
python -m unittest discover -s tests -v
```

Tests cover deterministic generation, minimum size, exact amount/time boundaries, simultaneous payments, account isolation, prevention of future leakage, cutoff behavior, invalid records/configuration, financial reconciliation, and a Streamlit dashboard smoke test with reactive controls. Application inputs are bounded; the analysis layer validates schema, timestamps, amounts, duplicate IDs, direction, and thresholds. Expected input failures display an explanatory error in the dashboard.

## Files

- `app.py`: interactive dashboard, charts, filters, export, and user-facing error handling.
- `monitoring.py`: synthetic data generation, validation, scoring, explanations, and financial summaries.
- `tests/`: standard-library unittest tests including Streamlit's AppTest.
- `requirements.txt`: direct runtime dependencies pinned to Python 3.9-compatible installed versions.

No files inside `.git/` or `venv/` are changed by the application.
