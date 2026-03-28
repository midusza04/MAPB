from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

BASE_DIR = Path(r"C:/Users/dusza/Documents/Studia/7semestr/MAPB")
DATA_DIR = BASE_DIR / "cotton-candy"
OUT_DIR = BASE_DIR / "reports" / "milestone1"
FIG_DIR = OUT_DIR / "figures"
REPORT_PATH = OUT_DIR / "milestone1_report.md"

INTEREST_KEYS = {
    "concept:instance",
    "cpee:instance",
    "concept:name",
    "time:timestamp",
    "concept:endpoint",
    "id:id",
    "cpee:activity",
    "lifecycle:transition",
    "cpee:lifecycle:transition",
}

ISO_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def classify_timestamp(value) -> str:
    if value is None or value == "":
        return "missing"
    if isinstance(value, str) and ISO_TZ_RE.match(value):
        return "iso8601_with_tz"
    if isinstance(value, str):
        return "other_string"
    return type(value).__name__


def normalize_resource(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    endpoint = endpoint.replace("https-get://", "https://").replace("https-post://", "https://")
    parsed = urlparse(endpoint)
    return parsed.netloc if parsed.netloc else endpoint


def parse_timestamp(raw):
    if raw is None or raw == "":
        return None
    ts = pd.to_datetime(raw, errors="coerce", utc=True)
    if pd.isna(ts):
        return None
    return ts.to_pydatetime()


def stream_events(file_path: Path):
    current = None
    seq = 0

    with file_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            if line == "---":
                if current is not None:
                    yield current, seq
                current = None
                continue

            if line == "event:":
                current = {}
                seq += 1
                continue

            if current is None:
                continue

            if line.startswith("  ") and not line.startswith("    "):
                stripped = line.strip()
                if ": " in stripped:
                    key, value = stripped.split(": ", 1)
                elif stripped.endswith(":"):
                    key, value = stripped[:-1], ""
                else:
                    continue

                if key in INTEREST_KEYS and key not in current:
                    current[key] = value

    if current is not None:
        yield current, seq


def fmt_counter(counter_like: dict, limit: int = 10) -> str:
    items = sorted(counter_like.items(), key=lambda x: x[1], reverse=True)[:limit]
    return ", ".join([f"{k}: {v}" for k, v in items])


def main():
    xes_files = sorted(DATA_DIR.glob("batch-*/*.xes.yaml"))
    if not xes_files:
        raise FileNotFoundError("Brak plików *.xes.yaml")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"files to process: {len(xes_files)}")

    # Global metrics
    total_events = 0
    activity_counter = Counter()
    timeline_hourly = Counter()

    missing = Counter()
    type_counts = {
        "case_id": Counter(),
        "case_uuid": Counter(),
        "activity": Counter(),
        "timestamp_raw": Counter(),
        "timestamp_class": Counter(),
    }

    duplicate_set = set()
    duplicate_count = 0
    parse_failed = 0
    non_monotonic = 0

    # Per-case metrics
    case_events = defaultdict(int)
    case_min_ts = {}
    case_max_ts = {}
    case_prev_ts = {}

    for i, path in enumerate(xes_files, start=1):
        fallback_case = str(path.relative_to(DATA_DIR)).replace("\\", "/")

        for event, seq in stream_events(path):
            total_events += 1

            case_id = event.get("concept:instance")
            case_uuid = event.get("cpee:instance")
            activity = event.get("concept:name") or event.get("id:id") or event.get("cpee:activity")
            ts_raw = event.get("time:timestamp")
            endpoint = event.get("concept:endpoint")
            resource = normalize_resource(endpoint)

            case_key = case_uuid or case_id or fallback_case

            ts = parse_timestamp(ts_raw)
            ts_class = classify_timestamp(ts_raw)

            # Missing values
            if case_id in (None, ""):
                missing["case_id"] += 1
            if case_uuid in (None, ""):
                missing["case_uuid"] += 1
            if activity in (None, ""):
                missing["activity"] += 1
            if ts_raw in (None, ""):
                missing["timestamp_raw"] += 1
            if ts is None:
                missing["timestamp"] += 1
            if resource in (None, ""):
                missing["resource"] += 1

            # Type consistency
            type_counts["case_id"][type(case_id).__name__] += 1
            type_counts["case_uuid"][type(case_uuid).__name__] += 1
            type_counts["activity"][type(activity).__name__] += 1
            type_counts["timestamp_raw"][type(ts_raw).__name__] += 1
            type_counts["timestamp_class"][ts_class] += 1

            # Duplicates on key fields
            dup_key = (
                case_id,
                case_uuid,
                activity,
                ts_raw,
                event.get("id:id"),
                endpoint,
                event.get("lifecycle:transition"),
                event.get("cpee:lifecycle:transition"),
            )
            if dup_key in duplicate_set:
                duplicate_count += 1
            else:
                duplicate_set.add(dup_key)

            # Timestamp quality
            if ts_raw not in (None, "") and ts is None:
                parse_failed += 1

            if ts is not None:
                prev = case_prev_ts.get(case_key)
                if prev is not None and ts < prev:
                    non_monotonic += 1
                case_prev_ts[case_key] = ts

                if case_key not in case_min_ts or ts < case_min_ts[case_key]:
                    case_min_ts[case_key] = ts
                if case_key not in case_max_ts or ts > case_max_ts[case_key]:
                    case_max_ts[case_key] = ts

                hour_bucket = ts.replace(minute=0, second=0, microsecond=0)
                timeline_hourly[hour_bucket] += 1

            case_events[case_key] += 1
            activity_counter[activity if activity not in (None, "") else "<missing>"] += 1

        if i % 150 == 0:
            print(f"processed files: {i}/{len(xes_files)}")

    # Aggregate stats
    n_cases = len(case_events)
    n_activities = len(activity_counter)

    events_per_case = pd.Series(list(case_events.values()), name="events_per_case")

    durations = []
    for case_key in case_events.keys():
        start = case_min_ts.get(case_key)
        end = case_max_ts.get(case_key)
        if start is not None and end is not None:
            durations.append((end - start).total_seconds())
    durations_series = pd.Series(durations, name="duration_sec") if durations else pd.Series(dtype=float)

    timeline_series = pd.Series(timeline_hourly).sort_index()

    # Save visualizations
    sns.set(style="whitegrid")

    plt.figure(figsize=(12, 4))
    timeline_series.plot(color="#1f77b4")
    plt.title("Timeline: liczba zdarzeń na godzinę")
    plt.xlabel("czas")
    plt.ylabel("liczba zdarzeń")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "timeline_events_per_hour.png", dpi=150)
    plt.close()

    plt.figure(figsize=(8, 4))
    sns.histplot(events_per_case, bins=40, kde=True, color="#2ca02c")
    plt.title("Rozkład liczby zdarzeń na przypadek")
    plt.xlabel("liczba zdarzeń")
    plt.ylabel("liczba przypadków")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "distribution_events_per_case.png", dpi=150)
    plt.close()

    if not durations_series.empty:
        plt.figure(figsize=(8, 4))
        sns.histplot(durations_series, bins=40, kde=True, color="#ff7f0e")
        plt.title("Rozkład czasu trwania przypadków [s]")
        plt.xlabel("czas trwania [s]")
        plt.ylabel("liczba przypadków")
        plt.tight_layout()
        plt.savefig(FIG_DIR / "distribution_case_duration_sec.png", dpi=150)
        plt.close()

    top_activities = pd.Series(activity_counter).sort_values(ascending=False).head(20)
    plt.figure(figsize=(10, 7))
    sns.barplot(x=top_activities.values, y=top_activities.index, orient="h", color="#9467bd")
    plt.title("Najczęstsze aktywności (Top 20)")
    plt.xlabel("liczba zdarzeń")
    plt.ylabel("aktywność")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "frequency_top_activities.png", dpi=150)
    plt.close()

    # Build report
    lines = [
        "# Milestone 1 – pełna analiza procesu (cotton-candy)",
        "",
        "Analiza wykonana na **całym zapisanym procesie** (`batch-*/*.xes.yaml`).",
        "",
        "## 1. Opis zbioru danych i kontekstu",
        "",
        "- System: Cottonbot / CPEE",
        "- Typ zdarzeń: event log XES zapisany jako YAML",
        f"- Liczba przypadków: **{n_cases:,}**",
        f"- Liczba zdarzeń: **{total_events:,}**",
        "",
        "## 2. Kluczowe atrybuty logu zdarzeń",
        "",
        "- case id: `concept:instance` i `cpee:instance`",
        "- activity: `concept:name` (fallback: `id:id`, `cpee:activity`)",
        "- timestamp: `time:timestamp`",
        "- resource: brak stabilnego `org:resource`; zastosowano proxy na bazie endpointu",
        f"  - braki resource/proxy: **{missing['resource']:,}/{total_events:,}**",
        "",
        "## 3. Analiza jakości danych",
        "",
        "### Brakujące wartości",
        f"- `case_id`: **{missing['case_id']:,}**",
        f"- `case_uuid`: **{missing['case_uuid']:,}**",
        f"- `activity`: **{missing['activity']:,}**",
        f"- `timestamp_raw`: **{missing['timestamp_raw']:,}**",
        f"- `timestamp` (po parsowaniu): **{missing['timestamp']:,}**",
        "",
        "### Duplikaty",
        f"- Duplikaty (po kluczowych polach): **{duplicate_count:,}**",
        "",
        "### Niespójności timestampów",
        f"- Nieudane parsowanie timestampów: **{parse_failed:,}**",
        f"- Ujemne różnice czasu wewnątrz case: **{non_monotonic:,}**",
        "",
        "### Niespójności typów danych",
        f"- `case_id`: {fmt_counter(type_counts['case_id'])}",
        f"- `case_uuid`: {fmt_counter(type_counts['case_uuid'])}",
        f"- `activity`: {fmt_counter(type_counts['activity'])}",
        f"- `timestamp_raw`: {fmt_counter(type_counts['timestamp_raw'])}",
        f"- format timestampów: {fmt_counter(type_counts['timestamp_class'])}",
        "",
        "## 4. Eksploracyjna analiza danych",
        "",
        "- Rozkład zdarzeń na przypadek jest skośny z długim ogonem.",
        "- Częstotliwości aktywności są nierównomierne (dominacja kilku kroków procesu).",
        "- Timeline pokazuje okresy wysokiej i niskiej intensywności zdarzeń.",
        "",
        "## 5. Podstawowe statystyki",
        "",
        f"- liczba eventów: **{total_events:,}**",
        f"- liczba cases: **{n_cases:,}**",
        f"- liczba activities: **{n_activities:,}**",
        "",
        "### Zdarzenia na case",
        f"- min: **{int(events_per_case.min())}**",
        f"- mediana: **{int(events_per_case.median())}**",
        f"- średnia: **{events_per_case.mean():.2f}**",
        f"- max: **{int(events_per_case.max())}**",
        "",
    ]

    if not durations_series.empty:
        lines.extend(
            [
                "### Czas trwania case [s]",
                f"- min: **{durations_series.min():.2f}**",
                f"- mediana: **{durations_series.median():.2f}**",
                f"- średnia: **{durations_series.mean():.2f}**",
                f"- max: **{durations_series.max():.2f}**",
                "",
            ]
        )

    lines.append("### Top 10 aktywności")
    for act, cnt in top_activities.head(10).items():
        lines.append(f"- {act}: **{int(cnt):,}**")

    lines.extend(
        [
            "",
            "## 6. Podstawowe wizualizacje",
            "",
            "Wygenerowane pliki:",
            "- `figures/timeline_events_per_hour.png`",
            "- `figures/distribution_events_per_case.png`",
            "- `figures/distribution_case_duration_sec.png`",
            "- `figures/frequency_top_activities.png`",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"events parsed: {total_events}")
    print(f"saved report: {REPORT_PATH}")
    print(f"saved figures: {FIG_DIR}")


if __name__ == "__main__":
    main()
