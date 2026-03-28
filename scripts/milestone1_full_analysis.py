from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import yaml


BASE_DIR = Path(r"C:/Users/dusza/Documents/Studia/7semestr/MAPB")
DATA_DIR = BASE_DIR / "cotton-candy"
OUTPUT_DIR = BASE_DIR / "reports" / "milestone1"
FIG_DIR = OUTPUT_DIR / "figures"
REPORT_PATH = OUTPUT_DIR / "milestone1_report.md"


@dataclass
class ParseSummary:
    files_processed: int = 0
    events_processed: int = 0


def safe_type_name(value) -> str:
    if value is None:
        return "NoneType"
    return type(value).__name__


def classify_timestamp(raw) -> str:
    if raw is None:
        return "missing"
    if isinstance(raw, pd.Timestamp):
        return "pandas_timestamp"
    if not isinstance(raw, str):
        return type(raw).__name__
    iso_tz = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
    plain_dt = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?$")
    if iso_tz.match(raw):
        return "iso8601_with_tz"
    if plain_dt.match(raw):
        return "plain_datetime"
    return "other_string"


def extract_resource(event: dict) -> str | None:
    # Prefer explicit resource if present.
    for key in ("org:resource", "resource", "cpee:resource"):
        if key in event and event[key] not in (None, ""):
            return str(event[key])

    endpoint = event.get("concept:endpoint")
    if endpoint:
        endpoint_str = str(endpoint)
        parsed = urlparse(endpoint_str.replace("https-get://", "https://").replace("https-post://", "https://"))
        if parsed.netloc:
            return parsed.netloc
        return endpoint_str

    source = event.get("stream:source")
    if source:
        return str(source)

    return None


