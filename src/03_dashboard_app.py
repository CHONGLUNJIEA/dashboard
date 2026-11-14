"""Streamlit dashboard for the UMDAC Datathon 2026 Swift payments analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


PROJECT_DIR = Path(__file__).resolve().parents[1]
SUMMARY_PATH = PROJECT_DIR / "output" / "dashboard_summary.json"
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
TOKEN_NAMES = ["iban", "business", "first_name"]
ANOMALY_ORDER = [
    "NORMAL",
    "ROMANCE_SCAM",
    "FAT_FINGER_MISTAKE",
    "CEO_SCAM",
    "ACCOUNT_REPLACEMENT_SCAM",
    "DUPLICATE_PAYMENT",
    "CUSTOMER_RECALL",
]
COLORS = {
    "navy": "#15324B",
    "blue": "#2673A6",
    "teal": "#138A8A",
    "gold": "#D99A2B",
    "coral": "#C84D4D",
    "slate": "#64748B",
    "light": "#E8F0F5",
}


st.set_page_config(
    page_title="Swift Payments | UMDAC Datathon 2026",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #15324B;
        --muted: #526579;
        --line: #D7E1E9;
        --paper: #F4F7FA;
        --blue: #2673A6;
        --teal: #138A8A;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    .block-container { max-width: 1320px; padding-top: 1.8rem; }
    .report-kicker {
        color: var(--teal); font-size: .78rem; font-weight: 750;
        letter-spacing: .14em; text-transform: uppercase; margin-bottom: .35rem;
    }
    .report-title { color: var(--ink); font-size: 2.25rem; font-weight: 760; margin: 0; }
    .report-subtitle { color: var(--muted); font-size: 1rem; margin-top: .45rem; }
    .feature-heading {
        border-bottom: 2px solid var(--line); margin: .2rem 0 1rem;
        padding: .3rem 0 .75rem;
    }
    .feature-heading .number {
        color: var(--teal); font-size: .75rem; font-weight: 800;
        letter-spacing: .12em; text-transform: uppercase;
    }
    .feature-heading h2 {
        color: var(--ink); font-size: 1.55rem; line-height: 1.2;
        margin: .25rem 0 0;
    }
    .rule-card {
        background: #EAF4F8; border-left: 5px solid var(--blue);
        border-radius: 6px; color: var(--ink); margin: .35rem 0 1rem;
        padding: .8rem 1rem;
    }
    .rule-card strong { display: block; font-size: .76rem; letter-spacing: .08em;
        margin-bottom: .3rem; text-transform: uppercase; }
    .rule-card p { margin: 0; }
    .interpretation-card {
        background: #FFFFFF; border: 1px solid var(--line); border-radius: 6px;
        color: var(--muted); line-height: 1.5; margin-top: .55rem;
        padding: .75rem 1rem;
    }
    .interpretation-card strong {
        color: var(--ink); display: block; font-size: .76rem;
        letter-spacing: .08em; margin-bottom: .25rem; text-transform: uppercase;
    }
    .stPlotlyChart { background: #FFFFFF; border: 1px solid var(--line);
        border-radius: 7px; padding: .25rem; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid var(--line); border-radius: 7px;
        padding: .65rem .8rem;
    }
    @media print {
        @page { size: A4 landscape; margin: 0.38in; }
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: #FFFFFF !important; color: #172B3A !important;
            -webkit-print-color-adjust: exact; print-color-adjust: exact;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"],
        [data-testid="stSidebar"], #MainMenu, footer,
        .stDeployButton, button, .stSelectbox {
            display: none !important;
        }
        div[data-testid="stElementContainer"]:has(.stSelectbox) {
            display: none !important;
        }
        .block-container {
            max-width: none !important; padding: 0 !important;
        }
        div[class*="st-key-feature-section-"] {
            break-before: page !important;
            page-break-before: always !important;
        }
        .stPlotlyChart, [data-testid="stPlotlyChart"], figure,
        .rule-card, .interpretation-card {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
        }
        .stPlotlyChart {
            background: #FFFFFF !important; border: 0 !important;
            padding: 0 !important;
        }
        .feature-heading { margin-top: 0 !important; }
        .report-title { font-size: 1.65rem !important; }
        .rule-card, .interpretation-card { font-size: 9pt !important; }
        div[data-testid="stMetric"] { padding: .35rem .5rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_summary(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns
    with Path(path).open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def _number(value: Any, decimals: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{decimals}f}"


def _percent(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1%}"


def _yes_no(passed: bool) -> str:
    return "PASS" if passed else "CHECK"


def _rule_callout(text: str) -> None:
    st.markdown(
        '<div class="rule-card"><strong>Reconstructed Business Rule(s)</strong>'
        f"<p>{text}</p></div>",
        unsafe_allow_html=True,
    )


def _interpretation(text: str) -> None:
    st.markdown(
        '<div class="interpretation-card"><strong>'
        "Real-World Economic &amp; Banking Interpretation"
        f"</strong>{text}</div>",
        unsafe_allow_html=True,
    )


def _section_header(number: int, title: str) -> None:
    st.markdown(
        f'<div class="feature-heading"><span class="number">Feature Group '
        f"{number:02d}</span><h2>{title}</h2></div>",
        unsafe_allow_html=True,
    )


def _polish_figure(
    figure: go.Figure, title: str, height: int = 390
) -> go.Figure:
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        template="plotly_white",
        height=height,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial, sans-serif", "color": COLORS["navy"], "size": 12},
        margin={"l": 58, "r": 30, "t": 70, "b": 60},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hoverlabel={"bgcolor": "#15324B", "font": {"color": "#FFFFFF"}},
    )
    figure.update_xaxes(showgrid=False, linecolor="#B8C6D1", automargin=True)
    figure.update_yaxes(
        gridcolor="#E7EDF2", zerolinecolor="#B8C6D1", automargin=True
    )
    return figure


def _show_figure(figure: go.Figure, key: str) -> None:
    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displaylogo": False,
            "responsive": True,
            "toImageButtonOptions": {
                "format": "png",
                "filename": key,
                "scale": 2,
            },
        },
        key=key,
    )


def _section_container(number: int):
    return st.container(key=f"feature-section-{number}")


def render_routing(data: dict[str, Any]) -> None:
    section = data["feature_group_1_routing_topology"]
    checks = section["rule_checks"]
    direct_check = checks["direct_has_exactly_two_participants"]
    indirect_checks = checks[
        "indirect_and_covered_have_at_least_three_participants"
    ]

    with _section_container(1):
        _section_header(1, "Routing Topology & Network Structure")
        _rule_callout(
            f"<b>Direct ⇒ participant_count = 2</b> "
            f"({_yes_no(direct_check['passed'])}, "
            f"{_number(direct_check['rows'])} rows); "
            "<b>Indirect/Covered ⇒ participant_count ≥ 3</b> "
            f"(Indirect {_yes_no(indirect_checks['Indirect']['passed'])}; "
            f"Covered {_yes_no(indirect_checks['Covered']['passed'])}). "
            "Heatmap rows separate CONTINUITY_QFLAG = Y and N."
        )

        frame = pd.DataFrame(section["cross_tabulation"])
        participant_counts = sorted(
            int(value) for value in frame["participant_count"].dropna().unique()
        )
        row_labels = []
        matrix = []
        for transaction_type in ("Direct", "Indirect", "Covered"):
            for flag in ("Y", "N"):
                row_labels.append(f"{transaction_type} · {flag}")
                row = []
                for participant_count in participant_counts:
                    match = frame[
                        (frame["transaction_type_code"] == transaction_type)
                        & (frame["continuity_qflag"] == flag)
                        & (frame["participant_count"] == participant_count)
                    ]
                    row.append(int(match["count"].sum()))
                matrix.append(row)
        figure = go.Figure(
            go.Heatmap(
                z=matrix,
                x=participant_counts,
                y=row_labels,
                colorscale="Blues",
                text=matrix,
                texttemplate="%{text}",
                hovertemplate=(
                    "Participants: %{x}<br>Type / continuity: %{y}"
                    "<br>Transactions: %{z:,}<extra></extra>"
                ),
                colorbar={"title": "Transactions"},
            )
        )
        if 2.5 <= max(participant_counts, default=0):
            figure.add_vline(
                x=2.5,
                line_dash="dash",
                line_color=COLORS["coral"],
                annotation_text="2 | 3+ threshold",
                annotation_position="top",
            )
        figure.update_layout(
            xaxis_title="PARTICIPANT_COUNT",
            yaxis_title="TRANSACTION_TYPE_CODE · CONTINUITY_QFLAG",
            height=380,
        )
        _show_figure(_polish_figure(figure, "Participants by route type and continuity"), "routing")
        _interpretation(
            "Direct payments usually travel between an ordering institution and a beneficiary institution, "
            "so a two-participant route is structurally expected. Indirect and covered payments involve "
            "intermediaries or cover arrangements, which add participants and routing complexity."
        )


def render_fx(data: dict[str, Any]) -> None:
    section = data["feature_group_2_fx_settlement_latency"]
    rows = section["by_transaction_type_and_currency_conversion_count"]
    check = section["direct_fx_rule"]
    ratios = {
        row["transaction_type_code"]: row
        for row in section["median_latency_comparison_fx_gte_3_vs_lt_3"]
    }
    direct_ratio = ratios.get("Direct", {}).get("gte_3_to_lt_3_median_ratio")
    indirect_ratio = ratios.get("Indirect", {}).get("gte_3_to_lt_3_median_ratio")
    covered_ratio = ratios.get("Covered", {}).get("gte_3_to_lt_3_median_ratio")

    with _section_container(2):
        _section_header(2, "Foreign Exchange (FX) Steps & Settlement Latency")
        _rule_callout(
            f"<b>Direct ⇒ FX steps ≤ 1</b> ({_yes_no(check['passed'])}; "
            f"observed maximum {section['direct_max_fx_steps']}). "
            "<b>FX ≥ 3 ⇒ compare median TOTAL_DURATION with FX &lt; 3</b>: "
            f"Indirect ratio {_number(indirect_ratio, 2)}×; "
            f"Covered ratio {_number(covered_ratio, 2)}×; "
            f"Direct ratio {_number(direct_ratio, 2)} (no FX ≥ 3 observations)."
        )

        frame = pd.DataFrame(rows).dropna(subset=["currency_conversion_count", "median"])
        figure = go.Figure()
        for transaction_type, color in (
            ("Direct", COLORS["blue"]),
            ("Indirect", COLORS["teal"]),
            ("Covered", COLORS["gold"]),
        ):
            subset = frame[frame["transaction_type_code"] == transaction_type].sort_values(
                "currency_conversion_count"
            )
            if subset.empty:
                continue
            median = subset["median"].astype(float)
            figure.add_trace(
                go.Scatter(
                    x=subset["currency_conversion_count"],
                    y=median,
                    mode="lines+markers",
                    name=transaction_type,
                    line={"color": color, "width": 3},
                    marker={"size": 8},
                    error_y={
                        "type": "data",
                        "symmetric": False,
                        "array": (subset["p75"].astype(float) - median).clip(lower=0),
                        "arrayminus": (median - subset["p25"].astype(float)).clip(lower=0),
                        "color": color,
                        "thickness": 1.5,
                        "width": 4,
                    },
                    customdata=subset[["count", "mean"]].to_numpy(),
                    hovertemplate=(
                        f"{transaction_type}<br>FX steps: %{{x}}"
                        "<br>Median duration: %{y:,.1f}"
                        "<br>IQR: p25–p75"
                        "<br>Transactions: %{customdata[0]:,}"
                        "<br>Mean duration: %{customdata[1]:,.1f}<extra></extra>"
                    ),
                )
            )
        max_fx = int(frame["currency_conversion_count"].max())
        if max_fx >= 3:
            figure.add_vrect(
                x0=2.5,
                x1=max_fx + 0.5,
                fillcolor="#FCE9E5",
                opacity=0.45,
                line_width=0,
                annotation_text="FX ≥ 3",
                annotation_position="top left",
            )
        figure.update_xaxes(
            title_text="CURRENCY_CONVERSION_COUNT", dtick=1, rangemode="tozero"
        )
        figure.update_yaxes(
            title_text="TOTAL_DURATION (median; log scale)", type="log"
        )
        _show_figure(
            _polish_figure(figure, "Settlement latency by FX conversion count"),
            "fx-latency",
        )
        _interpretation(
            "Every currency conversion can add pricing, liquidity, correspondent-bank, and settlement coordination. "
            "Longer multi-currency chains therefore tend to take more time, although the measured latency also "
            "reflects cut-off times, market hours, and payment-specific controls."
        )


def render_temporal(data: dict[str, Any]) -> None:
    section = data["feature_group_3_temporal_circadian_patterns"]
    rows = section["by_hour_day_ordering_type_and_currency"]
    currencies = sorted(section["top_currencies"])

    with _section_container(3):
        _section_header(3, "Temporal Dynamics & Working-Hour Rhythms")
        _rule_callout(
            "<b>EPOCH_SECONDS → UTC hour ∈ [0, 23] and weekday ∈ [0, 6]</b> "
            "(0 = Monday). Volume and median USD_AMOUNT are grouped by UTC hour, "
            "weekday, ORDERING_TYPE ∈ {B, C}, and the six selected currencies; "
            "use the controls to inspect a single type/currency slice."
        )
        controls = st.columns([1, 1, 2])
        currency = controls[0].selectbox(
            "Currency",
            currencies,
            index=currencies.index("EUR") if "EUR" in currencies else 0,
            key="temporal-currency",
        )
        ordering_type = controls[1].selectbox(
            "Ordering type",
            ["B", "C"],
            key="temporal-ordering-type",
        )
        metric_label = controls[2].selectbox(
            "Heatmap measure",
            ["Transaction volume", "Median USD amount"],
            key="temporal-measure",
        )
        metric_column = "count" if metric_label == "Transaction volume" else "median"
        frame = pd.DataFrame(rows)
        selected = frame[
            (frame["currency_code"] == currency)
            & (frame["ordering_type"] == ordering_type)
        ]
        matrix = (
            selected.pivot(
                index="utc_day_of_week",
                columns="utc_hour_of_day",
                values=metric_column,
            )
            .reindex(index=range(7), columns=range(24))
        )
        if metric_column == "count":
            matrix = matrix.fillna(0)
        figure = go.Figure(
            go.Heatmap(
                z=matrix.to_numpy(dtype=float),
                x=list(range(24)),
                y=list(range(7)),
                colorscale="Teal",
                colorbar={"title": metric_label},
                hovertemplate=(
                    "UTC hour: %{x}:00<br>Weekday: %{customdata}"
                    "<br>" + metric_label + ": %{z:,.2f}<extra></extra>"
                ),
                customdata=[[DAY_NAMES[day]] * 24 for day in range(7)],
            )
        )
        figure.update_xaxes(
            title_text="UTC hour of day",
            tickmode="array",
            tickvals=list(range(0, 24, 2)),
            ticktext=[f"{hour:02d}:00" for hour in range(0, 24, 2)],
        )
        figure.update_yaxes(
            title_text="UTC day of week",
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=DAY_NAMES,
            autorange="reversed",
        )
        _show_figure(
            _polish_figure(
                figure,
                f"{metric_label} · {currency} · ORDERING_TYPE {ordering_type}",
            ),
            "temporal-patterns",
        )
        _interpretation(
            "Payment instructions are created and processed across markets that open and close at different local times. "
            "The UTC heatmap makes global activity comparable, while currency and ordering-party filters help separate "
            "market-hour effects from differences between business and consumer traffic."
        )


def render_corridors(data: dict[str, Any]) -> None:
    section = data["feature_group_4_currency_corridor_alignment"]
    alignment = section["country_currency_matches_by_role"]
    corridors = section["usd_amount_by_ordering_to_beneficiary_type"]
    ordering_rate = alignment["ordering"]["match_rate"]
    beneficiary_rate = alignment["beneficiary"]["match_rate"]

    with _section_container(4):
        _section_header(4, "Currency Corridors & Party-Type Value Flows")
        _rule_callout(
            f"<b>BIC country = BIC8[4:6]</b>; a match is an observed currency equal "
            "to the mapped country currency (including Eurozone → EUR). Match rates "
            f"among comparable rows: ordering {_percent(ordering_rate)} "
            f"({_number(alignment['ordering']['comparable_rows'])} rows), "
            f"beneficiary {_percent(beneficiary_rate)} "
            f"({_number(alignment['beneficiary']['comparable_rows'])} rows). "
            "USD_AMOUNT is compared across B→B, B→C, C→B, and C→C."
        )

        figure = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=(
                "BIC-country / currency match rate",
                "USD amount by ordering → beneficiary type",
            ),
            column_widths=[0.37, 0.63],
            horizontal_spacing=0.12,
        )
        roles = ["ordering", "beneficiary"]
        role_rates = [alignment[role]["match_rate"] for role in roles]
        role_counts = [alignment[role]["comparable_rows"] for role in roles]
        figure.add_trace(
            go.Bar(
                x=["Ordering BIC", "Beneficiary BIC"],
                y=[rate * 100 if rate is not None else 0 for rate in role_rates],
                marker_color=[COLORS["blue"], COLORS["teal"]],
                text=[_percent(rate) for rate in role_rates],
                textposition="outside",
                customdata=role_counts,
                hovertemplate=(
                    "%{x}<br>Match rate: %{y:.1f}%"
                    "<br>Comparable rows: %{customdata:,}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        corridor_frame = pd.DataFrame(corridors)
        corridor_frame["pair"] = (
            corridor_frame["ordering_type"]
            + "→"
            + corridor_frame["beneficiary_type"]
        )
        corridor_frame = corridor_frame.sort_values("pair")
        median = corridor_frame["median"].astype(float)
        figure.add_trace(
            go.Scatter(
                x=corridor_frame["pair"],
                y=median,
                mode="markers",
                marker={"size": 10, "color": COLORS["gold"]},
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": (corridor_frame["p75"].astype(float) - median).clip(
                        lower=0
                    ),
                    "arrayminus": (median - corridor_frame["p25"].astype(float)).clip(
                        lower=0
                    ),
                    "color": COLORS["navy"],
                    "thickness": 1.5,
                    "width": 6,
                },
                customdata=corridor_frame[["count", "mean"]].to_numpy(),
                hovertemplate=(
                    "%{x}<br>Median USD_AMOUNT: $%{y:,.2f}"
                    "<br>IQR: p25–p75"
                    "<br>Transactions: %{customdata[0]:,}"
                    "<br>Mean: $%{customdata[1]:,.2f}<extra></extra>"
                ),
                showlegend=False,
            ),
            row=1,
            col=2,
        )
        figure.update_yaxes(
            title_text="Match rate (%)", range=[0, 110], row=1, col=1
        )
        figure.update_yaxes(
            title_text="USD_AMOUNT (median; log scale)",
            type="log",
            row=1,
            col=2,
        )
        figure.update_xaxes(title_text="BIC role", row=1, col=1)
        figure.update_xaxes(title_text="Party-type corridor", row=1, col=2)
        _show_figure(
            _polish_figure(figure, "Currency alignment and corridor values", 410),
            "currency-corridors",
        )
        _interpretation(
            "A sender's domestic currency commonly aligns with the ordering institution's home market, while the beneficiary "
            "may be paid across a border or receive a different settlement currency. Business and consumer corridors also "
            "have different typical ticket sizes, so medians and IQRs are more representative than means alone."
        )


def render_anomalies(data: dict[str, Any]) -> None:
    section = data["feature_group_5_anomaly_fraud_signatures"]
    summaries = section["by_anomaly_type"]
    checks = section["ordering_type_constraint_checks"]
    outliers = section["fat_finger_high_amount_outliers"]
    romance = checks["ROMANCE_SCAM"]
    ceo = checks["CEO_SCAM"]
    fat_finger = summaries["FAT_FINGER_MISTAKE"]
    fat_quantiles = fat_finger["usd_amount_quantiles"]

    with _section_container(5):
        _section_header(5, "Anomaly Detection & Fraud Typology Rules")
        _rule_callout(
            "<b>ROMANCE_SCAM ⇒ ORDERING_TYPE = C</b> "
            f"({_yes_no(romance['passed'])}; {romance['rows']:,} rows); "
            "<b>CEO_SCAM ⇒ ORDERING_TYPE = B</b> "
            f"({_yes_no(ceo['passed'])}; {ceo['rows']:,} rows). "
            f"FAT_FINGER_MISTAKE median USD_AMOUNT = "
            f"${_number(fat_quantiles.get('median'), 2)}; "
            f"1.5×IQR upper fence = ${_number(outliers['iqr_upper_fence'], 2)}, "
            f"with {outliers['high_outlier_count']:,} high outliers. "
            "Blank ANOMALY_TYPE values are counted as NORMAL."
        )

        labels = [name for name in ANOMALY_ORDER if name in summaries]
        counts = [summaries[name]["count"] for name in labels]
        anomaly_labels = [name for name in labels if name != "NORMAL"]
        figure = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Transactions by anomaly class · log count", "Anomaly USD_AMOUNT quartiles · log scale"),
            row_heights=[0.37, 0.63],
            vertical_spacing=0.2,
        )
        figure.add_trace(
            go.Bar(
                x=labels,
                y=counts,
                marker_color=[
                    COLORS["slate"] if name == "NORMAL" else COLORS["coral"]
                    for name in labels
                ],
                text=[f"{count:,}" for count in counts],
                textposition="outside",
                showlegend=False,
                hovertemplate="%{x}<br>Transactions: %{y:,}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        for field, color, label in (
            ("p25", COLORS["blue"], "p25"),
            ("median", COLORS["gold"], "Median"),
            ("p75", COLORS["coral"], "p75"),
        ):
            values = [
                summaries[name]["usd_amount_quantiles"].get(field)
                for name in anomaly_labels
            ]
            figure.add_trace(
                go.Scatter(
                    x=anomaly_labels,
                    y=values,
                    mode="lines+markers",
                    name=label,
                    line={"color": color, "width": 2},
                    marker={"size": 7},
                    connectgaps=False,
                    hovertemplate=(
                        f"%{{x}}<br>{label}: $%{{y:,.2f}}<extra></extra>"
                    ),
                ),
                row=2,
                col=1,
            )
        figure.update_yaxes(type="log", title_text="Transactions", row=1, col=1)
        figure.update_yaxes(
            type="log", title_text="USD_AMOUNT ($)", row=2, col=1
        )
        figure.update_xaxes(title_text="ANOMALY_TYPE", tickangle=-22, row=1, col=1)
        figure.update_xaxes(title_text="ANOMALY_TYPE", tickangle=-22, row=2, col=1)
        figure.update_layout(height=470, barmode="group")
        _show_figure(
            _polish_figure(figure, "Anomaly prevalence and amount signatures", 470),
            "anomaly-signatures",
        )
        _interpretation(
            "Romance and executive-impersonation cases exploit different trust relationships, which is consistent with "
            "their observed customer-versus-business ordering-party constraints. Recall, duplicate, account-replacement, "
            "and input-error labels are distinct operational signals; an unusual amount is a review cue, not proof of fraud."
        )


def render_tokens(data: dict[str, Any]) -> None:
    token_data = data["feature_group_6_tokenized_party_details"][
        "frequency_and_transaction_counts_by_role_type_and_token"
    ]

    with _section_container(6):
        _section_header(6, "Party Identity & Tokenized Text Patterns")
        _rule_callout(
            "<b>Token frequency = occurrences of &lt;iban:…&gt;, "
            "&lt;business:…&gt;, and &lt;first_name:…&gt;</b>, grouped by "
            "ORDERING_TYPE or BENEFICIARY_TYPE (B/C). Hover for the number of "
            "transactions containing each token; ordering and beneficiary roles "
            "are shown separately."
        )
        figure = make_subplots(
            rows=1,
            cols=2,
            subplot_titles=("Ordering-party tokens", "Beneficiary-party tokens"),
            horizontal_spacing=0.12,
        )
        type_colors = {"B": COLORS["blue"], "C": COLORS["teal"]}
        for column, role in enumerate(("ordering", "beneficiary"), start=1):
            role_data = token_data.get(role, {})
            for party_type in ("B", "C"):
                type_data = role_data.get(party_type, {})
                frequencies = [
                    type_data.get(token, {}).get("frequency", 0)
                    for token in TOKEN_NAMES
                ]
                transactions = [
                    type_data.get(token, {}).get("transactions_with_token", 0)
                    for token in TOKEN_NAMES
                ]
                figure.add_trace(
                    go.Bar(
                        x=TOKEN_NAMES,
                        y=frequencies,
                        name=f"Type {party_type}",
                        marker_color=type_colors[party_type],
                        customdata=transactions,
                        hovertemplate=(
                            "%{x}<br>Token occurrences: %{y:,}"
                            "<br>Transactions containing token: %{customdata:,}"
                            "<extra></extra>"
                        ),
                    ),
                    row=1,
                    col=column,
                )
        figure.update_yaxes(title_text="Token occurrences", row=1, col=1)
        figure.update_yaxes(title_text="Token occurrences", row=1, col=2)
        figure.update_xaxes(title_text="Token class", row=1, col=1)
        figure.update_xaxes(title_text="Token class", row=1, col=2)
        figure.update_layout(barmode="group", height=390)
        _show_figure(
            _polish_figure(figure, "Token frequencies by party role and type"),
            "party-tokens",
        )
        _interpretation(
            "IBAN tokens identify account references, while business names and personal names help distinguish legal entities "
            "from individual customers in payment narratives. Differences in token frequency can reflect both party mix and "
            "how much structured remittance information institutions supply."
        )


if not SUMMARY_PATH.is_file():
    st.error(
        f"Dashboard summary not found at {SUMMARY_PATH}. "
        "Run src/02_etl_aggregator.py first."
    )
    st.stop()

summary_stat = SUMMARY_PATH.stat()
summary = load_summary(str(SUMMARY_PATH), summary_stat.st_mtime_ns)
metadata = summary["metadata"]

st.markdown('<div class="report-kicker">UMDAC Datathon 2026 · Preliminary Round</div>', unsafe_allow_html=True)
st.markdown('<h1 class="report-title">Swift Payments: Routing, Settlement & Risk</h1>', unsafe_allow_html=True)
st.markdown(
    '<div class="report-subtitle">An evidence-led reconstruction of routing, '
    "FX latency, temporal rhythms, currency corridors, anomaly signatures, and "
    "party-text patterns.</div>",
    unsafe_allow_html=True,
)
metric_columns = st.columns(4)
metric_columns[0].metric("Transactions", f"{metadata['total_rows']:,}")
metric_columns[1].metric("Input parts", metadata["source_file_count"])
metric_columns[2].metric(
    "Direct routes",
    f"{summary['feature_group_1_routing_topology']['rule_checks']['direct_has_exactly_two_participants']['rows']:,}",
)
metric_columns[3].metric(
    "Anomaly-labelled",
    f"{metadata['total_rows'] - summary['feature_group_5_anomaly_fraud_signatures']['by_anomaly_type']['NORMAL']['count']:,}",
)
st.caption(
    "Source: dashboard/data/part_*.csv · "
    "Summary: dashboard/output/dashboard_summary.json · "
    "Use Chrome Print → Save as PDF for the six-section executive report."
)
st.divider()

render_routing(summary)
render_fx(summary)
render_temporal(summary)
render_corridors(summary)
render_anomalies(summary)
render_tokens(summary)
