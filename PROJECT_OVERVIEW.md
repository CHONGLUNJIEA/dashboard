# Swift Payments Analytics Dashboard

## Project

This project analyzes the fictitious Swift-style payment dataset prepared for the
UMDAC Datathon 2026 Preliminary Round. It reconstructs transaction-routing,
foreign-exchange, settlement-latency, temporal, currency-corridor, anomaly, and
party-text patterns, then presents the findings in a printable Streamlit report.

GitHub repository: [CHONGLUNJIEA/dashboard](https://github.com/CHONGLUNJIEA/dashboard)
(private).

The ETL processed **1,048,575 transactions** from six CSV parts. The generated
summary is `output/dashboard_summary.json` (about 4.3 MB).

## Repository layout

```text
dashboard/
├── data/
│   ├── part_1.csv
│   ├── part_2.csv
│   ├── part_3.csv
│   ├── part_4.csv
│   ├── part_5.csv
│   └── part_6.csv
├── output/
│   └── dashboard_summary.json
├── src/
│   ├── 02_etl_aggregator.py
│   └── 03_dashboard_app.py
├── .gitignore
└── requirements.txt
```

The CSV parts are about 518 MB combined; each part is below 100 MB. The source
parts are copied into `data/`, leaving the originals outside this project
unchanged.

## Run locally

### Open the dashboard in Chrome

1. Open the `dashboard` project folder in VS Code, then open **Terminal → New
   Terminal**. The terminal should be at the project root (the folder containing
   `requirements.txt`).
2. Install the dependencies the first time you set up the project:

```powershell
python -m pip install -r .\requirements.txt
```

3. Start the Streamlit app:

```powershell
python -m streamlit run .\src\03_dashboard_app.py
```

4. Open Chrome and visit `http://localhost:8501`, or use the **Local URL**
   printed in the terminal. If port 8501 is already in use, Streamlit may show a
   different port; use the URL it prints.

Keep the terminal open while using the dashboard. Press `Ctrl+C` in that
terminal to stop the server. The checked-in `output/dashboard_summary.json` is
ready to use; rerun `python .\src\02_etl_aggregator.py` from the project root
only if you need to regenerate the summary from the CSV files. Chrome's
**Print → Save as PDF** produces a landscape report with a page break before
each feature group.

## Dataset checks and inferred relationships

`src/02_etl_aggregator.py` reads all `data/part_*.csv` files in chunks and writes
the feature-group statistics to `output/dashboard_summary.json`.

| Feature group | Included evidence |
| --- | --- |
| Routing topology | Dataset validation against the payment-type definitions, plus transaction type × participant count × continuity flag. |
| FX and settlement latency | Count, mean, median, 25th percentile, and 75th percentile of `TOTAL_DURATION` by transaction type and FX-step count; FX ≥3 versus FX <3 median-duration comparisons by route type. |
| Temporal patterns | UTC hour and weekday transaction counts and median USD amount, segmented by ordering type and EUR, USD, GBP, CHF, SGD, and CNY. |
| Currency and corridors | BIC country codes from characters `[4:6]`, mapped-currency match rates, and USD amount distributions for all four B/C party-type corridors. |
| Anomaly signatures | Dataset validation against Romance/CEO scam party-type definitions, 100% `ORDERING_TYPE` breakdown by anomaly, amount quantiles, and high-amount outlier summary. |
| Tokenized party details | Token-containing transactions per 1,000 records within each role and B/C party type, with raw occurrence counts retained for hover detail. |

Observed checks from this run:

- **Dataset validation:** Direct routes had exactly two participants in 662,245
  rows; Indirect (342,752) and Covered (43,578) routes had at least three.
- **FX/duration relationship:** In pooled data, comparing FX ≥3 with FX <3,
  median `TOTAL_DURATION` rose from 149 to 545 for Indirect (3.66×) and from 308
  to 542 for Covered (1.76×). Controlling for route size changes the picture:
  among Indirect payments with exactly four participants, the median was 438 at
  one FX conversion (n=4,917) and 415 at three (n=51,132), so it did not rise in
  this cohort. Direct had no FX ≥3 observations and a maximum of one step. The
  pooled association may reflect route mix and is not evidence that FX steps
  cause longer duration.
- **High-FX sample sizes:** For conversion counts ≥8, groups below n=30 are
  marked low-confidence in the chart; hover also reports n for every point.
- **Currency alignment:** Ordering BICs matched in 794,544 of 883,612 comparable
  rows (89.9%); beneficiary BICs matched in 188,292 of 899,096 comparable rows
  (20.9%). The row counts shown here are denominators, not match counts.
- **Anomaly dataset validation:** Romance Scam rows had `ORDERING_TYPE=C`, and
  CEO Scam rows had `ORDERING_TYPE=B`; both checks passed. Blank
  `ANOMALY_TYPE` values are treated as `NORMAL`, so all rows are represented.
- **Anomaly evidence and specification discrepancy:** The 100% stacked chart
  shows ordering-party type by anomaly class. `CUSTOMER_RECALL` appears in 32
  dataset rows although it is not among the five anomaly examples listed in the
  case-study brief; it is retained as a distinct dataset category pending
  clarification.
- **Normalized token pattern:** The ordering-party `<business:...>` token occurs
  in 854.36 per 1,000 B records (704,225/824,276) and 0 per 1,000 C records
  (0/224,299). Because the consumer baseline is zero, a finite relative-rate
  multiplier is undefined; the dashboard shows normalized rates rather than
  claiming an arbitrary finite multiple.

Currency match rates use matched rows divided by comparable rows, where
comparable means a mapped BIC country code and a present currency. The dashboard
shows both counts explicitly. Rates exclude unmapped BIC country codes and
missing currencies.
The country-to-currency mapping is intentionally explicit in the ETL script;
these rates describe the mapped observations and are not, on their own, proof
of a settlement-currency rule. High-amount outliers are review signals, not
proof of fraud.

## Dashboard

`src/03_dashboard_app.py` renders one section for each feature group. Each
section includes a labeled evidence, validation, or method callout, a Plotly
chart, and a concise banking interpretation. The FX section highlights an
inferred, quantified association rather than restating the supplied definitions.
The temporal heatmap can be filtered by currency,
ordering type, and measure. Print CSS requests A4 landscape pages, starts each
feature group on a new page, and keeps charts together when printing.
