from __future__ import annotations

from collections import Counter
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
    if not isinstance(value, str):
        return type(value).__name__
    if ISO_TZ_RE.match(value):
        return "iso8601_with_tz"
    return "other"


def normalize_resource(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    endpoint = endpoint.replace("https-get://", "https://").replace("https-post://", "https://")
    parsed = urlparse(endpoint)
    if parsed.netloc:
        return parsed.netloc
    return endpoint


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

            # Top-level event keys only (2 spaces indent, not nested).
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


def build_dataframe(xes_files: list[Path]) -> pd.DataFrame:
    rows = []

    for i, path in enumerate(xes_files, start=1):
        seq_local = 0
        for event, seq in stream_events(path):
            seq_local = seq

            case_id = event.get("concept:instance")
            case_uuid = event.get("cpee:instance")
            activity = event.get("concept:name") or event.get("id:id") or event.get("cpee:activity")
            ts_raw = event.get("time:timestamp")
            ts = pd.to_datetime(ts_raw, errors="coerce", utc=True)
            endpoint = event.get("concept:endpoint")
            resource = normalize_resource(endpoint)

            rows.append(
                {
                    "file": str(path.relative_to(BASE_DIR)).replace("\\", "/"),
                    "batch": path.parent.name,
                    "seq_in_file": seq,
                    "case_id": case_id,
                    "case_uuid": case_uuid,
                    "activity": activity,
                    "timestamp_raw": ts_raw,
                    "timestamp": ts,
                    "timestamp_class": classify_timestamp(ts_raw),
                    "resource": resource,
                    "endpoint": endpoint,
                    "event_id": event.get("id:id"),
                    "lifecycle": event.get("lifecycle:transition"),
                    "cpee_lifecycle": event.get("cpee:lifecycle:transition"),
                    "type_case_id": type(case_id).__name__,
                    "type_case_uuid": type(case_uuid).__name__,
                    "type_activity": type(activity).__name__,
                    "type_timestamp_raw": type(ts_raw).__name__,
                }
            )

        if i % 150 == 0:
            print(f"processed files: {i}/{len(xes_files)}")

    return pd.DataFrame(rows)


def choose_case_key(df: pd.DataFrame) -> pd.Series:
    key = df["case_uuid"].astype("string")
    key = key.fillna(df["case_id"].astype("string"))
    return key


def analyze_quality(df: pd.DataFrame) -> dict:
    missing = df[["case_id", "case_uuid", "activity", "timestamp_raw", "timestamp", "resource"]].isna().sum()

    dup_cols = [
        "case_id",
        "case_uuid",
        "activity",
        "timestamp_raw",
        "event_id",
        "endpoint",
        "lifecycle",
        "cpee_lifecycle",
    ]
    dup_count = int(df.duplicated(subset=dup_cols).sum())

    parse_failed = int(df["timestamp_raw"].notna().sum() - df["timestamp"].notna().sum())

    work = df.copy()
    work["case_key"] = choose_case_key(work)
    work = work.sort_values(["case_key", "seq_in_file"])
    work["delta_sec"] = work.groupby("case_key")["timestamp"].diff().dt.total_seconds()
    non_monotonic = int((work["delta_sec"] < 0).sum())

    type_summary = {
        "case_id": dict(Counter(df["type_case_id"])),
        "case_uuid": dict(Counter(df["type_case_uuid"])),
        "activity": dict(Counter(df["type_activity"])),
        "timestamp_raw": dict(Counter(df["type_timestamp_raw"])),
        "timestamp_class": dict(Counter(df["timestamp_class"])),
    }

    return {
        "missing": missing,
        "duplicates": dup_count,
        "parse_failed": parse_failed,
        "non_monotonic": non_monotonic,
        "type_summary": type_summary,
    }


def analyze_stats(df: pd.DataFrame) -> dict:
    work = df.copy()
    work["case_key"] = choose_case_key(work)

    n_events = len(work)
    n_cases = int(work["case_key"].nunique())
    n_activities = int(work["activity"].dropna().nunique())

    events_per_case = work.groupby("case_key").size().rename("events_per_case")

    durations = (
        work.dropna(subset=["timestamp"])
        .groupby("case_key")["timestamp"]
        .agg(["min", "max"])
    )
    durations["duration_sec"] = (durations["max"] - durations["min"]).dt.total_seconds()

    activity_freq = work["activity"].fillna("<missing>").value_counts()

    return {
        "work": work,
        "n_events": n_events,
        "n_cases": n_cases,
        "n_activities": n_activities,
        "events_per_case": events_per_case,
        "durations": durations,
        "activity_freq": activity_freq,
    }


def save_visualizations(stats: dict):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    sns.set(style="whitegrid")

    work = stats["work"]
    events_per_case = stats["events_per_case"]
    durations = stats["durations"]
    activity_freq = stats["activity_freq"]

    timeline = work.dropna(subset=["timestamp"]).set_index("timestamp").resample("1h").size()
    plt.figure(figsize=(12, 4))
    timeline.plot(color="#1f77b4")
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

    plt.figure(figsize=(8, 4))
    sns.histplot(durations["duration_sec"].dropna(), bins=40, kde=True, color="#ff7f0e")
    plt.title("Rozkład czasu trwania przypadków [s]")
    plt.xlabel("czas trwania [s]")
    plt.ylabel("liczba przypadków")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "distribution_case_duration_sec.png", dpi=150)
    plt.close()

    top20 = activity_freq.head(20)
    plt.figure(figsize=(10, 7))
    sns.barplot(x=top20.values, y=top20.index, orient="h", color="#9467bd")
    plt.title("Najczęstsze aktywności (Top 20)")
    plt.xlabel("liczba zdarzeń")
    plt.ylabel("aktywność")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "frequency_top_activities.png", dpi=150)
    plt.close()


