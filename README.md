# MAPB – Projekt: Cotton Candy

Repozytorium do projektu z przedmiotu **Modelowanie i analiza procesów biznesowych (MAPB)**.

## Dataset (cotton-candy)

W folderze `cotton-candy/` znajduje się log zdarzeń procesu produkcji waty cukrowej (CPEE / Cottonbot) zapisany w formacie **XES jako YAML**.

W skrócie:

- Struktura: `batch-0/ … batch-23/`
- Typy plików:
	- `*.xes.yaml` – logi zdarzeń (typowo 1 plik ≈ 1 przypadek / 1 uruchomienie)
	- `*-process.yaml` – logi procesowe z bogatszymi danymi strumieniowymi
	- `index.txt` – mapa hierarchii instancji procesu w danym batchu

### Jakie dane są w logach?

- Kluczowe pola logu: **case id** (`concept:instance` i/lub `cpee:instance`), **activity** (`concept:name`), **timestamp** (`time:timestamp`), oraz informacje o źródle (np. `concept:endpoint`, `stream:source`).
- Timestampy:
	- `time:timestamp` ma format ISO 8601 ze strefą (np. `2025-07-28T01:44:36.857242+02:00`).
	- Pomiarowe timestampy w streamie (`stream:point.stream:timestamp`) często są w formacie `YYYY-MM-DD HH:MM:SS.xx`.
- Czujniki / pomiary (w `stream:datastream`):
	- środowisko: `humidity`, `temperature`
	- infrared: `ambient`, `head`
	- plug: `current`, `power`
	- dodatkowo (rzadziej): `weight`, `pressures`, `pos1/pos2/pos3`.
- Parametry procesu (w `data` jako lista `{name, value}`): m.in. `wait_time`, `cook_time`, `cooldown_time`, `quality_score`, `sugar_amount`, `sizes`, `max_pressures`.

Pełniejszy opis znajduje się w pliku `opis_datasetu_cotton_candy.md`.

### Czy dataset jest w repo?

Nie. Dataset jest duży (u mnie ~347 MB) i jest ignorowany przez git w pliku `.gitignore`.
W repo trzymamy kod, notebooki i raporty, a dane pozostają lokalnie.

## Środowisko (Python + uv)

W projekcie używam `uv` do tworzenia środowiska i instalacji zależności.

1. Utworzenie środowiska:
	 - `uv venv .venv`
2. Aktywacja (Windows PowerShell):
	 - `.venv\Scripts\activate`
3. Instalacja pakietów:
	 - `uv pip install -r requirements.txt`

## Uruchomienie notebooków

Notebooki w projekcie:

- `milestone1_cotton_candy.ipynb`
- `milestone2_cotton_candy.ipynb`

W VS Code wybierz kernel Pythona ze środowiska `.venv` i uruchom komórki.

## Milestone 1 (zrozumienie danych)

Notebook `milestone1_cotton_candy.ipynb` koncentruje się na rozpoznaniu struktury logu i jakości danych:

- wczytanie i spłaszczenie event logu XES/YAML,
- identyfikacja kluczowych atrybutów (`case_id`, `activity`, `timestamp`, `resource`),
- analiza braków danych i duplikatów,
- podstawowe statystyki procesu (liczba eventów/cases/aktywności),
- EDA: rozkłady, częstości aktywności, timeline,
- interpretacja wyników jakości danych i charakterystyki procesu.

### Wynik Milestone 1

Efektem jest uporządkowany i zrozumiały obraz danych procesowych, który stanowi bazę pod analizy zaawansowane z Milestone 2 (klasteryzacja, redukcja wymiarowości, wykrywanie anomalii).

## Milestone 2 (analiza zaawansowana)

Notebook `milestone2_cotton_candy.ipynb` rozszerza analizę o:

- inżynierię cech na poziomie przypadków,
- wykrywanie outlierów (IQR, Isolation Forest),
- redukcję wymiarowości (PCA, t-SNE, UMAP),
- klasteryzację (K-Means, DBSCAN),
- analizę relacji między zdarzeniami (Directly-Follows),
- analizę wzorców czasowych i wariantów procesu,
- wykrywanie anomalii (LOF + konsensus metod).

### Dodatkowe pakiety dla Milestone 2

Poza pakietami z `requirements.txt` notebook Milestone 2 wymaga:

- `scikit-learn`
- `umap-learn`

Instalacja (przykład):

- `uv pip install scikit-learn umap-learn`

Jeśli używasz Condy, możesz zainstalować te biblioteki ręcznie w aktywnym środowisku.
