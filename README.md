# Project 9 · Financial Fraud and Transaction Monitoring

## Video Demonstration

[Watch the Sentinel Fraud Monitoring Demonstration](https://drive.google.com/file/d/1kyaQtqhwGkY4YDd38A0UDhMgBqEx65sn/view?usp=sharing)

**Sentinel** is a Python 3.9 / Streamlit / Plotly prototype for a college finance course. It demonstrates transparent screening of fictional banking activity. Alerts require investigation and do not prove fraud. Scores are review priorities, never probabilities of fraud.

## Install and launch

The existing Git repository and `venv` are preserved. Do not recreate the environment or commit it.

```sh
cd /Users/brodyzychowski/Documents/fraud-monitor
source venv/bin/activate
python --version
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501 while the command is running. If the page cannot be reached, start the command above and leave that terminal open. Stop with Ctrl+C. Tested with Python 3.9.6 and the versions in `requirements.txt`.

## Dashboard

- Four KPI cards: transaction count, gross dollar volume, average amount, flagged count. Flag percentage and dollar exposure appear immediately below.
- Five interactive Plotly charts: daily gross volume by direction, amount distribution, risk score distribution with adjustable cutoff, top customer spending, and channel exposure.
- Cash flow, account concentration, average debit spending, and rolling-activity summaries.
- Customer, risk level, channel, and flag-status review filters; transaction inspector explaining rule contributions; filtered CSV export including audit columns.
- Controls immediately recalculate the full portfolio. Review filters affect only the table, inspector, and export, not baselines or portfolio charts. Risk labels and alert status are intentionally independent.

## Synthetic dataset and assumptions

The default is 500 transactions; controls allow 500–10,000. Python's local random generator uses seed **9**, adjustable for exploration. Identical count and seed reproduce the records. Transactions cover January 1–30, 2025, interpreted as UTC, across 30 fictional customers with one account each. Fields include transaction ID, customer/account IDs, timestamp, positive USD amount, debit/credit direction, channel, merchant category, scenario, and balance after transaction.

Ordinary amounts follow a lognormal distribution with log-mean 5.6, log-standard-deviation 1.0, capped at $4,500. Directions are sampled 85% debit and 15% credit; channels are Card, Transfer, ATM, and Online. Credit category is Income; debit categories are illustrative random categories. Categories and channels are not a full behavioral simulation, and amounts are not conditioned on merchant type. Eight transactions are replaced with $8,000–$25,000 amounts. Twelve debits of $600–$1,500 on CU001 are planted one minute apart on January 16. Scenarios identify demonstration injections, not confirmed fraud labels. Changing seed/count can change which records trigger rules.

Each account starts at $50,000. The balance adds credits and subtracts debits in timestamp/transaction-ID order. An illustrative credit facility permits negative balances; there is no overdraft detection. This is a ledger simulation, not a realistic liquidity model. Balances and scenario labels never contribute to scores. No external data, sensitive information, uploads, or bank connection is used.

## Explicit detection rules

| Signal | Condition (inclusive comparison) | Points |
|---|---|---:|
| Large payment | Amount ≥ dollar threshold (default $5,000) | 35 |
| Customer-relative payment | Amount ≥ multiplier × prior mean (default 4×), with at least 5 prior same-direction records | 25 |
| High frequency | At least 5 customer transactions in a trailing 60-minute window | 30 |
| Multiple signals | At least two signals trigger | 10 |

Score = sum of these contributions, from 0 to 100. Alert if score ≥ cutoff (default **35**). Risk labels: Minimal 0; Low 1–39; Elevated 40–69; High 70–100. Thus a Low-labeled record can be flagged at cutoff 35. Adjusting the cutoff changes alerts but not scores.

Customer-relative baselines use only strictly earlier timestamps of the same direction. Current and simultaneous payments cannot affect their own baseline. Below the minimum history, that rule is inactive and the explanation says why; other rules still operate. Frequency combines debit and credit activity per customer and includes the current transaction, all simultaneous transactions, and the exact lower window boundary. No future timestamps contribute. Each record exposes history count, prior mean, relative ratio, rolling count, rule booleans, point contributions, and an explanation.

## Financial calculations and verification

1. **Gross volume and average:** sum all positive amounts, including credits and debits. Average = volume / record count. This is activity, not revenue or net spending.
2. **Flag exposure:** flagged count / total count × 100; flagged dollar volume = sum of amounts where alert status is true. Neither measure is a loss estimate.
3. **Customer spending:** sum debit amounts per customer; average debit = spending / debit count. Credit receipts are excluded from spending.
4. **Net flow:** total credits − total debits; this is not an ending balance.
5. **Concentration:** account gross transaction value / portfolio gross value × 100. The top-five share sums the five largest account shares. Channel flag rate = channel flagged count / channel record count × 100.

A hand-calculated test uses one $100 credit and $200/$6,000 debits: volume $6,300, average $2,100, net flow −$6,100, one amount alert at cutoff 35, flagged volume $6,000, flag rate 33⅓%. Other tests reconcile balances and financial totals. Empty summaries return zeros instead of dividing by zero; empty review filters show a message. Invalid source records raise clear validation errors caught by the dashboard. Baseline NaN means no prior history, not missing source data.

## Automated tests

```sh
python -m unittest discover -s tests -v
```

Tests cover reproducibility, minimum 500 rows, scoring boundaries, rolling-window endpoints, customer isolation, simultaneous timestamps, no future leakage, relative-threshold changes, limited/direction-specific history, cutoff changes, invalid and missing data, empty results, balance reconciliation, financial calculations, five rendered charts, reactive controls, and review filters. Streamlit AppTest may emit a harmless missing-ScriptRunContext warning in test mode.

## Limitations and AI disclosure

Weights and distributions are illustrative; no model was trained or calibrated and there are no accuracy, precision, or recall claims. Previous unusual amounts can distort a customer's mean. Rules may produce false positives or miss fraud. The prototype lacks real banking security, access controls, investigator workflows, and production-scale validation.

An OpenAI Codex coding agent inspected the existing project, proposed and implemented the redesign, wrote supporting logic/documentation/tests, and executed automated tests. The student should independently review the code, understand and verify the financial methods, take their own screenshots of the running application, and follow the course's AI-use disclosure rules. This statement does not claim independent student authorship or instructor approval.

## Submission screenshots to take

1. Portfolio overview with KPI cards and the three upper charts.
2. Customer spending/channel exposure and cash-flow summaries.
3. Transaction review with a selected alert and its explanation.
4. Rules & calculations tab or changed thresholds demonstrating interactivity.

## Structure

`app.py` contains the interface; `monitoring.py` contains generation, validation, scoring, and summaries; `tests/` contains automated checks; `.streamlit/config.toml` defines the theme; `requirements.txt` pins direct dependencies. `.gitignore` excludes `venv/`, bytecode, and `.env`. No commits or uploads are performed by this implementation.

## Simulated Free and Premium subscriptions

The app starts in **Free ($0/month)**. Open **Pricing & subscription** to see both plans side by side and click **Upgrade to Premium — $20/month**. The active plan appears above the dashboard and in the sidebar. **Switch to Free Plan** reverses the demonstration at any time. There is no billing, payment integration, credit-card collection, or persistent account entitlement. Session state stores the plan; a new browser session returns to Free. This is a college-project product mockup, not production access control.

| Capability | Free | Premium — $20/month (simulated) |
|---|---|---|
| Transactions displayed/analyzed | 250 | 500–10,000 |
| Dollar threshold and frequency-count controls | Adjustable | Adjustable |
| Relative multiplier, history minimum, rolling window, risk cutoff | Standard defaults | Fully adjustable |
| Rule-based scores and basic flag explanations | Included | Included |
| Daily activity and amount charts | Included | Included |
| Financial summaries, cash flow, concentration | Included | Included |
| Risk distribution, customer spending, channel charts | Upgrade preview | Included |
| Flag-status filter | Included | Included |
| Customer, risk, channel filters | Locked | Included |
| CSV export and detailed alert inspector | Locked | Included |

The reproducible generator still produces at least 500 source records; Free analyzes only the first 250 in chronological order. Premium defaults to the full 500. This preserves the source generation and planted scenarios, although a Free preview may omit later planted activity. Scores are recalculated on the records available to each plan, so customer history and frequency results can differ. Plan switching never modifies or deletes the source or changes the rule weights. To demonstrate the full assignment, switch to Premium (no payment). Basic explanations remain in Free to preserve transparent monitoring. Disabled Free controls cannot apply previously selected Premium values.

### Layout fix and verification

The old `2rem` top padding placed content underneath Streamlit's fixed toolbar. The main content now has `5.5rem` clearance (`6rem` on narrow screens), a fluid wrapping title, horizontally scrollable tabs, and normal-flow content with no fixed dashboard positioning. Streamlit columns adapt to narrow screens. Navy, white, and teal styling remains. Tests cover Free/Premium switching, controls, data limits, chart availability, export gating, filters, and financial totals in addition to the existing scoring tests. For screenshots, capture both the dashboard and the Pricing & subscription tab. A running server is required; leave the launch terminal open.