def top_dict(d: dict, n: int = 10) -> str:
    items = sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]
    return ", ".join([f"{k}: {v}" for k, v in items])


def write_report(df: pd.DataFrame, quality: dict, stats: dict, files_count: int):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    missing = quality["missing"]
    resource_missing = int(df["resource"].isna().sum())

    ev_case = stats["events_per_case"]
    dur = stats["durations"]["duration_sec"]
    top_acts = stats["activity_freq"].head(10)

    lines = [
        "# Milestone 1 – pełna analiza procesu (cotton-candy)",
        "",
        "Analiza wykonana na **całym zapisanym procesie** (`batch-*/*.xes.yaml`).",
        "",
        "## 1. Opis zbioru i kontekstu",
        "",
        "- System: Cottonbot / CPEE",
        "- Typ zdarzeń: event log XES zapisany w YAML",
        f"- Liczba przypadków (plików `*.xes.yaml`): **{files_count:,}**",
        f"- Liczba zdarzeń: **{stats['n_events']:,}**",
        "",
        "## 2. Kluczowe atrybuty logu",
        "",
        "- case id: `concept:instance` oraz `cpee:instance`",
        "- activity: `concept:name` (fallback: `id:id`, `cpee:activity`)",
        "- timestamp: `time:timestamp`",
        "- resource: brak jednolitego `org:resource`; użyto proxy na bazie endpointu",
        f"  - braki resource/proxy: **{resource_missing:,}/{len(df):,}**",
        "",
        "## 3. Analiza jakości danych",
        "",
        "### Braki",
        f"- `case_id`: **{int(missing['case_id']):,}**",
        f"- `case_uuid`: **{int(missing['case_uuid']):,}**",
        f"- `activity`: **{int(missing['activity']):,}**",
        f"- `timestamp_raw`: **{int(missing['timestamp_raw']):,}**",
        f"- `timestamp` po parsowaniu: **{int(missing['timestamp']):,}**",
        "",
        "### Duplikaty",
        f"- Duplikaty (po kluczowych polach): **{quality['duplicates']:,}**",
        "",
        "### Niespójności timestampów",
        f"- Nieudane parsowanie timestampów: **{quality['parse_failed']:,}**",
        f"- Ujemne różnice czasu wewnątrz case: **{quality['non_monotonic']:,}**",
        "",
        "### Niespójności typów",
        f"- `case_id`: {top_dict(quality['type_summary']['case_id'])}",
        f"- `case_uuid`: {top_dict(quality['type_summary']['case_uuid'])}",
        f"- `activity`: {top_dict(quality['type_summary']['activity'])}",
        f"- `timestamp_raw`: {top_dict(quality['type_summary']['timestamp_raw'])}",
        f"- klasy timestampów: {top_dict(quality['type_summary']['timestamp_class'])}",
        "",
        "## 4. Eksploracyjna analiza danych",
        "",
        "- Rozkład liczby zdarzeń na przypadek ma długi ogon (kilka bardzo długich przebiegów).",
        "- Częstości aktywności są mocno nierównomierne (dominują wybrane kroki).",
        "- Timeline pokazuje okresy zwiększonej intensywności zdarzeń.",
        "",
        "## 5. Podstawowe statystyki",
        "",
        f"- eventy: **{stats['n_events']:,}**",
        f"- cases: **{stats['n_cases']:,}**",
        f"- activities: **{stats['n_activities']:,}**",
        "",
        "### Zdarzenia na case",
        f"- min: **{int(ev_case.min())}**",
        f"- mediana: **{int(ev_case.median())}**",
        f"- średnia: **{ev_case.mean():.2f}**",
        f"- max: **{int(ev_case.max())}**",
        "",
        "### Czas trwania case [s]",
        f"- min: **{dur.min():.2f}**",
        f"- mediana: **{dur.median():.2f}**",
        f"- średnia: **{dur.mean():.2f}**",
        f"- max: **{dur.max():.2f}**",
        "",
        "### Top 10 aktywności",
    ]

    for act, cnt in top_acts.items():
        lines.append(f"- {act}: **{cnt:,}**")

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


def main():
    xes_files = sorted(DATA_DIR.glob("batch-*/*.xes.yaml"))
    if not xes_files:
        raise FileNotFoundError("Brak plików `*.xes.yaml` w cotton-candy")

    print(f"files to process: {len(xes_files)}")
    df = build_dataframe(xes_files)
    print(f"events parsed: {len(df)}")

    quality = analyze_quality(df)
    stats = analyze_stats(df)

    save_visualizations(stats)
    write_report(df, quality, stats, len(xes_files))

    # Przydatny eksport danych bazowych do dalszej pracy.
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
        "event_id",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df[core_cols].to_csv(OUT_DIR / "events_core.csv", index=False)

    print(f"saved report: {REPORT_PATH}")
    print(f"saved figures: {FIG_DIR}")


if __name__ == "__main__":
    main()