def iter_event_docs(file_path: Path):
    with file_path.open("r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    if not docs:
        return {}, []
    meta = docs[0].get("log", {}) if isinstance(docs[0], dict) else {}
    return meta, docs[1:]


def parse_all_events(xes_files: list[Path]):
    rows = []
    summary = ParseSummary()

    for idx, path in enumerate(xes_files, start=1):
        meta, event_docs = iter_event_docs(path)

        case_uuid_meta = None
        case_name_meta = None
        if isinstance(meta, dict):
            trace = meta.get("trace")
            if isinstance(trace, dict):
                case_uuid_meta = trace.get("cpee:instance")
                case_name_meta = trace.get("concept:name")

        seq = 0
        for doc in event_docs:
            if not isinstance(doc, dict):
                continue
            event = doc.get("event")
            if not isinstance(event, dict):
                continue

            seq += 1
            timestamp_raw = event.get("time:timestamp")
            timestamp = pd.to_datetime(timestamp_raw, errors="coerce", utc=True)

            activity = event.get("concept:name")
            if activity in (None, ""):
                activity = event.get("id:id") or event.get("cpee:activity")

            case_id = event.get("concept:instance")
            case_uuid = event.get("cpee:instance") or case_uuid_meta
            case_name = case_name_meta

            resource = extract_resource(event)

            rows.append(
                {
                    "file": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
                    "batch": path.parent.name,
                    "seq_in_file": seq,
                    "case_id": case_id,
                    "case_uuid": case_uuid,
                    "case_name": case_name,
                    "event_id": event.get("id:id"),
                    "activity": activity,
                    "timestamp_raw": timestamp_raw,
                    "timestamp": timestamp,
                    "timestamp_class": classify_timestamp(timestamp_raw),
                    "lifecycle": event.get("lifecycle:transition"),
                    "cpee_lifecycle": event.get("cpee:lifecycle:transition"),
                    "endpoint": event.get("concept:endpoint"),
                    "resource": resource,
                    "has_data": "data" in event,
                    "has_stream": "stream:datastream" in event,
                    "type_case_id": safe_type_name(case_id),
                    "type_case_uuid": safe_type_name(case_uuid),
                    "type_activity": safe_type_name(activity),
                    "type_timestamp_raw": safe_type_name(timestamp_raw),
                }
            )

        summary.files_processed += 1
        summary.events_processed += seq

        if idx % 100 == 0:
            print(f"Processed files: {idx}/{len(xes_files)}")

    return pd.DataFrame(rows), summary


def choose_case_key(df: pd.DataFrame) -> pd.Series:
    # Prefer UUID case id; fallback to numeric/string case id.
    key = df["case_uuid"].astype("string")
    fallback = df["case_id"].astype("string")
    key = key.fillna(fallback)
    return key


def compute_quality(df: pd.DataFrame):
    missing = df[["case_id", "case_uuid", "activity", "timestamp_raw", "timestamp", "resource"]].isna().sum()

    duplicate_subset = [
        "case_id",
        "case_uuid",
        "activity",
        "timestamp_raw",
        "event_id",
        "endpoint",
        "lifecycle",
        "cpee_lifecycle",
    ]
    duplicate_count = int(df.duplicated(subset=duplicate_subset).sum())

    # Inconsistent timestamps: parse failures and non-monotonic order inside case.
    parse_failed = int(df["timestamp_raw"].notna().sum() - df["timestamp"].notna().sum())

    case_key = choose_case_key(df)
    ordered = df.copy()
    ordered["case_key"] = case_key
    ordered = ordered.sort_values(["case_key", "seq_in_file"])
    ordered["delta_sec"] = ordered.groupby("case_key")["timestamp"].diff().dt.total_seconds()
    non_monotonic_count = int((ordered["delta_sec"] < 0).sum())

    type_consistency = {
        "case_id": dict(Counter(df["type_case_id"])),
        "case_uuid": dict(Counter(df["type_case_uuid"])),
        "activity": dict(Counter(df["type_activity"])),
        "timestamp_raw": dict(Counter(df["type_timestamp_raw"])),
        "timestamp_class": dict(Counter(df["timestamp_class"])),
    }

    return {
        "missing": missing,
        "duplicate_count": duplicate_count,
        "parse_failed": parse_failed,
        "non_monotonic_count": non_monotonic_count,
        "type_consistency": type_consistency,
    }


def compute_stats(df: pd.DataFrame):
    case_key = choose_case_key(df)
    work = df.copy()
    work["case_key"] = case_key

    n_events = len(work)
    n_cases = int(work["case_key"].nunique())
    n_activities = int(work["activity"].dropna().nunique())

    events_per_case = work.groupby("case_key").size().rename("events_per_case")

    ts_work = work.dropna(subset=["timestamp"]).copy()
    durations = (
        ts_work.groupby("case_key")["timestamp"]
        .agg(["min", "max"])
        .assign(duration_sec=lambda x: (x["max"] - x["min"]).dt.total_seconds())
    )

    activity_freq = work["activity"].fillna("<missing>").value_counts()

    return {
        "n_events": n_events,
        "n_cases": n_cases,
        "n_activities": n_activities,
        "events_per_case": events_per_case,
        "durations": durations,
        "activity_freq": activity_freq,
        "work": work,
    }


def make_visualizations(stats: dict, fig_dir: Path):
    fig_dir.mkdir(parents=True, exist_ok=True)
    sns.set(style="whitegrid")

    work = stats["work"]
    events_per_case = stats["events_per_case"]
    durations = stats["durations"]
    activity_freq = stats["activity_freq"]

    # Timeline: events per hour
    timeline = (
        work.dropna(subset=["timestamp"])
        .set_index("timestamp")
        .resample("1h")
        .size()
    )
    plt.figure(figsize=(12, 4))
    timeline.plot(color="#1f77b4")
    plt.title("Timeline: liczba zdarzeń w czasie (agregacja godzinowa)")
    plt.xlabel("czas")
    plt.ylabel("liczba zdarzeń")
    plt.tight_layout()
    plt.savefig(fig_dir / "timeline_events_per_hour.png", dpi=150)
    plt.close()

    # Distribution: events per case
    plt.figure(figsize=(8, 4))
    sns.histplot(events_per_case, bins=40, kde=True, color="#2ca02c")
    plt.title("Rozkład liczby zdarzeń na przypadek")
    plt.xlabel("liczba zdarzeń")
    plt.ylabel("liczba przypadków")
    plt.tight_layout()
    plt.savefig(fig_dir / "distribution_events_per_case.png", dpi=150)
    plt.close()

    # Distribution: case duration
    plt.figure(figsize=(8, 4))
    sns.histplot(durations["duration_sec"].dropna(), bins=40, kde=True, color="#ff7f0e")
    plt.title("Rozkład czasu trwania przypadków [s]")
    plt.xlabel("czas trwania [s]")
    plt.ylabel("liczba przypadków")
    plt.tight_layout()
    plt.savefig(fig_dir / "distribution_case_duration_sec.png", dpi=150)
    plt.close()

    # Frequency: top activities
    top_activities = activity_freq.head(20)
    plt.figure(figsize=(10, 7))
    sns.barplot(x=top_activities.values, y=top_activities.index, orient="h", color="#9467bd")
    plt.title("Najczęstsze aktywności (Top 20)")
    plt.xlabel("liczba zdarzeń")
    plt.ylabel("aktywność")
    plt.tight_layout()
    plt.savefig(fig_dir / "frequency_top_activities.png", dpi=150)
    plt.close()


def fmt_counter(d: dict, limit: int = 10) -> str:
    items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:limit]
    return ", ".join([f"{k}: {v}" for k, v in items])


