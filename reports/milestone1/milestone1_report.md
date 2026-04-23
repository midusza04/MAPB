# Milestone 1 – raport z naciskiem na dane sensorowe (Cotton Candy)

Raport został zaktualizowany na podstawie wynikow sekcji sensorowej notebooka i plikow CSV w katalogu reports/milestone1.

## 1. Zakres aktualizacji

Zakres obejmuje dane pomiarowe z plikow batch-*/*-process.yaml:
- jakosc danych per sensor,
- czestotliwosc wystapien sensorow,
- statystyki numeryczne wartosci sensorow,
- podsumowanie Milestone 1 pod katem warstwy sensorowej.

## 2. Podsumowanie sensorow

Na podstawie pliku m1_summary.csv:
- liczba punktow sensorowych: 38,207
- liczba typow sensorow: 11

Najczesciej wystepujace sensory (m1_sensor_frequency.csv):
- humidity: 9,434
- temperature: 9,434
- head: 4,717
- ambient: 4,717
- current: 4,700
- power: 4,700

Wniosek: trzon danych tworza sensory srodowiskowe i energetyczne (humidity, temperature, ambient, head, current, power).

## 3. Jakosc danych sensorowych

Na podstawie m1_sensor_quality_per_sensor.csv:
- brakujace znaczniki czasu: 0 dla wszystkich sensorow (0.00%)
- duplikaty: wystepuja tylko dla current i power (po 11 rekordow, 0.23%)
- nienumeryczne wartosci:
  - pressures: 100.00%
  - brakujace sensor_id (pusty identyfikator): 100.00%
  - pos1: 58.52%
  - pos2: 52.44%
  - pos3: 52.44%

Wniosek: jakosc timestampow jest bardzo dobra, a glownym obszarem ryzyka sa wartosci nienumeryczne dla czesci sensorow pozycyjnych i pomocniczych.

## 4. Statystyki wartosci numerycznych sensorow

Na podstawie m1_sensor_numeric_stats.csv:
- temperature: srednia 31.47, mediana 24.82, max 46.81
- humidity: srednia 48.75, mediana 60.13, max 65.56
- ambient: srednia 30.62, mediana 31.11, max 34.39
- head: srednia 67.49, mediana 71.03, max 90.93
- current: srednia 2.75, mediana 4.36, max 4.51
- power: srednia 595.26, mediana 950.00, max 1002.00

Wniosek: sensory head/current/power wykazuja duza zmiennosc, co jest spójne z fazami pracy urzadzenia.

## 5. Wizualizacje i artefakty

W notebooku dodano osobna heatmape jakosci per sensor (metryki %):
- missing_timestamp_pct
- non_numeric_value_pct
- duplicates_pct

Wygenerowane tabele CSV:
- m1_summary.csv
- m1_sensor_quality_per_sensor.csv
- m1_sensor_frequency.csv
- m1_sensor_numeric_stats.csv
- m1_event_missing_table.csv
- m1_checklist.csv

## 6. Wnioski dla Milestone 1

1. Warstwa sensorowa jest dobrze pokryta i dostarcza duzej liczby pomiarow.
2. Najwazniejsze problemy jakosciowe dotycza nie timestampow, lecz nienumerycznych wartosci dla wybranych sensorow.
3. Dane z sensorow humidity/temperature/head/ambient/current/power stanowia stabilna baze do kolejnych etapow (Milestone 2: modelowanie i analizy zaleznosci).