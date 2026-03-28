# Opis datasetu: Cotton Candy (log zdarzeń)

Ten dokument opisuje zawartość folderu `cotton-candy/` używanego w projekcie MAPB (analiza procesu na podstawie logów zdarzeń).

## 1) Kontekst i pochodzenie danych

Zbiór danych dotyczy uruchomień procesu produkcji waty cukrowej realizowanego przez system „Cottonbot / Cotton Candy Machine” sterowany workflow engine **CPEE** (w logach pojawia się `xes.creator: cpee.org`).

W logach widoczne są wywołania usług/sensorów zewnętrznych (np. `sugarpi/environment`, `sugarpi/plug`, `sugarpi/weigh_max`) oraz pomiary z czujników (wilgotność/temperatura itp.).

## 2) Struktura folderów i plików

W katalogu `cotton-candy/` znajdują się podkatalogi `batch-0/ … batch-23/`.

W każdym batchu występują typowo:

- `*.xes.yaml` – log zdarzeń w formacie XES zapisanym jako YAML (jeden plik zwykle odpowiada jednemu „przypadkowi” / uruchomieniu procesu).
- `*-process.yaml` – logi „procesowe” (również w formie XES→YAML), często bogatsze o dane strumieniowe (datastream) i parametry procesu.
- `index.txt` – mapa hierarchii instancji procesu (zależności parent/child) i powiązania nazw z identyfikatorami instancji.

### Rozmiar zbioru (na podstawie skanu katalogu)

- Liczba batchy: **24**
- Liczba plików `*.xes.yaml`: **1294**
- Liczba plików `*-process.yaml`: **33**

### Liczba przypadków (cases)

Przyjmując, że każdy plik `*.xes.yaml` to jeden przypadek:

- Liczba przypadków: **1294**
- Liczba przypadków na batch (min/mediana/max): **9 / 59 / 78**

### Liczba zdarzeń (events)

Zliczenie wykonano przez policzenie liczby dokumentów `event:` w plikach YAML.

- `*.xes.yaml`:
  - Łącznie: **564 185** eventów
  - Na plik (min/mediana/średnia/max): **15 / 42 / 436.00 / 31 421**
- `*-process.yaml`:
  - Łącznie (wszystkie pliki): **9 853** eventy
  - Na plik (min/mediana/średnia/max): **69 / 258 / 298.58 / 497**

Uwaga: średnia liczba zdarzeń na przypadek jest „zawyżana” przez nieliczne bardzo długie przebiegi (max 31k eventów).

## 3) Format logu zdarzeń (XES zapisany jako YAML)

Pliki mają strukturę YAML z wieloma dokumentami rozdzielonymi `---`:

- pierwszy dokument: metadane logu (`log:`) z definicjami rozszerzeń XES oraz informacjami o trace,
- kolejne dokumenty: pojedyncze zdarzenia w polu `event:`.

### Typowe klucze w evencie

Najczęściej występują m.in.:

- `concept:instance` – identyfikator przypadku w logu (często liczba, np. `61169`)
- `cpee:instance` – identyfikator instancji CPEE (UUID)
- `concept:name` – nazwa aktywności (np. „Get the Environment Data”)
- `time:timestamp` – timestamp zdarzenia
- `concept:endpoint` – endpoint usługi/sensora wywołanej w ramach aktywności
- `id:id` – identyfikator zdarzenia / aktywności (np. `a14`, `a21`, `external`)
- `lifecycle:transition`, `cpee:lifecycle:transition` – przejścia lifecycle
- `stream:datastream` – zagnieżdżone dane strumieniowe (pomiary)
- `data` – lista elementów `{name, value}` (parametry procesu, agregaty, konfiguracja)

## 4) Kluczowe atrybuty (case id / activity / timestamp / resource)

### Case ID

W praktyce spotykane są dwie identyfikacje przypadku:

- `concept:instance` – numeryczny identyfikator instancji/trace,
- `cpee:instance` – UUID instancji procesu w CPEE.

W `index.txt` w każdym batchu widać dodatkowo hierarchię instancji (np. „Create 11 Cotton Candies” → „Cottonbot - Run with Data Collection” → „move_touch” → …).

### Activity

- `concept:name` – czytelna nazwa aktywności,
- alternatywnie: `id:id` / `cpee:activity` – krótsze identyfikatory (np. `a14`).

### Timestamp

- `time:timestamp` (dla eventów) jest w formacie **ISO 8601 z offsetem strefy**:
  - przykład: `2025-07-28T01:44:36.857242+02:00`

### Resource

W klasycznym sensie „resource” (wykonawca/pracownik) nie zawsze jest jawnie obecny jako osobna kolumna. Najbliższe odpowiedniki to:

