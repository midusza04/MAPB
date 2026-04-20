# Milestone 2 – rozszerzona analiza procesu (cotton-candy)

Raport przygotowany na podstawie wyników z notebooka `milestone2_cotton_candy.ipynb`.

## 1. Zakres i dane wejściowe

- Źródło: logi `batch-*/*.xes.yaml`
- Liczba batchy: **24**
- Liczba plików: **1,294**
- Wczytane dane surowe: **564,185 zdarzeń**, **1,244 przypadki**

## 2. Czyszczenie i normalizacja

- Sparsowane timestampy: **483,714 / 483,714 (100.0%)**
- Usunięte duplikaty: **99,812**
- Po czyszczeniu: **464,373 zdarzeń**, **1,244 przypadki**
- Brak timestampu: **871 zdarzeń (0.2%)**
- Po usunięciu zdarzeń bez timestampu: **463,502 zdarzeń**, **1,244 przypadki**

Wniosek: jakość danych po czyszczeniu jest wystarczająca do analizy sekwencji, czasu i anomalii.

## 3. Macierz cech i outliery

- Macierz cech: **1,244 cases × 26 kolumn**
- Macierz po skalowaniu: **(1244, 20)**

Wykrywanie outlierów:
- IQR: **304 / 1244 (24.4%)**
- Isolation Forest (contamination=5%): **63 / 1244**
- Część wspólna IQR ∩ IF: **62**

Wniosek: IQR jest znacznie bardziej czuły (szeroki zakres odchyleń), a IF identyfikuje bardziej selektywną grupę przypadków odstających.

## 4. Redukcja wymiarowości i klasteryzacja

- PCA: liczba komponentów do 90% wariancji = **8**
- K-Means (wg silhouette): **k = 13**, **score = 0.744**
- DBSCAN: **8 klastrów**, **21 punktów szumu**

Wniosek: dane mają dobrze separowalne grupy (wysoki silhouette), a DBSCAN dodatkowo ujawnia niewielki zbiór punktów potencjalnie anomalitycznych.

## 5. Warianty procesu

- Liczba unikalnych wariantów: **261**
- Top 1 wariant: **165 cases (13.3%)**
- Top 15 wariantów obejmuje: **938 / 1244 cases (75.4%)**
- Warianty występujące 1 raz: **230 (88.1%)**
- Warianty występujące ≤5 razy: **242 (92.7%)**
- Wariantów do pokrycia 80% przypadków: **22**
- Wariantów do pokrycia 95% przypadków: **199**

Wniosek: proces ma silny efekt Pareto (niewiele wariantów pokrywa większość przypadków), ale jednocześnie występuje bardzo długi ogon rzadkich przebiegów.

## 6. Anomalie (IQR + IF + LOF)

- LOF: **63 / 1244**
- Anomalie konsensusowe (>=2 metody): **78 (6.3%)**
- Rzadkie warianty (częstość <=3): **251 (20.2%)**
- Rzadkie warianty ∩ anomalie konsensusowe: **76**

Macierz nakładania:
- IQR vs IF: **62**
- IQR vs LOF: **21**
- IF vs LOF: **7**

Wnioski:
- Konsensus 3 metod daje mniejszy, bardziej wiarygodny zbiór anomalii niż pojedyncze metody.
- **76/78 (97.4%)** anomalii konsensusowych to jednocześnie przypadki z rzadkimi wariantami, co potwierdza silny związek między nietypową strukturą ścieżki a odchyleniami numerycznymi.

## 7. Podsumowanie biznesowe

- Pipeline danych jest stabilny: po czyszczeniu zachowano **463k+** zdarzeń i pełen zbiór **1,244** case’ów.
- Proces wykazuje jednocześnie:
  - wyraźne klastry zachowań (K-Means/DBSCAN),
  - wysoki poziom zmienności ścieżek (261 wariantów, długi ogon),
  - spójnie wykrywalne anomalie (~6.3% przypadków).
- Najbardziej praktyczna definicja anomalii na tym etapie: **konsensus >=2 metody + sygnał rzadkiego wariantu**.
