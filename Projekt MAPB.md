# **Opis projektu z przedmiotu**  ***“Modelowanie i analiza procesów biznesowych”***

**Konsultacje projektowe:**   
co dwa tygodnie (zgodnie z rozpiską w USOS)  
w poniedziałki w godz. 15:00-16:30 (C2 426\) 

**Projekty można realizować w grupach** (preferowane 2-4 osób na grupę).

**Postępy projektów powinny być konsultowane co najmniej raz w miesiącu.**  
Aby grupy nie musiały czekać na swoją godzinę konsultacji, będzie utworzony arkusz, w którym można zapisać się na slot konsultacyjny. W przypadku braku dostępnych slotów będzie możliwość umówienia się na konsultacje poza godzinami zajęć lub pierwszeństwo w kolejnym dostępnym terminie konsultacji. 

W ramach projektu każda grupa powinna wybrać co najmniej jeden zestaw danych ze strony: [https://zenodo.org/communities/iopt/](https://zenodo.org/communities/iopt/) do szczegółowej analizy. 

**Kamienie milowe**

**Milestone 1: Zrozumienie zbioru danych**

* opis zbioru danych i jego kontekstu (system, typ zdarzeń, liczba przypadków)  
* identyfikacja kluczowych atrybutów logu zdarzeń (case id, activity, timestamp, resource — które są, których brakuje)  
* analiza jakości danych (brakujące wartości, duplikaty, niespójne timestampy, niespójne typy danych, itp.)  
* eksploracyjna analiza danych  
* podstawowe statystyki (liczba eventów, cases, activities)  
* podstawowe wizualizacje (timeline, distribution, frequency)

**Wynik**: raport \+ jupyter notebook (np. na Google Colab).

**Milestone 2: Eksploracja danych i analiza cech**

* przygotowanie lub wybór logu zdarzeń  
* czyszczenie i normalizacja danych  
* wykrywanie wartości odstających (outlierów)  
* redukcja wymiarowości PCA / t-SNE / UMAP  
* klasteryzacja / inne wizualizacje  
* analiza relacji między zdarzeniami  
* identyfikacja ciekawych wzorców, np. wzorce czasowe (zachowanie w porach dnia, dni tygodnia, sezonowość),   
* analiza częstości ścieżek, najczęstszych wariantów  
* identyfikacja nietypowych zachowań, wykrywanie anomalii

**Wynik**: raport \+ jupyter notebook (np. na Google Colab).

**Milestone 3: Odkrywanie procesu i reguł**

* wygenerowanie modelu DFG (Directly-Follows Graph)  
* odkrycie modelu procesu odkrytego co najmniej dwoma różnymi algorytmami   
* stworzenie końcowego modelu BPMN, zaproponować ulepszenia  
* odkrycie reguł decyzyjnych  
* analiza zasobów (sieci współpracy, obciążenie pracowników)  
* identyfikacja problemów / wąskich gardeł procesu

W raporcie końcowym należy także dokonać interpretacji procesu uwzględniającej:

* co model mówi o analizowanym systemie  
* jakie są najczęstsze ścieżki procesu  
* gdzie pojawiają się opóźnienia  
* jakie mogą być potencjalne usprawnienia, wnioski biznesowe

**Wynik**: raport z modelami procesu (ew. jupyter notebook)

W ramach projektu możliwa jest także ścieżka badawcza (naukowa) polegająca na opracowaniu badań i przygotowaniu krótkiego artykułu naukowego na: 

* [https://www.yorku.ca/events/bpm2026/calls/call-for-responsible-bpm-forum/](https://www.yorku.ca/events/bpm2026/calls/call-for-responsible-bpm-forum/)  
* [https://www.yorku.ca/events/bpm2026/workshops/](https://www.yorku.ca/events/bpm2026/workshops/)