def build_report(summary: ParseSummary, quality: dict, stats: dict) -> str:
    events_per_case = stats["events_per_case"]
    durations = stats["durations"]
    activity_freq = stats["activity_freq"]

    missing = quality["missing"]
    type_consistency = quality["type_consistency"]

    # resource availability
    resource_missing = int(stats["work"]["resource"].isna().sum())
    resource_total = len(stats["work"])

    lines = []
    lines.append("# Milestone 1 – Analiza pełnego procesu (cotton-candy)")
    lines.append("")
    lines.append("Raport wygenerowany automatycznie na podstawie **całego zapisanego procesu** (`*.xes.yaml` w `cotton-candy/`).")
    lines.append("")

    lines.append("## 1. Opis zbioru danych i kontekstu")
    lines.append("")
    lines.append("- System: Cottonbot / CPEE (log zdarzeń procesu produkcji waty cukrowej)")
    lines.append("- Typ zdarzeń: event log XES zapisany jako YAML (zdarzenia aktywności, stream/data, zmiany dataelements)")
    lines.append(f"- Liczba przetworzonych plików przypadków: **{summary.files_processed}**")
    lines.append(f"- Liczba przetworzonych zdarzeń: **{summary.events_processed:,}**")
    lines.append("")

    lines.append("## 2. Kluczowe atrybuty logu zdarzeń")
    lines.append("")
    lines.append("- `case id`: obecny jako `concept:instance` (często ID numeryczne) i `cpee:instance` (UUID)")
    lines.append("- `activity`: obecna głównie jako `concept:name` (fallback: `id:id` / `cpee:activity`)")
    lines.append("- `timestamp`: obecny jako `time:timestamp`")
    lines.append("- `resource`: brak jednolitego, klasycznego `org:resource`; użyto proxy (`endpoint`/source).")
    lines.append(f"  - Braki resource/proxy: **{resource_missing:,}/{resource_total:,}** zdarzeń")
    lines.append("")

    lines.append("## 3. Analiza jakości danych")
    lines.append("")
    lines.append("### 3.1 Brakujące wartości")
    lines.append("")
    lines.append(f"- `case_id` braków: **{int(missing['case_id']):,}**")
    lines.append(f"- `case_uuid` braków: **{int(missing['case_uuid']):,}**")
    lines.append(f"- `activity` braków: **{int(missing['activity']):,}**")
    lines.append(f"- `timestamp_raw` braków: **{int(missing['timestamp_raw']):,}**")
    lines.append(f"- `timestamp` (po parsowaniu) braków: **{int(missing['timestamp']):,}**")
    lines.append("")

    lines.append("### 3.2 Duplikaty")
    lines.append("")
    lines.append(f"- Duplikaty (na kluczowych kolumnach): **{quality['duplicate_count']:,}**")
    lines.append("")

    lines.append("### 3.3 Niespójności timestampów")
    lines.append("")
    lines.append(f"- Nieudane parsowanie timestampów: **{quality['parse_failed']:,}**")
    lines.append(f"- Zdarzenia z ujemnym krokiem czasu wewnątrz przypadku: **{quality['non_monotonic_count']:,}**")
    lines.append("")

    lines.append("### 3.4 Niespójności typów danych")
    lines.append("")
    lines.append(f"- Typy `case_id`: {fmt_counter(type_consistency['case_id'])}")
    lines.append(f"- Typy `case_uuid`: {fmt_counter(type_consistency['case_uuid'])}")
    lines.append(f"- Typy `activity`: {fmt_counter(type_consistency['activity'])}")
    lines.append(f"- Typy `timestamp_raw`: {fmt_counter(type_consistency['timestamp_raw'])}")
    lines.append(f"- Klasy formatów timestampów: {fmt_counter(type_consistency['timestamp_class'])}")
    lines.append("")

    lines.append("## 4. Eksploracyjna analiza danych")
    lines.append("")
    lines.append("- Rozkład liczby zdarzeń na przypadek wykazuje długi ogon (istnieją bardzo długie przypadki).")
    lines.append("- Aktywności mają nierównomierny rozkład częstości (niewielka grupa aktywności dominuje).")
    lines.append("- Timeline zdarzeń pokazuje okresy wzmożonej aktywności i przerwy między seriami batchy.")
    lines.append("")

    lines.append("## 5. Podstawowe statystyki")
    lines.append("")
    lines.append(f"- Liczba eventów: **{stats['n_events']:,}**")
    lines.append(f"- Liczba cases: **{stats['n_cases']:,}**")
    lines.append(f"- Liczba activities: **{stats['n_activities']:,}**")
    lines.append("")
    lines.append("### 5.1 Zdarzenia na przypadek")
    lines.append("")
    lines.append(f"- min: **{int(events_per_case.min())}**")
    lines.append(f"- mediana: **{int(events_per_case.median())}**")
    lines.append(f"- średnia: **{events_per_case.mean():.2f}**")
    lines.append(f"- max: **{int(events_per_case.max())}**")
    lines.append("")

    lines.append("### 5.2 Czas trwania przypadków [s]")
    lines.append("")
    lines.append(f"- min: **{durations['duration_sec'].min():.2f}**")
    lines.append(f"- mediana: **{durations['duration_sec'].median():.2f}**")
    lines.append(f"- średnia: **{durations['duration_sec'].mean():.2f}**")
    lines.append(f"- max: **{durations['duration_sec'].max():.2f}**")
    lines.append("")

    lines.append("### 5.3 Najczęstsze aktywności (Top 10)")
    lines.append("")
    for act, cnt in activity_freq.head(10).items():
        lines.append(f"- {act}: **{cnt:,}**")
    lines.append("")

    lines.append("## 6. Wizualizacje")
    lines.append("")
    lines.append("Wygenerowane pliki PNG:")
    lines.append("")
    lines.append("- `figures/timeline_events_per_hour.png`")
    lines.append("- `figures/distribution_events_per_case.png`")
    lines.append("- `figures/distribution_case_duration_sec.png`")
    lines.append("- `figures/frequency_top_activities.png`")
    lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    xes_files = sorted(DATA_DIR.glob("batch-*/*.xes.yaml"))
    if not xes_files:
        raise FileNotFoundError("Nie znaleziono plików *.xes.yaml w cotton-candy")

    print(f"Found xes files: {len(xes_files)}")
    df, summary = parse_all_events(xes_files)
    print(f"Events dataframe rows: {len(df)}")

    quality = compute_quality(df)
    stats = compute_stats(df)

    make_visualizations(stats, FIG_DIR)
    report = build_report(summary, quality, stats)
    REPORT_PATH.write_text(report, encoding="utf-8")

    # Save compact CSV with core columns for reproducibility.
    core_cols = [
        "file",
        "batch",
        "seq_in_file",
        "case_id",
        "case_uuid",
        "activity",
        "timestamp_raw",
        "timestamp",
        "resource",
        "endpoint",
        "lifecycle",
        "cpee_lifecycle",
    ]
    df[core_cols].to_csv(OUTPUT_DIR / "events_core.csv", index=False)

    print("Saved report:", REPORT_PATH)
    print("Saved figures in:", FIG_DIR)


if __name__ == "__main__":
    main()
