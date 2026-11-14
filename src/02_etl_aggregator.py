"""Aggregate Swift payments CSV parts into dashboard-ready statistics."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


CHUNK_SIZE = 100_000
TOP_CURRENCIES = {"EUR", "USD", "GBP", "CHF", "SGD", "CNY"}
ANOMALY_CLASSES = [
    "NORMAL",
    "ROMANCE_SCAM",
    "FAT_FINGER_MISTAKE",
    "CEO_SCAM",
    "ACCOUNT_REPLACEMENT_SCAM",
    "DUPLICATE_PAYMENT",
    "CUSTOMER_RECALL",
]
TOKEN_TYPES = ("iban", "business", "first_name")
TOKEN_PATTERN = {name: re.compile(rf"(?i)<{name}:") for name in TOKEN_TYPES}
EUROZONE_COUNTRIES = {
    "AT", "BE", "BG", "CY", "DE", "EE", "ES", "FI", "FR", "GR", "HR",
    "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PT", "SI", "SK",
}
COUNTRY_CURRENCY = {
    **{country: "EUR" for country in EUROZONE_COUNTRIES},
    "US": "USD",
    "GB": "GBP",
    "CH": "CHF",
    "SG": "SGD",
    "CN": "CNY",
    "JP": "JPY",
    "AU": "AUD",
    "KR": "KRW",
    "HK": "HKD",
    "TR": "TRY",
    "AE": "AED",
    "CA": "CAD",
    "NZ": "NZD",
    "IN": "INR",
    "SE": "SEK",
    "NO": "NOK",
    "DK": "DKK",
    "PL": "PLN",
    "CZ": "CZK",
    "HU": "HUF",
    "ZA": "ZAR",
    "BR": "BRL",
    "MX": "MXN",
    "TH": "THB",
    "ID": "IDR",
    "MY": "MYR",
    "PH": "PHP",
    "SA": "SAR",
    "IL": "ILS",
    "RU": "RUB",
    "UA": "UAH",
    "RO": "RON",
}
REQUIRED_COLUMNS = [
    "EPOCH_SECONDS",
    "CURRENCY_CODE",
    "USD_AMOUNT",
    "ORDERING_BIC8",
    "BENEFICIARY_BIC8",
    "TOTAL_DURATION",
    "CONTINUITY_QFLAG",
    "CURRENCY_CONVERSION_COUNT",
    "PARTICIPANT_COUNT",
    "TRANSACTION_TYPE_CODE",
    "ORDERING_TOKENS",
    "BENEFICIARY_TOKENS",
    "ORDERING_TYPE",
    "BENEFICIARY_TYPE",
    "ANOMALY_TYPE",
]


def _python_value(value: Any) -> Any:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, np.generic):
        return _python_value(value.item())
    if isinstance(value, np.ndarray):
        return [_python_value(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _python_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_python_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _key_value(value: Any) -> Any:
    value = _python_value(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _key_tuple(key: Any) -> tuple[Any, ...]:
    if not isinstance(key, tuple):
        key = (key,)
    return tuple(_key_value(value) for value in key)


def _add_group_counts(
    target: Counter[tuple[Any, ...]], frame: pd.DataFrame, columns: list[str]
) -> None:
    grouped = frame.groupby(columns, dropna=False, observed=True, sort=False).size()
    for key, count in grouped.items():
        target[_key_tuple(key)] += int(count)


def _add_group_values(
    target: defaultdict[tuple[Any, ...], list[np.ndarray]],
    frame: pd.DataFrame,
    columns: list[str],
    value_column: str,
) -> None:
    for key, group in frame.groupby(
        columns, dropna=False, observed=True, sort=False
    ):
        values = pd.to_numeric(group[value_column], errors="coerce").dropna()
        if not values.empty:
            target[_key_tuple(key)].append(values.to_numpy(dtype=np.float64))


def _describe(values: list[np.ndarray]) -> dict[str, Any]:
    combined = np.concatenate(values) if values else np.array([], dtype=np.float64)
    if combined.size == 0:
        return {"count": 0}
    q25, median, q75 = np.quantile(combined, [0.25, 0.5, 0.75])
    return {
        "count": int(combined.size),
        "min": float(np.min(combined)),
        "p25": float(q25),
        "median": float(median),
        "p75": float(q75),
        "max": float(np.max(combined)),
        "mean": float(np.mean(combined)),
    }


def _rows_from_counts(
    counts: Counter[tuple[Any, ...]], field_names: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for key, count in sorted(counts.items(), key=lambda item: tuple(
        "" if value is None else str(value) for value in item[0]
    )):
        rows.append({**dict(zip(field_names, key)), "count": int(count)})
    return rows


def _rows_from_values(
    values: defaultdict[tuple[Any, ...], list[np.ndarray]],
    field_names: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for key, arrays in sorted(values.items(), key=lambda item: tuple(
        "" if value is None else str(value) for value in item[0]
    )):
        rows.append({**dict(zip(field_names, key)), **_describe(arrays)})
    return rows


def _count_by_key(
    counts: Counter[tuple[Any, ...]], first_value: Any
) -> int:
    return sum(count for key, count in counts.items() if key[0] == first_value)


def _build_summary(files: list[Path]) -> dict[str, Any]:
    routing_counts: Counter[tuple[Any, ...]] = Counter()
    routing_participant_counts: Counter[tuple[Any, ...]] = Counter()
    duration_values: defaultdict[tuple[Any, ...], list[np.ndarray]] = defaultdict(list)
    duration_row_counts: Counter[tuple[Any, ...]] = Counter()
    temporal_values: defaultdict[tuple[Any, ...], list[np.ndarray]] = defaultdict(list)
    corridor_values: defaultdict[tuple[Any, ...], list[np.ndarray]] = defaultdict(list)
    anomaly_values: defaultdict[tuple[Any, ...], list[np.ndarray]] = defaultdict(list)
    anomaly_counts: Counter[tuple[Any, ...]] = Counter()
    anomaly_party_counts: Counter[tuple[Any, ...]] = Counter()
    alignment_counts: Counter[tuple[Any, ...]] = Counter()
    token_counts: dict[tuple[Any, ...], list[int]] = defaultdict(lambda: [0, 0])
    total_rows = 0

    for file_path in files:
        available_columns = set(pd.read_csv(file_path, nrows=0).columns)
        missing_columns = sorted(set(REQUIRED_COLUMNS) - available_columns)
        if missing_columns:
            raise ValueError(
                f"{file_path.name} is missing required columns: "
                f"{', '.join(missing_columns)}"
            )

        reader = pd.read_csv(
            file_path,
            usecols=REQUIRED_COLUMNS,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        )
        for chunk in reader:
            total_rows += len(chunk)
            for column in (
                "TRANSACTION_TYPE_CODE",
                "CONTINUITY_QFLAG",
                "CURRENCY_CODE",
                "ORDERING_TYPE",
                "BENEFICIARY_TYPE",
                "ANOMALY_TYPE",
            ):
                chunk[column] = chunk[column].astype("string").str.strip()
            chunk["ANOMALY_TYPE"] = chunk["ANOMALY_TYPE"].fillna("NORMAL")
            chunk["ANOMALY_TYPE"] = chunk["ANOMALY_TYPE"].replace("", "NORMAL")

            for column in (
                "PARTICIPANT_COUNT",
                "CURRENCY_CONVERSION_COUNT",
                "TOTAL_DURATION",
                "USD_AMOUNT",
                "EPOCH_SECONDS",
            ):
                chunk[column] = pd.to_numeric(chunk[column], errors="coerce")

            _add_group_counts(
                routing_counts,
                chunk,
                [
                    "TRANSACTION_TYPE_CODE",
                    "PARTICIPANT_COUNT",
                    "CONTINUITY_QFLAG",
                ],
            )
            _add_group_counts(
                routing_participant_counts,
                chunk,
                ["TRANSACTION_TYPE_CODE", "PARTICIPANT_COUNT"],
            )
            _add_group_counts(
                duration_row_counts,
                chunk,
                ["TRANSACTION_TYPE_CODE", "CURRENCY_CONVERSION_COUNT"],
            )
            _add_group_values(
                duration_values,
                chunk,
                ["TRANSACTION_TYPE_CODE", "CURRENCY_CONVERSION_COUNT"],
                "TOTAL_DURATION",
            )

            timestamps = pd.to_datetime(
                chunk["EPOCH_SECONDS"], unit="s", utc=True, errors="coerce"
            )
            chunk["UTC_HOUR_OF_DAY"] = timestamps.dt.hour
            chunk["UTC_DAY_OF_WEEK"] = timestamps.dt.day_of_week
            top_currency_rows = chunk[chunk["CURRENCY_CODE"].isin(TOP_CURRENCIES)]
            _add_group_values(
                temporal_values,
                top_currency_rows,
                [
                    "UTC_HOUR_OF_DAY",
                    "UTC_DAY_OF_WEEK",
                    "ORDERING_TYPE",
                    "CURRENCY_CODE",
                ],
                "USD_AMOUNT",
            )

            for role, bic_column in (
                ("ordering", "ORDERING_BIC8"),
                ("beneficiary", "BENEFICIARY_BIC8"),
            ):
                country = (
                    chunk[bic_column]
                    .astype("string")
                    .str.slice(4, 6)
                    .str.upper()
                )
                expected_currency = country.map(COUNTRY_CURRENCY)
                actual_currency = chunk["CURRENCY_CODE"]
                status = pd.Series(
                    "unmapped_country", index=chunk.index, dtype="string"
                )
                mapped = expected_currency.notna()
                comparable = mapped & actual_currency.notna()
                status.loc[mapped & actual_currency.isna()] = "missing_currency"
                status.loc[
                    comparable & expected_currency.eq(actual_currency)
                ] = "match"
                status.loc[
                    comparable & expected_currency.ne(actual_currency)
                ] = "mismatch"
                alignment = pd.DataFrame(
                    {
                        "ROLE": role,
                        "COUNTRY_CODE": country,
                        "EXPECTED_CURRENCY": expected_currency,
                        "CURRENCY_CODE": actual_currency,
                        "STATUS": status,
                    }
                )
                _add_group_counts(
                    alignment_counts,
                    alignment,
                    [
                        "ROLE",
                        "COUNTRY_CODE",
                        "EXPECTED_CURRENCY",
                        "CURRENCY_CODE",
                        "STATUS",
                    ],
                )

            _add_group_values(
                corridor_values,
                chunk,
                ["ORDERING_TYPE", "BENEFICIARY_TYPE"],
                "USD_AMOUNT",
            )
            _add_group_counts(anomaly_counts, chunk, ["ANOMALY_TYPE"])
            _add_group_counts(
                anomaly_party_counts,
                chunk,
                ["ANOMALY_TYPE", "ORDERING_TYPE", "BENEFICIARY_TYPE"],
            )
            _add_group_values(
                anomaly_values, chunk, ["ANOMALY_TYPE"], "USD_AMOUNT"
            )

            for role, token_column, party_type_column in (
                ("ordering", "ORDERING_TOKENS", "ORDERING_TYPE"),
                ("beneficiary", "BENEFICIARY_TOKENS", "BENEFICIARY_TYPE"),
            ):
                token_text = chunk[token_column].astype("string").fillna("")
                party_types = chunk[party_type_column]
                for token_name, pattern in TOKEN_PATTERN.items():
                    occurrences = token_text.str.count(pattern)
                    token_frame = pd.DataFrame(
                        {
                            "PARTY_TYPE": party_types,
                            "OCCURRENCES": occurrences,
                        }
                    )
                    grouped = token_frame.groupby(
                        "PARTY_TYPE", dropna=False, observed=True
                    )["OCCURRENCES"].agg(
                        frequency="sum",
                        transactions_with_token=lambda values: int(
                            (values > 0).sum()
                        ),
                    )
                    for party_type, row in grouped.iterrows():
                        key = (role, _key_value(party_type), token_name)
                        token_counts[key][0] += int(row["frequency"])
                        token_counts[key][1] += int(
                            row["transactions_with_token"]
                        )

    routing_rows = _rows_from_counts(
        routing_counts,
        [
            "transaction_type_code",
            "participant_count",
            "continuity_qflag",
        ],
    )
    routing_checks: dict[str, Any] = {}
    direct_rows = _count_by_key(routing_participant_counts, "Direct")
    direct_violations = [
        {"participant_count": key[1], "count": int(count)}
        for key, count in routing_participant_counts.items()
        if key[0] == "Direct" and key[1] != 2
    ]
    routing_checks["direct_has_exactly_two_participants"] = {
        "passed": direct_rows > 0 and not direct_violations,
        "rows": direct_rows,
        "violation_rows": sum(row["count"] for row in direct_violations),
        "violations_by_participant_count": direct_violations,
    }
    indirect_covered_checks = {}
    for transaction_type in ("Indirect", "Covered"):
        rows = _count_by_key(routing_participant_counts, transaction_type)
        violations = [
            {"participant_count": key[1], "count": int(count)}
            for key, count in routing_participant_counts.items()
            if key[0] == transaction_type
            and (key[1] is None or key[1] < 3)
        ]
        indirect_covered_checks[transaction_type] = {
            "passed": rows > 0 and not violations,
            "rows": rows,
            "violation_rows": sum(row["count"] for row in violations),
            "violations_by_participant_count": violations,
        }
    routing_checks["indirect_and_covered_have_at_least_three_participants"] = (
        indirect_covered_checks
    )

    duration_rows = _rows_from_values(
        duration_values,
        ["transaction_type_code", "currency_conversion_count"],
    )
    for row in duration_rows:
        key = (row["transaction_type_code"], row["currency_conversion_count"])
        row["row_count"] = duration_row_counts[key]
    fx_latency_comparison = []
    observed_transaction_types = sorted(
        {
            key[0]
            for key in duration_values
            if key[0] is not None
        }
    )
    for transaction_type in observed_transaction_types:
        low_values = [
            array
            for (tx_type, fx_count), arrays in duration_values.items()
            if tx_type == transaction_type
            and fx_count is not None
            and fx_count < 3
            for array in arrays
        ]
        high_values = [
            array
            for (tx_type, fx_count), arrays in duration_values.items()
            if tx_type == transaction_type
            and fx_count is not None
            and fx_count >= 3
            for array in arrays
        ]
        low_median = (
            float(np.median(np.concatenate(low_values))) if low_values else None
        )
        high_median = (
            float(np.median(np.concatenate(high_values))) if high_values else None
        )
        ratio = (
            high_median / low_median
            if high_median is not None and low_median not in (None, 0)
            else None
        )
        fx_latency_comparison.append(
            {
                "transaction_type_code": transaction_type,
                "median_fx_lt_3": low_median,
                "median_fx_gte_3": high_median,
                "gte_3_to_lt_3_median_ratio": ratio,
            }
        )

    direct_fx_counts = [
        (key[1], count)
        for key, count in duration_row_counts.items()
        if key[0] == "Direct"
    ]
    known_direct_fx = [value for value, _ in direct_fx_counts if value is not None]
    direct_fx_violations = [
        {"currency_conversion_count": value, "count": int(count)}
        for value, count in direct_fx_counts
        if value is None or value > 1
    ]
    direct_fx_rows = sum(count for _, count in direct_fx_counts)

    alignment_rows = _rows_from_counts(
        alignment_counts,
        [
            "role",
            "country_code",
            "expected_currency",
            "currency_code",
            "status",
        ],
    )
    alignment_summary = {}
    for role in ("ordering", "beneficiary"):
        statuses: Counter[str] = Counter()
        for key, count in alignment_counts.items():
            if key[0] == role:
                statuses[str(key[4])] += count
        comparable_rows = statuses["match"] + statuses["mismatch"]
        alignment_summary[role] = {
            "match_rows": statuses["match"],
            "mismatch_rows": statuses["mismatch"],
            "unmapped_country_rows": statuses["unmapped_country"],
            "missing_currency_rows": statuses["missing_currency"],
            "comparable_rows": comparable_rows,
            "match_rate": (
                statuses["match"] / comparable_rows if comparable_rows else None
            ),
        }

    corridor_rows = _rows_from_values(
        corridor_values, ["ordering_type", "beneficiary_type"]
    )
    anomaly_labels = set(ANOMALY_CLASSES)
    anomaly_labels.update(
        key[0] for key in anomaly_counts if key[0] is not None
    )
    anomaly_count_lookup = {
        key[0]: count for key, count in anomaly_counts.items()
    }
    anomaly_party_breakdown: dict[str, dict[str, dict[str, int]]] = {}
    for (anomaly, ordering_type, beneficiary_type), count in anomaly_party_counts.items():
        anomaly_name = anomaly if anomaly is not None else "UNKNOWN"
        ordering_name = ordering_type if ordering_type is not None else "UNKNOWN"
        beneficiary_name = (
            beneficiary_type if beneficiary_type is not None else "UNKNOWN"
        )
        anomaly_party_breakdown.setdefault(anomaly_name, {}).setdefault(
            ordering_name, {}
        )[beneficiary_name] = int(count)

    anomaly_summaries = {}
    for anomaly in sorted(anomaly_labels):
        values = anomaly_values.get((anomaly,), [])
        amount_summary = _describe(values)
        count = int(anomaly_count_lookup.get(anomaly, 0))
        amount_summary.pop("mean", None)
        anomaly_summaries[anomaly] = {
            "count": count,
            "ordering_type_to_beneficiary_type": anomaly_party_breakdown.get(
                anomaly, {}
            ),
            "usd_amount_quantiles": amount_summary,
        }

    anomaly_checks = {}
    for anomaly, expected_type in (
        ("ROMANCE_SCAM", "C"),
        ("CEO_SCAM", "B"),
    ):
        breakdown = anomaly_party_breakdown.get(anomaly, {})
        observed_ordering_types = sorted(breakdown)
        total = int(anomaly_count_lookup.get(anomaly, 0))
        violations = sum(
            count
            for ordering_type, beneficiary_breakdown in breakdown.items()
            if ordering_type != expected_type
            for count in beneficiary_breakdown.values()
        )
        anomaly_checks[anomaly] = {
            "field_checked": "ORDERING_TYPE",
            "expected_ordering_type": expected_type,
            "observed_ordering_types": observed_ordering_types,
            "rows": total,
            "violation_rows": int(violations),
            "passed": total > 0 and violations == 0,
        }

    fat_finger_values = anomaly_values.get(("FAT_FINGER_MISTAKE",), [])
    fat_finger_stats = _describe(fat_finger_values)
    if fat_finger_stats["count"]:
        q25, q75 = np.quantile(
            np.concatenate(fat_finger_values), [0.25, 0.75]
        )
        upper_fence = float(q75 + 1.5 * (q75 - q25))
        amounts = np.concatenate(fat_finger_values)
        high_outlier_count = int(np.count_nonzero(amounts > upper_fence))
        fat_finger_outliers = {
            "iqr_upper_fence": upper_fence,
            "high_outlier_count": high_outlier_count,
            "high_outlier_rate": float(high_outlier_count / amounts.size),
        }
    else:
        fat_finger_outliers = {
            "iqr_upper_fence": None,
            "high_outlier_count": 0,
            "high_outlier_rate": None,
        }

    token_summary: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    for (role, party_type, token_name), values in token_counts.items():
        role_summary = token_summary.setdefault(role, {})
        type_summary = role_summary.setdefault(
            party_type if party_type is not None else "UNKNOWN", {}
        )
        type_summary[token_name] = {
            "frequency": int(values[0]),
            "transactions_with_token": int(values[1]),
        }

    return {
        "metadata": {
            "source_files": [file.name for file in files],
            "source_file_count": len(files),
            "total_rows": total_rows,
            "blank_anomaly_type_treated_as": "NORMAL",
            "currency_country_mapping_coverage": (
                "Match rates exclude unmapped BIC country codes and missing currencies."
            ),
        },
        "feature_group_1_routing_topology": {
            "cross_tabulation": routing_rows,
            "rule_checks": routing_checks,
        },
        "feature_group_2_fx_settlement_latency": {
            "by_transaction_type_and_currency_conversion_count": duration_rows,
            "direct_max_fx_steps": max(known_direct_fx) if known_direct_fx else None,
            "direct_fx_rule": {
                "passed": direct_fx_rows > 0 and not direct_fx_violations,
                "rows": direct_fx_rows,
                "violations": direct_fx_violations,
            },
            "median_latency_comparison_fx_gte_3_vs_lt_3": fx_latency_comparison,
        },
        "feature_group_3_temporal_circadian_patterns": {
            "timezone": "UTC",
            "day_of_week_numbering": "0=Monday through 6=Sunday",
            "top_currencies": sorted(TOP_CURRENCIES),
            "by_hour_day_ordering_type_and_currency": _rows_from_values(
                temporal_values,
                [
                    "utc_hour_of_day",
                    "utc_day_of_week",
                    "ordering_type",
                    "currency_code",
                ],
            ),
        },
        "feature_group_4_currency_corridor_alignment": {
            "bic_country_code_slice": "characters [4:6]",
            "country_currency_matches_by_role": alignment_summary,
            "country_currency_breakdown": alignment_rows,
            "usd_amount_by_ordering_to_beneficiary_type": corridor_rows,
        },
        "feature_group_5_anomaly_fraud_signatures": {
            "by_anomaly_type": anomaly_summaries,
            "ordering_type_constraint_checks": anomaly_checks,
            "fat_finger_high_amount_outliers": fat_finger_outliers,
        },
        "feature_group_6_tokenized_party_details": {
            "frequency_and_transaction_counts_by_role_type_and_token": token_summary,
        },
    }


def main() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    data_dir = project_dir / "data"
    output_path = project_dir / "output" / "dashboard_summary.json"
    files = sorted(data_dir.glob("part_*.csv"))
    if not files:
        raise FileNotFoundError(f"No part_*.csv files found in {data_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = _build_summary(files)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            _python_value(summary),
            output_file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        output_file.write("\n")
    print(f"Saved dashboard summary to {output_path}")
    print(f"Aggregated {summary['metadata']['total_rows']:,} rows")


if __name__ == "__main__":
    main()
