# Swift Payments Analytics Dashboard

## Project

This project analyzes the fictitious Swift-style payment dataset prepared for the
UMDAC Datathon 2026 Preliminary Round. It reconstructs transaction-routing,
foreign-exchange, settlement-latency, temporal, currency-corridor, anomaly, and
party-text patterns, then presents the findings in a printable Streamlit report.

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

From this directory in PowerShell:

```powershell
python -m pip install -r .\requirements.txt
python .\src\02_etl_aggregator.py
python -m streamlit run .\src\03_dashboard_app.py
```

Open the Streamlit URL shown in the terminal (normally
`http://localhost:8501`). Keep that terminal open while using the dashboard;
press `Ctrl+C` there to stop the server. Chrome's **Print → Save as PDF**
produces a landscape report with a page break before each feature group.

## ETL outputs and reconstructed rules

`src/02_etl_aggregator.py` reads all `data/part_*.csv` files in chunks and writes
the feature-group statistics to `output/dashboard_summary.json`.

| Feature group | Included evidence |
| --- | --- |
| Routing topology | Transaction type × participant count × continuity flag; Direct routes had exactly two participants, and Indirect/Covered routes had at least three. |
| FX and settlement latency | Count, mean, median, 25th percentile, and 75th percentile of `TOTAL_DURATION` by transaction type and FX-step count. Direct routes had at most one FX step. |
| Temporal patterns | UTC hour and weekday transaction counts and median USD amount, segmented by ordering type and EUR, USD, GBP, CHF, SGD, and CNY. |
| Currency and corridors | BIC country codes from characters `[4:6]`, mapped-currency match rates, and USD amount distributions for all four B/C party-type corridors. |
| Anomaly signatures | Counts, party-type breakdowns, amount quantiles, high-amount outlier summary, and Romance/CEO scam ordering-type checks. |
| Tokenized party details | `iban`, `business`, and `first_name` token occurrence and transaction counts by party role and B/C type. |

Observed checks from this run:

- **Routing:** Direct 662,245 rows; Indirect 342,752; Covered 43,578. All three
  participant-count checks passed.
- **FX:** Direct maximum was one conversion step. For FX ≥3 versus FX <3, the
  median-duration ratio was about 3.66× for Indirect and 1.76× for Covered.
- **Currency alignment:** Match rate was about 89.9% for ordering BICs and 20.9%
  for beneficiary BICs among comparable, mapped rows.
- **Anomalies:** Blank `ANOMALY_TYPE` values are treated as `NORMAL`; all rows
  are represented in the resulting anomaly counts. Romance Scam rows had
  `ORDERING_TYPE=C`, and CEO Scam rows had `ORDERING_TYPE=B`; both checks passed.

Currency match rates exclude unmapped BIC country codes and missing currencies.
The country-to-currency mapping is intentionally explicit in the ETL script;
these rates describe the mapped observations and are not, on their own, proof
of a settlement-currency rule. High-amount outliers are review signals, not
proof of fraud.

## Dashboard

`src/03_dashboard_app.py` renders one section for each feature group. Each
section includes a reconstructed-rule callout, a Plotly chart, and a concise
banking interpretation. The temporal heatmap can be filtered by currency,
ordering type, and measure. Print CSS requests A4 landscape pages, starts each
feature group on a new page, and keeps charts together when printing.