- `stream:source` (np. `sensors`, `plug`),
- endpoint (`concept:endpoint`) jako „źródło” zdarzenia,
- identyfikatory aktywności `cpee:activity`.

## 5) Timestampy – formaty i miejsca występowania

W danych występują co najmniej trzy typy timestampów:

1. **Event timestamp**: `time:timestamp`
   - ISO 8601 + strefa czasowa (offset)

2. **Timestampy pomiarów w strumieniu**: `stream:point.stream:timestamp`
   - zwykle format tekstowy: `YYYY-MM-DD HH:MM:SS.xx` (np. `2025-07-28 01:44:38.45`)
   - sporadycznie parser YAML zwraca obiekt typu `datetime` (zależy od konkretnej wartości i loadera)

3. **Timestampy w parametrach `data`**:
   - `env.value.timestamp` oraz `plug.value.timestamp`
   - format tekstowy: `YYYY-MM-DD HH:MM:SS.xx`

Implikacje analityczne:

- trzeba normalizować timestampy do jednego typu (`datetime`) i uważać na strefy czasowe,
- stream i `data` mogą mieć timestampy bez jawnego offsetu (lokalny czas).

## 6) Czujniki i dane pomiarowe

### Strumienie (`stream:datastream`)

W `stream:datastream` pojawiają się zagnieżdżone „pod-strumienie” (`stream:name`), m.in.:

- `environment`
- `internal`
- `infrared`
- `plug`
- oraz nadrzędny `all`

### Identyfikatory pomiarów (`stream:point.stream:id`)

Najczęściej spotykane identyfikatory punktów pomiarowych:

- `humidity` – wilgotność
- `temperature` – temperatura
- `ambient` – IR ambient
- `head` – IR head
- `current` – prąd (plug)
- `power` – moc (plug)

Rzadziej pojawiają się też punkty związane z jakością/ruchem/wyjściem procesu (w zależności od pliku):

- `pos1`, `pos2`, `pos3` – pozycje/pomiary na pozycjach
- `weight` – masa
- `pressures` – ciśnienia

### Agregaty/env/plug w `data`

W zdarzeniach typu `dataelements/change` występują elementy `data` zawierające m.in.:

- `env.value` z kluczami: `EnvH`, `EnvT`, `InH`, `InT`, `IrA`, `IrO`, `timestamp`
  - (środowisko: wilgotność/temperatura zewnętrzna, wewnętrzna oraz IR ambient/head)
- `plug.value` z kluczami: `current`, `power`, `timestamp`

## 7) Parametry procesu i pola jakościowe

W `data` pojawiają się parametry sterujące i wynikowe, np.:

- czasy: `wait_time`, `cook_time`, `cooldown_time`, `handover_time`, `total_time`
- surowce/geometria: `sugar_amount`, `stick_weight`, `radius`, `height`
- jakość/produkt: `quality_score`, `weight`
- utrzymanie ruchu: `batch_since_maintenance`, `iteration_since_maintenance`
- jakościowe pomiary per pozycja: `sizes`, `max_pressures`, `f_pressures`

Wartości mogą być liczbami lub tekstami (np. niektóre temperatury w streamie bywają zapisane jako string).

## 8) Przykładowe endpointy usług

W logach widoczne są m.in. endpointy:

- `https://lab.bpm.in.tum.de/sugarpi/environment/` – pobieranie danych środowiskowych
- `https-get://lab.bpm.in.tum.de/sugarpi/plug/` – pobieranie danych z wtyczki (moc/prąd)
- `https://lab.bpm.in.tum.de/sugarpi/weigh_max/` – ważenie
- endpointy UR5 (robot) – kroki/pozycje procesu jakości (np. `.../quality/posX.urp/wait`)

## 9) Uwagi dot. jakości danych (praktyczne)

- Log jest silnie **zagnieżdżony** (listy/słowniki w polach `data` i `stream:datastream`), więc do analizy zwykle trzeba go spłaszczyć (`json_normalize`) albo osobno zbudować tabelę pomiarów.
- Timestampy są w różnych formatach (ISO 8601 + offset vs „plain datetime”), co wymaga normalizacji.
- Część wartości liczbowych występuje jako string (np. temperatura `'37.90'`), co wymaga konwersji typów.
- Występują zdarzenia „systemowe” (konfiguracja, zmiana dataelements) oraz zdarzenia „pomiarowe” (stream/data) – warto je rozdzielić w EDA.

---

Jeśli chcesz, mogę dopisać w notebooku Milestone 1 automatyczną sekcję, która z plików process.yaml buduje osobny DataFrame z tabelą pomiarów (timestamp, stream_name, sensor_id, value) i robi dedykowane wykresy dla czujników.
