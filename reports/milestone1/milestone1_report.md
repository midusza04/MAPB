# Milestone 1 – pełna analiza procesu (cotton-candy)

Analiza wykonana na **całym zapisanym procesie** (`batch-*/*.xes.yaml`).

## 1. Opis zbioru danych i kontekstu

- System: Cottonbot / CPEE
- Typ zdarzeń: event log XES zapisany jako YAML
- Liczba przypadków: **1,244**
- Liczba zdarzeń: **564,185**

## 2. Kluczowe atrybuty logu zdarzeń

- case id: `concept:instance` i `cpee:instance`
- activity: `concept:name` (fallback: `id:id`, `cpee:activity`)
- timestamp: `time:timestamp`
- resource: brak stabilnego `org:resource`; zastosowano proxy na bazie endpointu
  - braki resource/proxy: **120,877/564,185**

## 3. Analiza jakości danych

### Brakujące wartości
- `case_id`: **0**
- `case_uuid`: **0**
- `activity`: **0**
- `timestamp_raw`: **80,471**
- `timestamp` (po parsowaniu): **80,471**

### Duplikaty
- Duplikaty (po kluczowych polach): **99,743**

### Niespójności timestampów
- Nieudane parsowanie timestampów: **0**
- Ujemne różnice czasu wewnątrz case: **64,840**

### Niespójności typów danych
- `case_id`: str: 564185
- `case_uuid`: str: 564185
- `activity`: str: 564185
- `timestamp_raw`: str: 483714, NoneType: 80471
- format timestampów: other_string: 483714, missing: 80471

## 4. Eksploracyjna analiza danych

- Rozkład zdarzeń na przypadek jest skośny z długim ogonem.
- Częstotliwości aktywności są nierównomierne (dominacja kilku kroków procesu).
- Timeline pokazuje okresy wysokiej i niskiej intensywności zdarzeń.

## 5. Podstawowe statystyki

- liczba eventów: **564,185**
- liczba cases: **1,244**
- liczba activities: **64**

### Zdarzenia na case
- min: **15**
- mediana: **42**
- średnia: **453.52**
- max: **31421**

### Czas trwania case [s]
- min: **3.73**
- mediana: **32.38**
- średnia: **385.36**
- max: **205121.41**

### Top 10 aktywności
- Get the Environment Data: **196,334**
- Get the Plug Data: **195,487**
- external: **65,868**
- Wait 2 seconds: **21,135**
- Sleep 1 Second: **17,986**
- Move down: **10,248**
- weigh_touch: **10,244**
- Run until CC Head is optimally cooled: **7,988**
- Move down until touch: **4,359**
- Measure the size of the Cotton Candy: **2,166**

## 6. Podstawowe wizualizacje

Wygenerowane pliki:
- `figures/timeline_events_per_hour.png`
- `figures/distribution_events_per_case.png`
- `figures/distribution_case_duration_sec.png`
- `figures/frequency_top_activities.png`