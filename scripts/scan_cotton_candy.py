from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re
import statistics as st

import yaml

BASE = Path(r"C:/Users/dusza/Documents/Studia/7semestr/MAPB/cotton-candy")

xes_files = sorted(BASE.glob("batch-*/*.xes.yaml"))
process_files = sorted(BASE.glob("batch-*/*-process.yaml"))
index_files = sorted(BASE.glob("batch-*/index.txt"))

print("batches:", len([p for p in BASE.glob("batch-*") if p.is_dir()]))
print("xes_files:", len(xes_files))
print("process_files:", len(process_files))
print("index_files:", len(index_files))

sample: list[Path] = []
all_log_files = []
all_log_files.extend(xes_files)
all_log_files.extend(process_files)

if all_log_files:
    candidates = []
    # kilka z XES
    if xes_files:
        candidates += [xes_files[0], xes_files[len(xes_files) // 2], xes_files[-1]]
        candidates += xes_files[:2]
    # kilka z process
    if process_files:
        candidates += [process_files[0], process_files[len(process_files) // 2], process_files[-1]]
        candidates += process_files[:2]

    seen: set[str] = set()
    for p in candidates:
        s = str(p)
        if s in seen:
            continue
        seen.add(s)
        sample.append(p)

activity_counter = Counter()
event_key_counter = Counter()
timestamp_examples: dict[str, Counter] = defaultdict(Counter)
stream_ids = Counter()
stream_names = Counter()
endpoints = Counter()
meta_names = Counter()
meta_creator = Counter()
data_names = Counter()
env_keys = Counter()
plug_keys = Counter()

iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
plain_re = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?$")
event_line_re = re.compile(rb"(?m)^event:[ \t]*$")


def classify_ts(value):
    if value is None:
        return "null"
    if not isinstance(value, str):
        return type(value).__name__
    if iso_re.match(value):
        return "iso8601_tz"
    if plain_re.match(value):
        return "plain_datetime"
    return "other"


def iter_events(doc_list):
    for doc in doc_list[1:]:
        if isinstance(doc, dict) and isinstance(doc.get("event"), dict):
            yield doc["event"]


def walk_stream_datastream(stream_datastream):
    if isinstance(stream_datastream, list):
        stack = list(stream_datastream)
    else:
        stack = [stream_datastream]

    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if "stream:name" in item:
                stream_names[str(item["stream:name"])] += 1
            pt = item.get("stream:point")
            if isinstance(pt, dict):
                if "stream:id" in pt:
                    stream_ids[str(pt["stream:id"])] += 1
                if "stream:timestamp" in pt:
                    timestamp_examples["stream:timestamp"][classify_ts(pt["stream:timestamp"])] += 1
            nested = item.get("stream:datastream")
            if isinstance(nested, list):
                stack.extend(nested)
        elif isinstance(item, list):
            stack.extend(item)


for path in sample:
    with path.open("r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    meta = docs[0].get("log", {}) if docs and isinstance(docs[0], dict) else {}
    if isinstance(meta, dict):
        xes = meta.get("xes")
        if isinstance(xes, dict):
            meta_creator[xes.get("creator")] += 1
        trace = meta.get("trace")
        if isinstance(trace, dict):
            meta_names[trace.get("cpee:name")] += 1

    for ev in iter_events(docs):
        for k in ev.keys():
            event_key_counter[k] += 1
        if "concept:name" in ev:
            activity_counter[str(ev["concept:name"])] += 1
        if "concept:endpoint" in ev:
            endpoints[str(ev["concept:endpoint"])] += 1
        if "time:timestamp" in ev:
            timestamp_examples["time:timestamp"][classify_ts(ev["time:timestamp"])] += 1

        sd = ev.get("stream:datastream")
        if sd is not None:
            walk_stream_datastream(sd)

        # data elements (lista {name, value})
        data = ev.get("data")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                if name is not None:
                    data_names[str(name)] += 1
                value = item.get("value")
                # env/plug mają zwykle zagnieżdżone timestampy i klucze czujników
                if name == "env" and isinstance(value, dict):
                    for k in value.keys():
                        env_keys[str(k)] += 1
                    ts = value.get("timestamp")
                    if ts is not None:
                        timestamp_examples["env.timestamp"][classify_ts(ts)] += 1
                if name == "plug" and isinstance(value, dict):
                    for k in value.keys():
                        plug_keys[str(k)] += 1
                    ts = value.get("timestamp")
                    if ts is not None:
                        timestamp_examples["plug.timestamp"][classify_ts(ts)] += 1

print("\n=== sample-based schema hints ===")
print("top event keys:", [k for k, _ in event_key_counter.most_common(15)])
print("time:timestamp patterns:", dict(timestamp_examples["time:timestamp"]))
print("stream:timestamp patterns:", dict(timestamp_examples["stream:timestamp"]))
print("env.timestamp patterns:", dict(timestamp_examples["env.timestamp"]))
print("plug.timestamp patterns:", dict(timestamp_examples["plug.timestamp"]))
print("stream point ids:", stream_ids.most_common(20))
print("stream names:", stream_names.most_common(20))
print("top data element names:", data_names.most_common(20))
print("env keys:", env_keys.most_common(20))
print("plug keys:", plug_keys.most_common(20))
print("top endpoints:", endpoints.most_common(10))
print("meta cpee:name:", meta_names.most_common(5))
print("meta creator:", meta_creator.most_common(5))

cases_per_batch = Counter(p.parent.name for p in xes_files)
vals = sorted(cases_per_batch.values())
print("\n=== cases per batch (min/median/max) ===")
if vals:
    print("min", min(vals), "median", int(st.median(vals)), "max", max(vals), "batches", len(vals))


def count_events_fast(path: Path) -> int:
    data = path.read_bytes()
    return len(event_line_re.findall(data))


def describe_event_counts(paths: list[Path], label: str) -> None:
    if not paths:
        print(f"\n=== event counts: {label} ===")
        print("no files")
        return

    counts = []
    for p in paths:
        try:
            counts.append(count_events_fast(p))
        except Exception:
            # jeśli jakiś plik ma nietypowe kodowanie, pomijamy
            continue

    print(f"\n=== event counts: {label} ===")
    print("files_count:", len(paths))
    print("counted_files:", len(counts))
    if counts:
        print("total_events:", sum(counts))
        print("min_events_per_file:", min(counts))
        print("median_events_per_file:", int(st.median(counts)))
        print("mean_events_per_file:", round(st.mean(counts), 2))
        print("max_events_per_file:", max(counts))


describe_event_counts(xes_files, "*.xes.yaml")
describe_event_counts(process_files, "*-process.yaml")
