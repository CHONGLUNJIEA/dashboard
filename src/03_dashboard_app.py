"""Streamlit dashboard for the UMDAC Datathon 2026 Swift payments analysis."""

from __future__ import annotations

import json
import math
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
    .stPlotlyChart {
        background: #FFFFFF; border-radius: 7px;
        box-shadow: 0 0 0 1px var(--line); padding: 0;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid var(--line); border-radius: 7px;
        padding: .65rem .8rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--ink) !important;
    }
    [data-testid="stWidgetLabel"],
    [data-testid="stWidgetLabel"] *,
    [role="listbox"] [role="option"] {
        color: var(--ink) !important;
    }
    [data-testid="stSelectbox"] [role="combobox"] {
        color: #EDEBE8 !important;
    }
    [role="listbox"] { background-color: #FFFFFF !important; }
    [role="listbox"] [role="option"]:hover,
    [role="listbox"] [role="option"][aria-selected="true"] {
        background-color: #EAF4F8 !important;
    }
    @media print {
        @page { size: A4 landscape; margin: 0.38in; }
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: #FFFFFF !important; color: #172B3A !important;
            -webkit-print-color-adjust: exact; print-color-adjust: exact;
        }
        html, body, #root, .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stMain"], [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            height: auto !important; min-height: 0 !important;
            max-height: none !important; overflow: visible !important;
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
        div[class*="st-key-fx-heatmap-filter"] {
            display: none !important;
        }
        .stPlotlyChart, [data-testid="stPlotlyChart"], figure,
        .rule-card, .interpretation-card {
            break-inside: avoid !important;
            page-break-inside: avoid !important;
        }
        .stPlotlyChart {
            background: #FFFFFF !important; border: 0 !important;
            box-shadow: none !important; padding: 0 !important;
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


def _evidence_callout(title: str, text: str) -> None:
    st.markdown(
        f'<div class="rule-card"><strong>{title}</strong>'
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


def _show_figure(figure: go.Figure, key: str, alt: str) -> None:
    st.plotly_chart(
        figure,
        alt=alt,
        theme=None,
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
        _evidence_callout(
            "Dataset validation",
            "Observed structure is consistent with the payment-type definitions: "
            f"Direct routes have exactly 2 participants "
            f"({_yes_no(direct_check['passed'])}, "
            f"{_number(direct_check['rows'])} rows); "
            "Indirect/Covered routes have at least 3 participants "
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
        figure = _polish_figure(
            figure, "Participants by route type and continuity"
        )
        figure.update_layout(
            title={"text": "Participants by route type and continuity", "x": 0.5, "xanchor": "center"},
            margin={"l": 165, "r": 45, "t": 75, "b": 70},
        )
        figure.update_xaxes(
            title_font={"color": COLORS["navy"]},
            tickfont={"color": COLORS["navy"]},
        )
        figure.update_yaxes(
            title_font={"color": COLORS["navy"]},
            tickfont={"color": COLORS["navy"]},
        )
        _show_figure(
            figure,
            "routing",
            "Direct routes have two participants; Indirect and Covered routes have at least three.",
        )
        _interpretation(
            "Direct payments usually travel between an ordering institution and a beneficiary institution, "
            "so a two-participant route is structurally expected. Indirect and covered payments involve "
            "intermediaries or cover arrangements, which add participants and routing complexity."
        )


def render_fx(data: dict[str, Any]) -> None:
    section = data["feature_group_2_fx_settlement_latency"]
    rows = section["by_transaction_type_and_currency_conversion_count"]
    participant_fx_rows = section[
        "by_transaction_type_participant_count_and_fx_count"
    ]
    check = section["direct_fx_rule"]
    ratios = {
        row["transaction_type_code"]: row
        for row in section["median_latency_comparison_fx_gte_3_vs_lt_3"]
    }
    indirect_ratio = ratios.get("Indirect", {}).get("gte_3_to_lt_3_median_ratio")
    covered_ratio = ratios.get("Covered", {}).get("gte_3_to_lt_3_median_ratio")
    controlled_cohort = {
        row["currency_conversion_count"]: row
        for row in participant_fx_rows
        if row["transaction_type_code"] == "Indirect"
        and row["participant_count"] == 4
        and row["currency_conversion_count"] in (1, 3)
    }
    if set(controlled_cohort) != {1, 3}:
        raise ValueError(
            "Expected Indirect payments with four participants and one and "
            "three FX conversions in the controlled duration summary."
        )
    low_sample_high_fx = [
        row
        for row in rows
        if row["currency_conversion_count"] is not None
        and row["currency_conversion_count"] >= 8
        and row["count"] < 30
    ]
    low_sample_summary = "; ".join(
        f"{row['transaction_type_code']} at {row['currency_conversion_count']} "
        f"conversions (n={row['count']:,})"
        for row in low_sample_high_fx
    ) or "none"
    frame = pd.DataFrame(rows).dropna(
        subset=["currency_conversion_count", "median"]
    )

    with _section_container(2):
        _section_header(2, "Foreign Exchange (FX) Steps & Settlement Latency")
        _evidence_callout(
            "Inferred relationship (observational, not causal)",
            "Controlled cohort (Indirect; exactly 4 participants; n = valid "
            "duration records): median "
            "TOTAL_DURATION is "
            f"{_number(controlled_cohort[1]['median'], 1)} (n="
            f"{_number(controlled_cohort[1]['count'])}) at 1 conversion versus "
            f"{_number(controlled_cohort[3]['median'], 1)} (n="
            f"{_number(controlled_cohort[3]['count'])}) at 3 conversions; "
            "this fixed-participant cohort does not show an increase. "
            "Across route types, at ≥3 FX steps versus &lt;3, median "
            "TOTAL_DURATION rises from "
            f"{_number(ratios['Indirect']['median_fx_lt_3'])} to "
            f"{_number(ratios['Indirect']['median_fx_gte_3'])} for Indirect "
            f"({_number(indirect_ratio, 2)}×), and from "
            f"{_number(ratios['Covered']['median_fx_lt_3'])} to "
            f"{_number(ratios['Covered']['median_fx_gte_3'])} for Covered "
            f"({_number(covered_ratio, 2)}×). "
            "The pooled association may reflect route mix and is not consistent "
            "within every fixed-participant cohort. Direct has no "
            "observations with ≥3 FX steps. This is a measured association, "
            f"not a causal claim. Dataset validation: Direct's maximum was "
            f"{section['direct_max_fx_steps']} FX step(s) "
            f"({_yes_no(check['passed'])}). High-FX groups (≥8 conversions) "
            f"with n &lt; 30 are low-confidence: {low_sample_summary}."
        )

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
            low_sample = subset["count"] < 30
            customdata = subset[["count", "mean"]].copy()
            customdata["sample_note"] = low_sample.map(
                {True: "low confidence (n < 30)", False: "n ≥ 30"}
            )
            figure.add_trace(
                go.Scatter(
                    x=subset["currency_conversion_count"],
                    y=median,
                    mode="lines+markers",
                    name=transaction_type,
                    line={"color": color, "width": 3},
                    marker={
                        "size": 8,
                        "symbol": [
                            "circle-open" if is_low else "circle"
                            for is_low in low_sample
                        ],
                    },
                    error_y={
                        "type": "data",
                        "symmetric": False,
                        "array": (subset["p75"].astype(float) - median).clip(lower=0),
                        "arrayminus": (median - subset["p25"].astype(float)).clip(lower=0),
                        "color": color,
                        "thickness": 1.5,
                        "width": 4,
                    },
                    customdata=customdata.to_numpy(),
                    hovertemplate=(
                        f"{transaction_type}<br>FX steps: %{{x}}"
                        "<br>Median duration: %{y:,.1f}"
                        "<br>IQR: p25–p75"
                        "<br>n (valid durations): %{customdata[0]:,}"
                        "<br>Mean duration: %{customdata[1]:,.1f}"
                        "<br>Sample note: %{customdata[2]}<extra></extra>"
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
            "At four participants, Indirect median duration is lower at three FX steps than one; pooled latency differs by route type.",
        )
        st.caption(
            "Open markers and hover labels identify low-confidence groups "
            "(n < 30); n counts records with a valid TOTAL_DURATION."
        )

        st.markdown("#### Duration by participant count and FX conversions")
        with st.container(key="fx-heatmap-filter"):
            selected_type = st.segmented_control(
                "Transaction type",
                options=["Indirect", "Direct", "Covered"],
                default="Indirect",
                key="fx_heatmap_transaction_type",
            )

        participant_fx_frame = pd.DataFrame(participant_fx_rows)
        selected_rows = participant_fx_frame.loc[
            participant_fx_frame["transaction_type_code"].eq(selected_type)
        ]
        if selected_rows.empty:
            st.info("No participant-duration data is available for this transaction type.")
        else:
            median_matrix = selected_rows.pivot(
                index="currency_conversion_count",
                columns="participant_count",
                values="median",
            ).sort_index().sort_index(axis=1)
            count_matrix = selected_rows.pivot(
                index="currency_conversion_count",
                columns="participant_count",
                values="count",
            ).reindex(
                index=median_matrix.index,
                columns=median_matrix.columns,
            )
            median_values = median_matrix.to_numpy(dtype=float)
            count_values = count_matrix.to_numpy(dtype=float)
            z_values = [
                [
                    math.log10(value)
                    if pd.notna(value) and value > 0
                    else None
                    for value in row
                ]
                for row in median_values
            ]
            cell_text = [
                [
                    f"{value:,.1f}" if pd.notna(value) else ""
                    for value in row
                ]
                for row in median_values
            ]
            customdata = [
                [
                    [median, count] if pd.notna(median) else [None, None]
                    for median, count in zip(median_row, count_row)
                ]
                for median_row, count_row in zip(median_values, count_values)
            ]
            valid_medians = median_values[pd.notna(median_values)]
            valid_medians = valid_medians[valid_medians > 0]
            min_duration = float(valid_medians.min())
            max_duration = float(valid_medians.max())
            zmin = math.log10(min_duration)
            zmax = math.log10(max_duration)
            if zmin == zmax:
                zmax = zmin + 0.01
                colorbar_values = [min_duration]
            else:
                colorbar_values = [
                    min_duration,
                    math.sqrt(min_duration * max_duration),
                    max_duration,
                ]

            figure = go.Figure(
                go.Heatmap(
                    z=z_values,
                    x=[int(value) for value in median_matrix.columns],
                    y=[int(value) for value in median_matrix.index],
                    customdata=customdata,
                    text=cell_text,
                    texttemplate="%{text}",
                    textfont={"color": COLORS["navy"], "size": 10},
                    colorscale="Blues",
                    zmin=zmin,
                    zmax=zmax,
                    hoverongaps=False,
                    colorbar={
                        "title": "Median duration<br>(log scale)",
                        "tickvals": [math.log10(value) for value in colorbar_values],
                        "ticktext": [f"{value:,.0f}" for value in colorbar_values],
                    },
                    hovertemplate=(
                        "Participants: %{x}<br>FX conversions: %{y}"
                        "<br>Median TOTAL_DURATION: %{customdata[0]:,.1f}"
                        "<br>n (valid durations): %{customdata[1]:,}"
                        "<extra></extra>"
                    ),
                )
            )
            figure.update_xaxes(
                title_text="Participant count",
                dtick=1,
                tickmode="linear",
            )
            figure.update_yaxes(
                title_text="Currency conversion count",
                dtick=1,
                tickmode="linear",
            )
            _show_figure(
                _polish_figure(
                    figure,
                    f"{selected_type} duration by participants and FX conversions",
                    height=430,
                ),
                "participant-fx-duration",
                f"Median payment duration by participant and currency-conversion "
                f"counts for {selected_type} transactions",
            )
        st.caption(
            "Each cell shows the median TOTAL_DURATION; hover for the number "
            "of records with valid durations. Blank cells have no observations. "
            "The color scale is logarithmic."
        )
        _interpretation(
            "Every currency conversion can add pricing, liquidity, correspondent-bank, and settlement coordination. "
            "Longer multi-currency chains therefore tend to take more time, although the measured latency also "
            "reflects cut-off times, market hours, and payment-specific controls."
        )


def render_temporal(data: dict[str, Any]) -> None:
    section = data["feature_group_3_temporal_circadian_patterns"]
    frame = pd.DataFrame(section["by_hour_day_ordering_type_and_currency"])
    currencies = sorted(section["top_currencies"])
    volume_values = frame["count"].dropna()
    amount_values = frame["median"].dropna()
    volume_max = max(float(volume_values.max()), 1.0) if not volume_values.empty else 1.0
    amount_max = max(float(amount_values.max()), 1.0) if not amount_values.empty else 1.0
    volume_matrix = []
    amount_matrix = []
    volume_hover_data = []
    amount_hover_data = []
    y_group_ticks = []
    y_group_labels = []
    for currency in currencies:
        for ordering_type in ("B", "C"):
            y_group_ticks.append(len(volume_matrix) + 3)
            y_group_labels.append(f"{currency} · {ordering_type}")
            type_rows = frame.loc[
                frame["currency_code"].eq(currency)
                & frame["ordering_type"].eq(ordering_type)
            ]
            for day in range(7):
                day_rows = type_rows.loc[
                    type_rows["utc_day_of_week"].eq(day)
                ].set_index("utc_hour_of_day")
                counts = (
                    day_rows["count"]
                    .reindex(range(24))
                    .fillna(0)
                    .astype(float)
                    .tolist()
                )
                amounts = (
                    day_rows["median"]
                    .reindex(range(24))
                    .astype(float)
                    .tolist()
                )
                volume_matrix.append(counts)
                amount_matrix.append(amounts)
                volume_hover_data.append(
                    [
                        [currency, ordering_type, DAY_NAMES[day], hour]
                        for hour in range(24)
                    ]
                )
                amount_hover_data.append(
                    [
                        [currency, ordering_type, DAY_NAMES[day], hour]
                        for hour in range(24)
                    ]
                )

    with _section_container(3):
        _section_header(3, "Temporal Dynamics & Working-Hour Rhythms")
        figure = go.Figure()
        figure.add_trace(
            go.Heatmap(
                z=volume_matrix,
                x=list(range(24)),
                y=list(range(len(volume_matrix))),
                coloraxis="coloraxis",
                customdata=volume_hover_data,
                hovertemplate=(
                    "%{customdata[0]} · ORDERING_TYPE %{customdata[1]}"
                    "<br>Weekday: %{customdata[2]}"
                    "<br>UTC hour: %{customdata[3]}:00"
                    "<br>Transaction volume: %{z:,.0f}<extra></extra>"
                ),
            )
        )
        figure.add_trace(
            go.Heatmap(
                z=amount_matrix,
                x=list(range(24, 48)),
                y=list(range(len(amount_matrix))),
                coloraxis="coloraxis2",
                customdata=amount_hover_data,
                hovertemplate=(
                    "%{customdata[0]} · ORDERING_TYPE %{customdata[1]}"
                    "<br>Weekday: %{customdata[2]}"
                    "<br>UTC hour: %{customdata[3]}:00"
                    "<br>Median USD amount: %{z:,.2f}<extra></extra>"
                ),
            )
        )
        figure = _polish_figure(
            figure,
            "Temporal patterns · All currencies, measures, and ordering types",
            height=490,
        )
        figure.update_layout(
            font={"family": "Arial, sans-serif", "color": COLORS["navy"], "size": 8},
            margin={"l": 115, "r": 20, "t": 95, "b": 100},
            coloraxis={
                "colorscale": "Teal",
                "cmin": 0,
                "cmax": volume_max,
                "colorbar": {
                    "title": {"text": "Transaction volume", "side": "top"},
                    "orientation": "h",
                    "x": 0.27,
                    "xanchor": "center",
                    "y": -0.22,
                    "len": 0.4,
                    "thickness": 8,
                    "tickfont": {"size": 7},
                },
            },
            coloraxis2={
                "colorscale": "Teal",
                "cmin": 0,
                "cmax": amount_max,
                "colorbar": {
                    "title": {"text": "Median USD amount", "side": "top"},
                    "orientation": "h",
                    "x": 0.73,
                    "xanchor": "center",
                    "y": -0.22,
                    "len": 0.4,
                    "thickness": 8,
                    "tickfont": {"size": 7},
                },
            },
            title={
                "text": "Temporal patterns · All currencies, measures, and ordering types",
                "x": 0.02,
                "y": 1.0,
                "xanchor": "left",
                "yanchor": "top",
            },
        )
        figure.update_xaxes(
            title_text="UTC hour of day",
            tickmode="array",
            tickvals=[0, 6, 12, 18, 24, 30, 36, 42],
            ticktext=["00", "06", "12", "18", "00", "06", "12", "18"],
            range=[-3.5, 47.5],
            showgrid=False,
        )
        figure.update_yaxes(
            type="linear",
            title_text="Currency · ORDERING_TYPE",
            tickmode="array",
            tickvals=y_group_ticks,
            ticktext=y_group_labels,
            autorange="reversed",
            tickfont={"size": 7},
            showgrid=False,
        )
        figure.add_annotation(
            text="Transaction volume",
            x=11.5,
            y=1.03,
            xref="x",
            yref="paper",
            showarrow=False,
            font={"size": 9, "color": COLORS["navy"]},
        )
        figure.add_annotation(
            text="Median USD amount",
            x=35.5,
            y=1.03,
            xref="x",
            yref="paper",
            showarrow=False,
            font={"size": 9, "color": COLORS["navy"]},
        )
        figure.add_shape(
            type="line",
            x0=23.5,
            x1=23.5,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line={"color": "#FFFFFF", "width": 2},
        )
        for boundary in range(7, len(volume_matrix), 7):
            figure.add_shape(
                type="line",
                x0=-0.5,
                x1=47.5,
                y0=boundary - 0.5,
                y1=boundary - 0.5,
                xref="x",
                yref="y",
                line={"color": "#FFFFFF", "width": 1},
            )
        _show_figure(
            figure,
            "temporal-patterns",
            "One heatmap with all currencies, weekday patterns, transaction volume, median amount, and B/C types.",
        )
        st.caption(
            f"All currencies: {', '.join(currencies)}. Rows group currency and B/C "
            "(each 7-row block runs Monday–Sunday); left band: transaction volume, "
            "right band: median USD. Each band has its own raw-value scale."
        )


def render_corridors(data: dict[str, Any]) -> None:
    section = data["feature_group_4_currency_corridor_alignment"]
    alignment = section["country_currency_matches_by_role"]
    corridors = section["usd_amount_by_ordering_to_beneficiary_type"]
    ordering_rate = alignment["ordering"]["match_rate"]
    beneficiary_rate = alignment["beneficiary"]["match_rate"]

    with _section_container(4):
        _section_header(4, "Currency Corridors & Party-Type Value Flows")
        _evidence_callout(
            "Comparison method",
            f"<b>BIC country = BIC8[4:6]</b>; a match is an observed currency equal "
            "to the mapped country currency (including Eurozone → EUR). Rates are "
            "matched rows ÷ comparable rows: ordering "
            f"{_number(alignment['ordering']['match_rows'])} / "
            f"{_number(alignment['ordering']['comparable_rows'])} = "
            f"{_percent(ordering_rate)}; beneficiary "
            f"{_number(alignment['beneficiary']['match_rows'])} / "
            f"{_number(alignment['beneficiary']['comparable_rows'])} = "
            f"{_percent(beneficiary_rate)}. "
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
        role_counts = [
            [
                alignment[role]["match_rows"],
                alignment[role]["comparable_rows"],
            ]
            for role in roles
        ]
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
                    "<br>Matched rows: %{customdata[0]:,}"
                    "<br>Comparable rows: %{customdata[1]:,}<extra></extra>"
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
            "Ordering BICs match mapped currencies more often than beneficiary BICs; corridor amounts vary by party type.",
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
    customer_recall_count = summaries.get("CUSTOMER_RECALL", {}).get("count", 0)

    with _section_container(5):
        _section_header(5, "Anomaly Labels, Party Types & Amount Signals")
        _evidence_callout(
            "Dataset validation",
            "Observed structure is consistent with the anomaly definitions: "
            f"all {romance['rows']:,} Romance Scam rows have ORDERING_TYPE=C "
            f"({_yes_no(romance['passed'])}); all {ceo['rows']:,} CEO Scam rows "
            f"have ORDERING_TYPE=B ({_yes_no(ceo['passed'])}). "
            f"Exploratory amount signal: FAT_FINGER_MISTAKE median USD_AMOUNT = "
            f"${_number(fat_quantiles.get('median'), 2)}; "
            f"1.5×IQR upper fence = ${_number(outliers['iqr_upper_fence'], 2)}, "
            f"with {outliers['high_outlier_count']:,} high outliers. "
            "Blank ANOMALY_TYPE values are counted as NORMAL; outliers are review "
            "signals, not confirmed fraud. Specification discrepancy: "
            f"CUSTOMER_RECALL occurs in {customer_recall_count:,} dataset rows "
            "but is not among the five anomaly examples listed in the case-study "
            "brief; it is retained as an observed category, not dropped."
        )

        labels = [name for name in ANOMALY_ORDER if name in summaries]
        counts = [summaries[name]["count"] for name in labels]
        anomaly_labels = [name for name in labels if name != "NORMAL"]
        count_figure = go.Figure(
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
            )
        )
        count_figure.update_yaxes(type="log", title_text="Transactions")
        count_figure.update_xaxes(tickangle=-35, automargin=True)
        count_figure = _polish_figure(
            count_figure, "Transactions by anomaly class · log count", 390
        )
        count_figure.update_layout(
            margin={"l": 75, "r": 30, "t": 80, "b": 135},
            showlegend=False,
        )
        _show_figure(
            count_figure,
            "anomaly-counts",
            "Transaction counts by anomaly class; NORMAL is the largest group.",
        )

        ordering_types_found = {
            party_type
            for name in labels
            for party_type in summaries[name][
                "ordering_type_to_beneficiary_type"
            ]
        }
        party_types = [
            party_type
            for party_type in ("B", "C", "UNKNOWN")
            if party_type in ordering_types_found
        ]
        party_colors = {
            "B": COLORS["blue"],
            "C": COLORS["teal"],
            "UNKNOWN": COLORS["slate"],
        }
        party_figure = go.Figure()
        for party_type in party_types:
            party_shares = []
            hover_counts = []
            for name in labels:
                breakdown = summaries[name]["ordering_type_to_beneficiary_type"]
                count = sum(breakdown.get(party_type, {}).values())
                total = summaries[name]["count"]
                party_shares.append(100 * count / total if total else 0)
                hover_counts.append([count, total])
            party_figure.add_trace(
                go.Bar(
                    x=labels,
                    y=party_shares,
                    name=f"ORDERING_TYPE {party_type}",
                    marker_color=party_colors.get(party_type, COLORS["slate"]),
                    customdata=hover_counts,
                    text=[
                        f"{share:.0f}%" if share >= 5 else ""
                        for share in party_shares
                    ],
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont={"size": 12, "color": "#FFFFFF"},
                    hovertemplate=(
                        "%{x}<br>ORDERING_TYPE "
                        + party_type
                        + ": %{customdata[0]:,} (%{y:.1f}%)"
                        "<br>Anomaly records: %{customdata[1]:,}<extra></extra>"
                    ),
                ),
            )
        party_figure.update_layout(barmode="stack")
        party_figure.update_yaxes(
            title_text="Share within anomaly class (%)", range=[0, 100]
        )
        party_figure.update_xaxes(tickangle=-35, automargin=True)
        party_figure = _polish_figure(
            party_figure,
            "Ordering party type by anomaly class · 100% stacked",
            430,
        )
        party_figure.update_layout(
            margin={"l": 85, "r": 30, "t": 90, "b": 140},
            legend={
                "orientation": "h",
                "x": 1,
                "xanchor": "right",
                "y": 1.02,
                "yanchor": "bottom",
            },
        )
        _show_figure(
            party_figure,
            "anomaly-party-type",
            "Romance Scam is all consumer ordering parties; CEO Scam is all business ordering parties.",
        )
        st.caption(
            "The 100% stacked bars show ordering-party type within each anomaly "
            "class (B = business, C = consumer); hover reports the supporting "
            "row counts."
        )

        amount_figure = go.Figure()
        for field, color, label in (
            ("p25", COLORS["blue"], "p25"),
            ("median", COLORS["gold"], "Median"),
            ("p75", COLORS["coral"], "p75"),
        ):
            values = [
                summaries[name]["usd_amount_quantiles"].get(field)
                for name in anomaly_labels
            ]
            amount_figure.add_trace(
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
                )
            )
        amount_figure.update_yaxes(
            type="log", title_text="USD_AMOUNT ($)"
        )
        amount_figure.update_xaxes(tickangle=-35, automargin=True)
        amount_figure = _polish_figure(
            amount_figure, "Anomaly USD_AMOUNT quartiles · log scale", 430
        )
        amount_figure.update_layout(
            margin={"l": 80, "r": 30, "t": 90, "b": 140},
            legend={
                "orientation": "h",
                "x": 1,
                "xanchor": "right",
                "y": 1.12,
                "yanchor": "bottom",
            },
        )
        _show_figure(
            amount_figure,
            "anomaly-amount-quartiles",
            "Amount quartiles vary across anomaly classes, with the largest values in selected classes.",
        )
        _interpretation(
            "The ordering-party breakdown directly shows Romance Scam rows as consumer (C) and CEO Scam rows as business (B). "
            "CUSTOMER_RECALL is preserved as an additional dataset label pending clarification of the brief/data discrepancy. "
            "An unusual amount remains a review cue, not proof of fraud."
        )


def render_tokens(data: dict[str, Any]) -> None:
    section = data["feature_group_6_tokenized_party_details"]
    token_data = section[
        "frequency_and_transaction_counts_by_role_type_and_token"
    ]
    record_counts = section["record_counts_by_party_type"]
    ordering_business_records = record_counts["ordering"].get("B", 0)
    ordering_consumer_records = record_counts["ordering"].get("C", 0)
    ordering_business_token_count = token_data["ordering"]["B"]["business"][
        "transactions_with_token"
    ]
    ordering_consumer_business_token_count = token_data["ordering"]["C"][
        "business"
    ]["transactions_with_token"]
    business_token_rate = (
        ordering_business_token_count / ordering_business_records * 1000
        if ordering_business_records
        else None
    )
    consumer_business_token_rate = (
        ordering_consumer_business_token_count / ordering_consumer_records * 1000
        if ordering_consumer_records
        else None
    )
    business_token_comparison = (
        "The consumer baseline is zero, so a finite B-to-C rate ratio is undefined."
        if consumer_business_token_rate == 0
        else (
            "The B-to-C rate ratio is "
            f"{_number(business_token_rate / consumer_business_token_rate, 2)}×."
            if business_token_rate is not None
            and consumer_business_token_rate is not None
            else "A B-to-C rate ratio is unavailable because a party-type denominator is zero."
        )
    )

    with _section_container(6):
        _section_header(6, "Party Identity & Tokenized Text Patterns")
        _evidence_callout(
            "Normalized token evidence",
            "Rate = transactions containing a token ÷ all records in that role "
            "and party type × 1,000. For ordering-party &lt;business:...&gt; "
            f"tokens: B (business) {_number(business_token_rate, 2)} per 1,000 "
            f"records ({ordering_business_token_count:,}/{ordering_business_records:,}); "
            f"C (consumer) {_number(consumer_business_token_rate, 2)} per 1,000 "
            f"records ({ordering_consumer_business_token_count:,}/"
            f"{ordering_consumer_records:,}). {business_token_comparison}"
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
            role_record_counts = record_counts.get(role, {})
            for party_type in ("B", "C"):
                type_data = role_data.get(party_type, {})
                denominator = role_record_counts.get(party_type, 0)
                transactions = [
                    type_data.get(token, {}).get("transactions_with_token", 0)
                    for token in TOKEN_NAMES
                ]
                frequencies = [
                    type_data.get(token, {}).get("frequency", 0)
                    for token in TOKEN_NAMES
                ]
                rates = [
                    count / denominator * 1000 if denominator else None
                    for count in transactions
                ]
                hover_data = [
                    [count, denominator, frequency]
                    for count, frequency in zip(transactions, frequencies)
                ]
                figure.add_trace(
                    go.Bar(
                        x=TOKEN_NAMES,
                        y=rates,
                        name=f"Type {party_type}",
                        legendgroup=party_type,
                        showlegend=column == 1,
                        marker_color=type_colors[party_type],
                        customdata=hover_data,
                        hovertemplate=(
                            "%{x}<br>Transactions per 1,000 records: %{y:.2f}"
                            "<br>Transactions containing token: "
                            "%{customdata[0]:,} / %{customdata[1]:,}"
                            "<br>Raw token occurrences: %{customdata[2]:,}"
                            "<extra></extra>"
                        ),
                    ),
                    row=1,
                    col=column,
                )
        figure.update_yaxes(
            title_text="Transactions per 1,000 records", row=1, col=1
        )
        figure.update_yaxes(
            title_text="Transactions per 1,000 records", row=1, col=2
        )
        figure.update_xaxes(title_text="Token class", row=1, col=1)
        figure.update_xaxes(title_text="Token class", row=1, col=2)
        figure.update_layout(barmode="group")
        figure = _polish_figure(
            figure, "Token prevalence per 1,000 party-type records", 440
        )
        figure.update_layout(
            margin={"l": 58, "r": 30, "t": 105, "b": 60},
            legend={
                "orientation": "h",
                "x": 1,
                "xanchor": "right",
                "y": 1.12,
                "yanchor": "bottom",
            },
        )
        _show_figure(
            figure,
            "party-tokens",
            "Token-containing transaction rates per 1,000 party-type records for ordering and beneficiary roles.",
        )
        st.caption(
            "B = business; C = consumer. Rates count each record at most once "
            "per token; hover also shows raw token occurrences."
        )
        _interpretation(
            "Per-1,000 rates normalize for different business and consumer record counts. In this dataset the ordering-party "
            "<business:...> token appears only in B records; because the observed C rate is zero, report the two rates rather "
            "than a finite relative-rate multiplier."
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
st.divider()

render_routing(summary)
render_fx(summary)
render_temporal(summary)
render_corridors(summary)
render_anomalies(summary)
render_tokens(summary)
