import streamlit as st
import pandas as pd
import requests
import openai
import json

from utils.helpers import track_usage, render_wow_metrics

def render(openai_api_key):
    st.header("Krok 2: Analiza Produktów (Kaskada 4 Promptów)")
    render_wow_metrics()
    
    input_mode = st.radio("Sposób wprowadzania produktów:", ["Automatycznie przez URL (Jina Reader)", "Wpisz ręcznie opisy"])
    
    if input_mode == "Automatycznie przez URL (Jina Reader)":
        product_urls_text = st.text_area("Wklej adresy URL produktów klienta (po jednym w linii):", height=150)
        
        with st.expander("Opcje Jina Reader (Opcjonalne)"):
            css_include = st.text_input("Selektor CSS do uwzględnienia (np. .product-description):")
            css_exclude = st.text_input("Selektor CSS do wykluczenia (np. .footer, nav):")
            scrape_mode = st.selectbox("Tryb Jina Reader", ["Domyslnie", "Pomiń cache (X-No-Cache)"])
    else:
        st.markdown("Wprowadź opisy produktów ręcznie. Zostaną one poddane analizie AI z pominięciem pobierania z sieci.")
        default_manual_df = pd.DataFrame([{"URL/Nazwa": "Produkt 1", "Opis": "Krótki opis produktu..."}])
        manual_df = st.data_editor(default_manual_df, num_rows="dynamic", use_container_width=True)
        
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models_list = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-5.5", "gpt-5.4-mini", "o1-mini", "o3-mini"]
        reasoning_efforts = ["low", "medium", "high"]
        
        template_all = st.radio("Szablon Ustawień:", ["Domyślny (Ręczne parametry)", "Rekomendowany (Kaskada GPT-5.5 -> GPT-5.4-mini)"], index=0, key="template_all")
        
        if template_all == "Rekomendowany (Kaskada GPT-5.5 -> GPT-5.4-mini)":
            st.info("Zastosowano kaskadę 5 promptów (wg. nowych zaleceń).")
            params_1 = {"model": "gpt-5.5", "temperature": 0.0, "max_tokens": 16000, "reasoning_effort": "medium"}
            params_2 = {"model": "gpt-5.5", "temperature": 0.1, "max_tokens": 16000, "reasoning_effort": "medium"}
            params_3 = {"model": "gpt-5.4-mini", "temperature": 1.0, "max_tokens": 16000, "reasoning_effort": "low"}
            params_4 = {"model": "gpt-5.4-mini", "temperature": 1.0, "max_tokens": 16000, "reasoning_effort": "low"}
            params_5 = {"model": "gpt-5.4-mini", "temperature": 1.0, "max_tokens": 16000, "reasoning_effort": "medium"}
        else:
            st.warning("Ustawiasz parametry ręcznie dla każdego z 5 promptów.")
            t1p, t2p, t3p, t4p, t5p = st.tabs(["Parametry P1", "Parametry P2", "Parametry P3", "Parametry P4", "Parametry P5"])
            with t1p:
                m1 = st.selectbox("Model P1", models_list, index=models_list.index("gpt-5.4-mini"), key="m1")
                t1 = st.slider("Temp P1", 0.0, 2.0, 1.0 if m1 == "gpt-5.4-mini" else 0.0, 0.1, key="t1")
                r1 = st.selectbox("Reasoning P1", reasoning_efforts, index=1, key="r1")
                params_1 = {"model": m1, "temperature": 1.0 if m1 == "gpt-5.4-mini" else t1, "max_tokens": 16000, "reasoning_effort": r1}
            with t2p:
                m2 = st.selectbox("Model P2", models_list, index=models_list.index("gpt-5.4-mini"), key="m2")
                t2 = st.slider("Temp P2", 0.0, 2.0, 1.0 if m2 == "gpt-5.4-mini" else 0.1, 0.1, key="t2")
                r2 = st.selectbox("Reasoning P2", reasoning_efforts, index=1, key="r2")
                params_2 = {"model": m2, "temperature": 1.0 if m2 == "gpt-5.4-mini" else t2, "max_tokens": 16000, "reasoning_effort": r2}
            with t3p:
                m3 = st.selectbox("Model P3", models_list, index=models_list.index("gpt-5.4-mini"), key="m3")
                t3 = st.slider("Temp P3", 0.0, 2.0, 1.0 if m3 == "gpt-5.4-mini" else 0.1, 0.1, key="t3")
                r3 = st.selectbox("Reasoning P3", reasoning_efforts, index=0, key="r3")
                params_3 = {"model": m3, "temperature": 1.0 if m3 == "gpt-5.4-mini" else t3, "max_tokens": 16000, "reasoning_effort": r3}
            with t4p:
                m4 = st.selectbox("Model P4", models_list, index=models_list.index("gpt-5.4-mini"), key="m4")
                t4 = st.slider("Temp P4", 0.0, 2.0, 1.0 if m4 == "gpt-5.4-mini" else 0.1, 0.1, key="t4")
                r4 = st.selectbox("Reasoning P4", reasoning_efforts, index=0, key="r4")
                params_4 = {"model": m4, "temperature": 1.0 if m4 == "gpt-5.4-mini" else t4, "max_tokens": 16000, "reasoning_effort": r4}
            with t5p:
                m5 = st.selectbox("Model P5", models_list, index=models_list.index("gpt-5.4-mini"), key="m5")
                t5 = st.slider("Temp P5", 0.0, 2.0, 1.0 if m5 == "gpt-5.4-mini" else 0.0, 0.1, key="t5")
                r5 = st.selectbox("Reasoning P5", reasoning_efforts, index=1, key="r5")
                params_5 = {"model": m5, "temperature": 1.0 if m5 == "gpt-5.4-mini" else t5, "max_tokens": 16000, "reasoning_effort": r5}

        # PROMPT 1
        sys_1_def = """Jesteś rygorystycznym ekstraktorem danych produktowych dla produktów zdrowotnych, kosmetycznych, dermokosmetycznych, OTC, leków bez recepty i wyrobów medycznych.

Twoim zadaniem jest wyłącznie wyodrębnienie i uporządkowanie informacji podanych wprost na stronie produktu.

Nie interpretuj, nie rozwijaj, nie twórz pomysłów contentowych, nie dodawaj wiedzy ogólnej i nie dopowiadaj zastosowań, których nie ma w treści.

Najważniejsza zasada:
Masz przepisać i uporządkować wszystko, co strona mówi o produkcie: na co jest, jak działa, dla kogo jest, co zawiera, jakie ma wskazania, przeciwwskazania, ostrzeżenia, claimy i ograniczenia.

Zasady:
1. Zwróć wyłącznie poprawny JSON.
2. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
3. Nie wolno pominąć żadnego wskazania, zastosowania, problemu, choroby, objawu, claimu ani przeciwwskazania, które występuje w treści.
4. Nie twórz wniosków. Jeżeli czegoś nie ma w treści, wpisz "brak_danych_w_tresci".
5. Każdy ważny fakt powinien mieć pole "dokladne_brzmienie_z_tresci".
6. Jeżeli informacja jest prawdopodobna, ale nie podana wprost, nie wpisuj jej jako fakt.
7. Jeżeli produkt jest lekiem, OTC, kosmetykiem albo wyrobem medycznym, odnotuj to dokładnie tak, jak wynika z treści.
8. Jeżeli strona zawiera sekcję składu, wskazań, przeciwwskazań, działania, dawkowania, ostrzeżeń lub informacji prawnych, wyodrębnij ją osobno.
9. Nie poprawiaj języka źródła w polu "dokladne_brzmienie_z_tresci".
10. Pisz po polsku."""
        
        usr_1_def = """Przeanalizuj treść strony produktu i wyodrębnij wszystkie fakty podane wprost.

URL:
{url}

Treść strony:
{content}

Zadanie:
Wyciągnij pełną, uporządkowaną listę faktów o produkcie.

Szczególnie wyszukaj:
* nazwę produktu,
* status produktu, np. lek, lek bez recepty, OTC, kosmetyk, dermokosmetyk, wyrób medyczny,
* kategorię i postać produktu,
* składniki aktywne lub kluczowe,
* stężenia, dawki lub ilości składników, jeśli są podane,
* wszystkie wskazania,
* wszystkie zastosowania,
* wszystkie choroby, problemy skórne, objawy i stany wymienione na stronie,
* działanie produktu,
* mechanizm działania opisany na stronie,
* informacje o dostępności, np. bez recepty,
* grupy odbiorców,
* przeciwwskazania,
* ostrzeżenia,
* działania niepożądane,
* sposób użycia, jeśli występuje,
* claimy marketingowe,
* elementy wizualne lub opisy zdjęć, jeśli wynikają z treści,
* braki w danych, które są istotne dla dalszej analizy.

Zwróć wyłącznie JSON o poniższej strukturze. Odpowiadaj WYŁĄCZNIE surowym tekstem JSON (bez formatowania Markdown i bloków kodu ```json). Wewnątrz wartości tekstowych używaj wyłącznie pojedynczych apostrofów ('), unikaj podwójnych cudzysłowów ("), aby nie zepsuć parsowania JSON.
{
"produkt": {
"nazwa": "",
"url": "{url}",
"status_produktu": "lek | lek_bez_recepty | OTC | kosmetyk | dermokosmetyk | wyrob_medyczny | suplement | inny | brak_danych_w_tresci",
"kategoria": "",
"postac": "",
"typ_produktu": "",
"czy_produkt_jest_lekiem": true,
"czy_dostepny_bez_recepty": true,
"dokladne_brzmienie_statusu_z_tresci": ""
},
"sklad": {
"skladniki_aktywne_lub_kluczowe": [
{
"skladnik": "",
"ilosc_lub_stezenie": "",
"rola_opisana_na_stronie": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"inne_skladniki_istotne": [
{
"skladnik": "",
"rola_lub_uwaga": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"czy_sklad_podany_w_tresci": true
},
"wskazania_i_zastosowania": [
{
"nazwa": "",
"typ": "choroba | objaw | stan_skory | problem_kosmetyczny | zastosowanie | informacja_o_dostepnosci | claim_marketingowy | inne",
"czy_wskazanie_medyczne": true,
"czy_podane_wprost": true,
"dokladne_brzmienie_z_tresci": ""
}
],
"dzialanie_i_mechanizm": [
{
"dzialanie": "",
"mechanizm": "",
"czego_dotyczy": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"grupy_docelowe_wprost": [
{
"grupa": "",
"kontekst_lub_ograniczenie": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"przeciwwskazania": [
{
"przeciwwskazanie": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"ostrzezenia_i_ograniczenia": [
{
"ostrzezenie_lub_ograniczenie": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"dzialania_niepozadane": [
{
"dzialanie_niepozadane": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"sposob_uzycia_lub_dawkowanie": [
{
"informacja": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"claimy_marketingowe": [
{
"claim": "",
"typ_claimu": "unikalnosc | skutecznosc | sklad | dostepnosc | bezpieczenstwo | wygoda | inne",
"czy_claim_wymaga_weryfikacji_regulacyjnej": true,
"dokladne_brzmienie_z_tresci": ""
}
],
"elementy_wizualne_lub_kontekstowe": [
{
"element": "",
"znaczenie_dla_komunikacji": "",
"dokladne_brzmienie_z_tresci": ""
}
],
"kanoniczna_lista_zastosowan_do_dalszej_analizy": [
{
"zastosowanie": "",
"podstawa_w_tresci": "",
"typ": "wskazanie | objaw | choroba | stan_skory | mechanizm | claim | grupa_docelowa | inne"
}
],
"braki_w_danych": [
{
"brak": "",
"dlaczego_to_istotne": ""
}
],
"kontrola_jakosci": {
"liczba_wykrytych_wskazan_i_zastosowan": 0,
"czy_wszystkie_wskazania_maja_cytat_z_tresci": true,
"czy_odnaleziono_sklad": true,
"czy_odnaleziono_dzialanie": true,
"czy_odnaleziono_przeciwwskazania": true,
"uwagi": ""
}
}"""

        # PROMPT 2
        sys_2_def = """Jesteś analitykiem medyczno-kosmetycznym, strategiem SEO i strategiem contentowym.

Twoim zadaniem jest znalezienie nieoczywistych, ale logicznych i bezpiecznych punktów zaczepienia dla produktu na podstawie uporządkowanych faktów z poprzedniego kroku.

Nie analizujesz surowej strony. Analizujesz wyłącznie skonsolidowane fakty o produkcie.

Cel:
Znajdź dodatkowe konteksty, sytuacje, grupy odbiorców i związki przyczynowo-skutkowe, które mogą prowadzić do sensownych tematów contentowych.

Nie chodzi o ponowne wypisanie wskazań ze strony. Chodzi o odkrycie, co może wynikać z tych wskazań.

Przykłady dobrego myślenia:
* produkt na suchą skórę → sucha skóra nasila się zimą → temat o pielęgnacji skóry zimą,
* produkt na suchość skóry → terapia przeciwtrądzikowa może wysuszać skórę → temat o pielęgnacji skóry podczas terapii przeciwtrądzikowej,
* produkt na otarcia → sportowcy często mają otarcia → temat o ochronie skóry przy bieganiu lub jeździe na rowerze,
* produkt wspiera barierę skóry → można rozważyć tematy o regeneracji bariery skórnej.

Zasady:
1. Zwróć wyłącznie poprawny JSON.
2. Odpowiadaj WYŁĄCZNIE surowym tekstem JSON (bez formatowania Markdown i bloków kodu ```json). Wewnątrz wartości tekstowych używaj wyłącznie pojedynczych apostrofów ('), unikaj podwójnych cudzysłowów ("), aby nie zepsuć parsowania JSON.
3. Nie wymyślaj właściwości produktu.
4. Nie sugeruj leczenia problemów, których produkt nie leczy według faktów źródłowych.
5. Jeżeli produkt łagodzi objawy, nie zmieniaj tego w claim „leczy chorobę”.
6. Każdy insight musi mieć jasny związek: fakt o produkcie → przyczyna/kontekst → problem użytkownika → bezpieczny kierunek contentu.
7. Nie generuj kontekstów zbyt ogólnych, np. „zdrowie”, „uroda”, „sport”, „zima”, jeśli nie są połączone z konkretnym problemem.
8. Jeżeli związek jest pośredni, oznacz to jako "pośredni".
9. Jeżeli temat wymaga ostrożności medycznej, prawnej lub regulatory, ustaw "wymaga_weryfikacji": true.
10. Lepiej zwrócić mniej, ale trafniejszych insightów.
11. Pisz konkretnie i pod SEO."""
        
        usr_2_def = """Znajdź nieoczywiste punkty zaczepienia dla produktu na podstawie skonsolidowanych faktów.

Dane wejściowe:
{product_facts_json}

Cel:
Chcę znaleźć dodatkowe tematy i konteksty, które nie zawsze są wprost opisane na stronie produktu, ale logicznie wynikają z jego wskazań, działania lub problemów, które rozwiązuje.

Nie powtarzaj tylko wskazań ze strony. Szukaj zależności typu:
fakt o produkcie → przyczyna lub kontekst → problem użytkownika → rola produktu → bezpieczny temat contentowy

Szukaj zwłaszcza:
* sezonowości,
* aktywności fizycznej,
* tarcia, potu, pracy fizycznej i odzieży,
* terapii lub leków, które mogą powodować problemy wtórne,
* czynników zewnętrznych, np. mróz, wiatr, ogrzewanie, klimatyzacja, słońce,
* grup odbiorców, które mogą mieć dany problem,
* codziennych sytuacji, w których problem się pojawia,
* problemów wtórnych, gdzie produkt może być wsparciem, ale nie rozwiązaniem problemu pierwotnego.

Zwróć wyłącznie JSON:
{
"najwazniejsze_insighty": [
{
"insight": "",
"punkt_wyjscia_z_faktow": "",
"zwiazek_przyczynowo_skutkowy": "",
"problem_uzytkownika": "",
"rola_produktu": "",
"bezpieczny_kierunek_contentu": "",
"dopasowanie_do_produktu": "mocne | srednie | pośrednie",
"czego_nie_sugerowac": "",
"wymaga_weryfikacji": true,
"priorytet": "wysoki | sredni | niski"
}
],
"konteksty_do_rozwazenia": {
"sezonowe": [],
"lifestyle": [],
"medyczno_kosmetyczne": [],
"codzienne": [],
"grupy_odbiorcow": []
},
"tematy_ryzykowne_lub_do_odrzucenia": [
{
"temat": "",
"dlaczego_ryzykowny": "",
"bezpieczniejsze_zawężenie": ""
}
],
"podsumowanie": {
"najlepszy_punkt_zaczepienia": "",
"najwieksza_szansa_contentowa": "",
"najwieksze_ryzyko_naduzycia": ""
}
}"""

        # PROMPT 3
        sys_3_def = """Jesteś ekspertem SEO specjalizującym się w researchu słów kluczowych dla produktów zdrowotnych, medycznych, kosmetycznych, dermokosmetycznych, OTC i leków bez recepty.

Twoim zadaniem jest wygenerowanie krótkich seed keywords do dalszej analizy w Ahrefs Matching Terms.

Seed keyword to krótka fraza bazowa, która po wpisaniu w Ahrefs może odkryć całą rodzinę powiązanych zapytań.

Nie generujesz long-taili, tytułów artykułów ani fraz poradnikowych. Nie generujesz fraz typu „po bieganiu”, „zimą”, „dla dzieci”, „jak stosować”, jeśli nie są samodzielnym głównym tematem. Ahrefs odkryje takie rozwinięcia później.

ZABRONIONE FRAZY (ABSOLUTNY ZAKAZ GENEROWANIA):
- Nie generuj form produktu w oderwaniu od problemu (BEZWZGLĘDNIE ZAKAZANE: "maść", "krem", "spray", "tabletki", "lek bez recepty", "lek", "żel", "syrop").
- Nie generuj ogólnych kategorii (BEZWZGLĘDNIE ZAKAZANE: "kosmetyki", "leki", "suplementy").
- Nie generuj pojedynczych składników w oderwaniu od kontekstu problemu, jeśli nie stanowią samodzielnej, popularnej frazy SEO.

Twoim celem jest zwrócenie fraz bazowych najbliższych produktowi:
* wskazań,
* chorób wymienionych wprost,
* objawów,
* stanów skóry,
* problemów skórnych,
* składników,
* mechanizmów działania,
* kategorii produktu,
* głównych zastosowań.

Zasady:
1. Zwróć wyłącznie poprawny JSON.
2. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
3. Wygeneruj maksymalnie {max_keywords} fraz.
4. Jeśli {max_keywords} nie jest podane, wygeneruj maksymalnie 30 fraz.
5. Każda fraza ma mieć od 1 do 4 słów.
6. Frazy mają być po polsku.
7. Frazy mają być krótkie, bazowe i naturalne językowo.
8. Fraza powinna nadawać się do ręcznego wpisania w Ahrefs Matching Terms.
9. Priorytet mają frazy podane wprost w faktach produktu.
10. Nie generuj long-taili ani doprecyzowań sytuacyjnych, np. „odparzenia po bieganiu”, jeśli wystarczy seed „odparzenia”.
11. Nie generuj fraz sezonowych typu „sucha skóra zimą”, jeśli wystarczy seed „sucha skóra” albo „nadmierna suchość skóry”.
12. Nie generuj fraz z grupami odbiorców typu „sucha skóra u dzieci”, jeśli wystarczy seed „sucha skóra”, chyba że grupa odbiorców jest głównym wskazaniem produktu.
13. Nie generuj fraz z aktywnościami typu „otarcia po rowerze”, jeśli wystarczy seed „otarcia”.
14. Nie generuj fraz ogólnych i pustych znaczeniowo, np. „skóra”, „choroba”, „leczenie”, „zdrowie”, „problem”, „kosmetyk”.
15. Nie powielaj podobnych wariantów, np. „sucha skóra” i „skóra sucha”. Wybierz naturalniejszą.
16. Możesz dodać nazwę choroby jako seed, jeśli choroba występuje wprost w faktach produktu, np. „łuszczyca”.
17. Jeśli produkt według faktów łagodzi objawy choroby, możesz dodać zarówno seed choroby, jak i seed objawowy, ale oznacz je jako wymagające ostrożnej komunikacji.
18. Nie dodawaj nazw chorób, których nie ma w faktach produktu.
19. Kolejność fraz ma oznaczać priorytet — od najważniejszej do najmniej ważnej.
20. Nie twórz fraz wyłącznie po to, żeby dobić do limitu. Lepiej zwrócić mniej dobrych seedów niż dużo słabych."""
        
        usr_3_def = """Wygeneruj seed keywords SEO do Ahrefs Matching Terms na podstawie faktów wyodrębnionych ze strony produktu.

Dane wejściowe:
{product_facts_json}

Limit fraz:
{max_keywords}

Cel:
Chcę otrzymać krótkie frazy bazowe, które najlepiej nadają się do wpisania w Ahrefs Matching Terms.

Frazy mają pomóc znaleźć większe grupy zapytań związanych z produktem, jego wskazaniami, zastosowaniami, składnikami i problemami użytkowników.

Nie chcę długich fraz ani doprecyzowań typu:
* po bieganiu,
* zimą,
* latem,
* dla dzieci,
* u dorosłych,
* na twarz,
* jak stosować,
* co wybrać,
* poradnik,
* objawy i przyczyny.

Jeżeli istnieje seed ogólny, wybierz seed ogólny:
* zamiast „odparzenia po bieganiu” wybierz „odparzenia”,
* zamiast „sucha skóra zimą” wybierz „sucha skóra” albo „nadmierna suchość skóry”,
* zamiast „łagodzenie objawów łuszczycy u dzieci” wybierz „łagodzenie objawów łuszczycy”, „objawy łuszczycy” albo „łuszczyca”,
* zamiast „olej lniany na skórę” wybierz „olej lniany”.

Uwzględnij przede wszystkim:
* wskazania wprost z produktu,
* choroby wymienione wprost,
* objawy wymienione wprost,
* stany skóry,
* składniki aktywne lub kluczowe,
* mechanizmy działania,
* typ produktu, jeśli jest istotny,
* status produktu, jeśli może mieć znaczenie SEO.

Zwróć wyłącznie JSON:
{
"seed_keywords": [
"fraza 1",
"fraza 2",
"fraza 3"
],
"keyword_details": [
{
"fraza": "",
"typ": "wskazanie | choroba | objaw | stan_skory | skladnik | mechanizm | typ_produktu | status | inne",
"podstawa_w_faktach": "",
"dlaczego_to_dobry_seed_do_ahrefs": "",
"priorytet": "wysoki | sredni | niski",
"czy_wymaga_ostroznej_komunikacji": true
}
],
"odrzucone_lub_zawężone_frazy": [
{
"fraza": "",
"powod": "zbyt_dlugie | zbyt_sytuacyjne | zbyt_ogolne | duplikat | niepotwierdzone | lepszy_seed_ogolny",
"zastapione_przez": ""
}
]
}"""

        # PROMPT 4
        sys_4_def = """Jesteś ekspertem SEO i strategiem słów kluczowych. Generujesz seed keywords do Ahrefs Matching Terms na podstawie rozszerzonej analizy produktu.

Twoim zadaniem nie jest tworzenie długich fraz contentowych. Twoim zadaniem jest wybranie krótkich, bazowych tematów, które po wpisaniu w Ahrefs mogą odkryć dużą rodzinę zapytań.

Rozszerzona analiza może zawierać sezonowość, sport, pracę fizyczną, grupy odbiorców, skutki uboczne terapii, codzienne sytuacje i konteksty lifestyle’owe. Nie oznacza to, że masz generować frazy z tymi doprecyzowaniami.

ZABRONIONE FRAZY (ABSOLUTNY ZAKAZ GENEROWANIA):
- Nie generuj form produktu w oderwaniu od problemu (BEZWZGLĘDNIE ZAKAZANE: "maść", "krem", "spray", "tabletki", "lek bez recepty", "lek", "żel", "syrop").
- Nie generuj ogólnych kategorii (BEZWZGLĘDNIE ZAKAZANE: "kosmetyki", "leki", "suplementy").
- Nie generuj pojedynczych składników w oderwaniu od kontekstu problemu.

Masz wyciągnąć z tej analizy tylko najlepsze, bazowe frazy:
* problem,
* objaw,
* stan skóry,
* skutek,
* składnik,
* mechanizm,
* choroba, jeśli występuje wprost w danych źródłowych,
* ogólny typ zastosowania.

Przykłady redukcji:
* „otarcia przy bieganiu” → „otarcia”
* „otarcia po rowerze” → „otarcia”
* „sucha skóra zimą” → „sucha skóra” albo „przesuszona skóra”
* „regeneracja skóry po mrozie” → „regeneracja skóry”
* „sucha skóra po terapii przeciwtrądzikowej” → „sucha skóra” albo „przesuszona skóra”
* „pielęgnacja skóry dziecka zimą” → „pielęgnacja skóry dziecka” tylko jeśli grupa dzieci jest istotna i potwierdzona; w innym przypadku „pielęgnacja skóry”
* „łagodzenie objawów łuszczycy” → zostaw jako seed, jeśli wynika z faktów produktu
* „łuszczyca” → dopuszczalne, jeśli choroba występuje wprost w faktach produktu

Zasady:
1. Zwróć wyłącznie poprawny JSON.
2. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
3. Wygeneruj maksymalnie {max_keywords} fraz.
4. Jeśli {max_keywords} nie jest podane, wygeneruj maksymalnie 40 fraz.
5. Każda fraza ma mieć od 1 do 4 słów.
6. Frazy mają być po polsku.
7. Frazy mają być krótkie, bazowe i przydatne w Ahrefs Matching Terms.
8. Nie generuj fraz pełniących funkcję tytułu artykułu.
9. Nie generuj pytań.
10. Nie generuj fraz zbyt długich, sytuacyjnych ani poradnikowych.
11. Nie generuj pojedynczych ogólników typu „zima”, „lato”, „sport”, „dzieci”, „choroba”, „leczenie”, „skóra”.
12. Nie generuj fraz, które same w sobie nie mają silnego związku z produktem.
13. Nie generuj doprecyzowań, które Ahrefs może odkryć samodzielnie na bazie krótszego seedu.
14. Jeżeli dłuższa fraza jest tylko wariantem krótszego seedu, wybierz krótszy seed.
15. Możesz dodać nazwę choroby jako seed tylko wtedy, gdy występuje w faktach źródłowych produktu.
16. Nie dodawaj chorób ani terapii wyłącznie na podstawie luźnych kontekstów contentowych.
17. Jeżeli produkt może wspierać skutek problemu, a nie problem pierwotny, wybierz seed dotyczący skutku.
18. Kolejność fraz ma oznaczać priorytet.
19. Lepiej zwrócić mniej fraz, ale bardzo trafnych, niż dużo szerokich i słabych.
20. Każda fraza musi mieć wyjaśnienie, dlaczego jest dobrym seedem do Ahrefs."""
        
        usr_4_def = """Wygeneruj seed keywords SEO do Ahrefs Matching Terms na podstawie rozszerzonej analizy produktu.

Rozszerzona analiza produktu:
{expanded_product_analysis_json}

Fakty źródłowe produktu:
{product_facts_json}

Limit fraz:
{max_keywords}

Cel:
Chcę otrzymać krótkie frazy bazowe, które można wpisać w Ahrefs Matching Terms, aby odkryć powiązane zapytania użytkowników.

Nie chcę fraz zbyt szczegółowych. Nie chcę fraz typu:
* odparzenia po bieganiu,
* sucha skóra zimą,
* skóra po treningu,
* pielęgnacja skóry sportowca,
* jak chronić skórę przed mrozem,
* objawy suchej skóry u dziecka,
* maść na otarcia po rowerze.

Jeśli wystarczy krótszy seed, wybierz krótszy seed:
* „odparzenia” zamiast „odparzenia po bieganiu”,
* „otarcia” zamiast „otarcia przy sporcie”,
* „sucha skóra” zamiast „sucha skóra zimą”,
* „regeneracja skóry” zamiast „regeneracja skóry po mrozie”,
* „bariera skórna” zamiast „regeneracja bariery skórnej zimą”,
* „olej lniany” zamiast „olej lniany na suchą skórę”.

Uwzględnij wyłącznie frazy, które są mocno powiązane z produktem, jego wskazaniami, mechanizmem działania lub bezpiecznymi zastosowaniami.

Zwróć wyłącznie JSON:
{
"seed_keywords": [
"fraza 1",
"fraza 2",
"fraza 3"
],
"keyword_groups": {
"wskazania_i_choroby": [],
"objawy_i_stany_skory": [],
"skladniki": [],
"mechanizm_dzialania": [],
"zastosowania": [],
"grupy_odbiorcow_tylko_jesli_istotne": []
},
"keyword_details": [
{
"fraza": "",
"typ": "wskazanie | choroba | objaw | stan_skory | skladnik | mechanizm | zastosowanie | grupa_odbiorcow | inne",
"powiazane_zastosowanie": "",
"podstawa": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"dlaczego_to_dobry_seed_do_ahrefs": "",
"czy_to_seed_bazowy_zamiast_long_tail": true,
"priorytet": "wysoki | sredni | niski",
"ryzyko_claimu": "niskie | srednie | wysokie",
"uwaga_komunikacyjna": ""
}
],
"frazy_odrzucone_lub_zredukowane": [
{
"fraza_pierwotna": "",
"powod": "zbyt_sytuacyjna | zbyt_długa | zbyt_ogolna | duplikat | niepotwierdzona | lepszy_seed_bazowy",
"zastapiona_przez": ""
}
]
}"""

        # PROMPT 5
        sys_5_def = """Jesteś strategiem SEO, analitykiem Content Gap, redaktorem naczelnym i ekspertem medyczno-kosmetycznym dla produktów zdrowotnych, kosmetycznych, dermokosmetycznych, OTC oraz leków bez recepty.

Twoim zadaniem jest przygotowanie skonsolidowanego kontekstu produktu, który później zostanie użyty przez inny model do oceny, czy temat znaleziony u konkurencji można bezpiecznie i sensownie opisać na blogu lub stronie producenta.

Nie tworzysz tekstu marketingowego. Nie tworzysz JSON-a. Nie generujesz seed keywords. Nie piszesz artykułu.

Tworzysz praktyczny, decyzyjny brief produktu, który pomaga ocenić:
* do jakich tematów produkt pasuje bezpośrednio,
* do jakich tematów pasuje tylko warunkowo,
* do jakich tematów nie należy go naciągać,
* jakie problemy użytkownika produkt realnie adresuje,
* jakie claimy są bezpieczne,
* jakie claimy są ryzykowne,
* kiedy temat konkurencji powinien zostać zaakceptowany,
* kiedy powinien zostać odrzucony.

Kontekst musi być zrozumiały dla modelu, który później będzie miał tylko:
* URL konkurencji,
* Title konkurencji,
* ten kontekst produktu.

Dlatego pisz jasno, konkretnie i decyzyjnie.

Zasady:
1. Nie zwracaj JSON-a.
2. Nie używaj bloków kodu.
3. Pisz po polsku.
4. Używaj nagłówków i list punktowanych.
5. Nie pisz zbyt literacko ani marketingowo.
6. Nie kopiuj całych analiz 1:1 — skonsoliduj je.
7. Nie dodawaj wiedzy, której nie da się uzasadnić faktami produktu lub bezpiecznym wnioskiem.
8. Wyraźnie oddzielaj:
   * fakty ze strony,
   * bezpieczne wnioski,
   * tematy warunkowe,
   * tematy ryzykowne,
   * tematy do odrzucenia.
9. Jeśli produkt łagodzi objawy choroby, nie pisz, że leczy chorobę.
10. Jeśli produkt wspiera regenerację, nawilżenie, natłuszczanie lub ochronę skóry, nie zmieniaj tego w claim leczenia chorób.
11. Przy chorobach, dzieciach, niemowlętach, ciąży, ranach, infekcjach, alergiach, przeciwwskazaniach i działaniach niepożądanych zachowaj szczególną ostrożność.
12. Jeżeli temat wymaga weryfikacji medycznej, prawnej, regulatory, ChPL, ulotki lub etykiety, zaznacz to wyraźnie.
13. Brief ma pomagać później odrzucać luźno powiązane tematy, dlatego jasno napisz, czego nie akceptować.
14. Tematy mają być opisane na poziomie problemów i intencji użytkownika, a nie jako lista słów kluczowych.
15. Każde zastosowanie produktu podane wprost w danych wejściowych musi zostać uwzględnione.
16. Jeżeli produkt ma kilka zastosowań, nie sprowadzaj go do jednego problemu.
17. Output powinien być możliwie kompletny, ale nie rozwlekły. Ma być użyteczny jako `{products_context}` w kolejnym promptcie."""

        usr_5_def = """Przygotuj skonsolidowany kontekst produktu do późniejszej analizy Content Gap.

Dane wejściowe:

Podstawowa ekstrakcja faktów ze strony produktu:
{product_facts_json}

Pogłębiona analiza produktu:
{expanded_product_analysis_json}

Cel:
Chcę otrzymać tekstowy `{products_context}`, który będzie później podstawiany do promptu analizującego URL i Title konkurencji.

Ten kontekst ma pomóc innemu modelowi bardzo rygorystycznie ocenić, czy temat konkurencji jest:
* mocno zgodny z produktem,
* tylko warunkowo zgodny,
* luźno powiązany,
* albo powinien zostać odrzucony.

Nie pisz o tym, że kontekst będzie porównywany z konkurencją. Po prostu przygotuj brief produktu w taki sposób, aby jasno wynikało:
* na jakie tematy produkt pasuje,
* na jakie tematy nie pasuje,
* gdzie są granicę komunikacji.

Zwróć tekst w poniższej strukturze:

# Kontekst produktu do oceny tematów contentowych

## 1. Produkt
Podaj:
* nazwę produktu,
* URL produktu, jeśli jest dostępny w danych,
* status produktu,
* typ i postać produktu,
* kategorię,
* najważniejsze składniki aktywne lub kluczowe,
* krótką rolę produktu.
Pisz konkretnie. Nie twórz opisu marketingowego.

## 2. Wskazania i zastosowania podane wprost
Wypisz wszystkie wskazania, zastosowania, problemy, choroby, objawy i stany skóry podane wprost w danych.
Dla każdego elementu podaj:
* nazwę wskazania lub zastosowania,
* czy jest to choroba, objaw, stan skóry, problem pielęgnacyjny, mechanizm czy claim,
* jak produkt jest z nim powiązany,
* czy komunikacja wymaga ostrożności.
Nie pomijaj żadnego wskazania z danych wejściowych.

## 3. Problemy, które produkt adresuje bezpośrednio
Wypisz problemy, dla których produkt jest bezpośrednio dopasowany według danych źródłowych.
Dla każdego problemu podaj:
* problem użytkownika,
* rola produktu,
* bezpieczny sposób komunikacji,
* przykładowe typy tematów, które byłyby zgodne,
* czego nie należy obiecywać.
To są tematy, które powinny być traktowane jako najmocniej zgodne z produktem.

## 4. Problemy, które produkt może wspierać pośrednio
Wypisz problemy i konteksty, które są powiązane z produktem, ale nie powinny być traktowane jako główne wskazanie.
Dla każdego podaj:
* problem pierwotny,
* problem wtórny lub skutek, z którym produkt może się łączyć,
* dlaczego związek jest pośredni,
* jak bezpiecznie zawęzić temat,
* czego nie sugerować.
Przykładowa logika: Jeżeli produkt może wspierać suchość skóry po jakiejś terapii, to bezpieczny temat powinien dotyczyć suchości skóry, a nie leczenia choroby pierwotnej.

## 5. Mechanizm działania jako podstawa dopasowania tematów
Wyjaśnij krótko, jak działa produkt według danych.
Uwzględnij:
* co robi na poziomie skóry lub naskórka,
* jaki problem użytkownika to adresuje,
* jakie tematy mogą wynikać z tego mechanizmu,
* jakich wniosków nie należy z tego mechanizmu wyciągać.
Ta sekcja ma pomagać rozpoznawać tematy powiązane z mechanizmem działania, np. bariera skóry, utrata wody, regeneracja, natłuszczenie, nawilżenie — ale tylko jeśli wynikają z danych.

## 6. Grupy odbiorców istotne dla produktu
Wypisz tylko te grupy odbiorców, które wynikają z danych albo są mocno uzasadnionym wnioskiem.
Dla każdej grupy podaj:
* dlaczego może być istotna,
* z jakim problemem przychodzi,
* czy wynika wprost z danych czy z wniosku,
* jakie tematy można rozważyć,
* jakie ryzyka komunikacyjne występują.
Nie dodawaj grup odbiorców luźno powiązanych.

## 7. Naturalne konteksty tematyczne
Wypisz konteksty, w których produkt naturalnie pasuje do problemu użytkownika.
Podziel je na:
* medyczno-kosmetyczne,
* pielęgnacyjne,
* codzienne,
* sezonowe,
* lifestyle’owe.
Przy każdym kontekście podaj:
* z którym wskazaniem lub mechanizmem się łączy,
* czy jest to mocne, średnie czy słabe dopasowanie,
* czy wymaga ostrożności.
Nie dodawaj kontekstów, które są zbyt ogólne, np. samo „zdrowie”, „sport”, „lato”, „zima”, jeśli nie wynikają jasno z problemu produktu.

## 8. Tematy mocno zgodne z produktem
Wypisz obszary tematyczne, które można uznać za mocno zgodne z produktem.
Dla każdego obszaru napisz:
* dlaczego pasuje,
* z którym wskazaniem lub działaniem produktu się łączy,
* jaka intencja użytkownika jest tu naturalna,
* czy temat może być traktowany jako bezpośrednio dopasowany.
To są obszary, przy których późniejsza ocena powinna łatwiej akceptować temat, jeśli URL lub Title jasno wskazuje poradnikowy charakter.

## 9. Tematy zgodne warunkowo
Wypisz tematy, które można rozważać tylko wtedy, gdy są odpowiednio zawężone.
Dla każdego tematu podaj:
* dlaczego jest warunkowy,
* jaki zakres byłby bezpieczny,
* jaki zakres byłby naciągany,
* czy wymaga weryfikacji.
To są tematy, które nie powinny być automatycznie akceptowane. Muszą mieć w URL-u lub Title jasny związek z problemem, który produkt rzeczywiście adresuje.

## 10. Tematy do odrzucenia lub naciągane
Wypisz tematy, które należy odrzucać, jeśli pojawią się jako zbyt luźno powiązane z produktem.
Dla każdego tematu podaj:
* dlaczego nie pasuje,
* jaki claim byłby nadużyciem,
* czy istnieje bezpieczniejsze zawężenie tematu.
Uwzględnij szczególnie:
* choroby, których produkt nie leczy według danych,
* problemy pierwotne, wobec których produkt może być co najwyżej wsparciem skutku,
* tematy zbyt ogólne,
* tematy lifestyle’owe bez jasnego związku z produktem,
* zastosowania poza zakresem danych,
* claimy o leczeniu, których nie ma w danych.

## 11. Reguły akceptacji tematów
Napisz praktyczne reguły decyzyjne.
Podziel je na:
### Akceptuj, jeśli:
Wypisz warunki, przy których temat jest mocno zgodny z produktem.
### Akceptuj warunkowo, jeśli:
Wypisz warunki, przy których temat może być rozważony, ale wymaga zawężenia lub ostrożności.
### Odrzuć, jeśli:
Wypisz warunki, przy których temat jest zbyt luźny, ryzykowny albo niezgodny z produktem.

## 12. Bezpieczne claimy i komunikaty
Wypisz, jak można bezpiecznie mówić o produkcie.
Podaj:
* bezpieczne sformułowania,
* bezpieczne kierunki komunikacji,
* neutralne określenia roli produktu,
* komunikaty wymagające ostrożności.
Nie twórz obietnic skuteczności, jeśli nie wynikają z danych.

## 13. Claimy ryzykowne i komunikaty do unikania
Wypisz, czego nie należy sugerować.
Uwzględnij:
* leczenie chorób, jeśli produkt tylko łagodzi objawy,
* obietnice pełnego rozwiązania problemu,
* stosowanie poza zakresem danych,
* twierdzenia o bezpieczeństwie dla grup, których nie potwierdzają dane,
* porównania z konkurencją bez podstawy,
* claims wymagające weryfikacji regulatory.

## 14. Najważniejsze granice dopasowania
Napisz krótkie, decyzyjne podsumowanie:
* produkt jest mocno dopasowany do tematów związanych z...
* produkt jest warunkowo dopasowany do tematów związanych z...
* produkt nie powinien być łączony z tematami dotyczącymi...
* największe ryzyko polega na...
* najbezpieczniej traktować produkt jako..."""

        t1, t2, t3, t4, t5 = st.tabs(["1. Ekstrakcja", "2. Rozszerzona", "3. Frazy z Faktów", "4. Frazy z Analizy", "5. Kontekst CG"])
        with t1:
            step2_sys_1 = st.text_area("System (P1)", value=sys_1_def, height=200, key="s1")
            step2_user_1 = st.text_area("User (P1)", value=usr_1_def, height=200, key="u1")
        with t2:
            step2_sys_2 = st.text_area("System (P2)", value=sys_2_def, height=200, key="s2")
            step2_user_2 = st.text_area("User (P2)", value=usr_2_def, height=200, key="u2")
        with t3:
            step2_sys_3 = st.text_area("System (P3)", value=sys_3_def, height=200, key="s3")
            step2_user_3 = st.text_area("User (P3)", value=usr_3_def, height=200, key="u3")
        with t4:
            step2_sys_4 = st.text_area("System (P4)", value=sys_4_def, height=200, key="s4")
            step2_user_4 = st.text_area("User (P4)", value=usr_4_def, height=200, key="u4")
        with t5:
            step2_sys_5 = st.text_area("System (P5)", value=sys_5_def, height=200, key="s5")
            step2_user_5 = st.text_area("User (P5)", value=usr_5_def, height=200, key="u5")

        def analyze_single_product(url, content, client, idx=0, total=1, my_bar=None):
            try:
                if content is None:
                    headers = {
                        "Accept": "application/json",
                        "X-Retain-Images": "none"
                    }
                    if st.session_state.get("jina_api_key"):
                        headers["Authorization"] = f"Bearer {st.session_state.jina_api_key}"
                    if scrape_mode == "Pomiń cache (X-No-Cache)":
                        headers["X-No-Cache"] = "true"
                    if css_include:
                        headers["X-Target-Selector"] = css_include
                    
                    jina_url = f"https://r.jina.ai/{url}"
                    response = requests.get(jina_url, headers=headers)
                    if response.status_code == 200:
                        content = response.json().get('data', {}).get('content', response.text)
                    else:
                        st.error(f"Błąd pobierania strony {url}: {response.status_code}")
                        return None
                    
                if content:
                    content_clipped = content[:8000]
                    
                    from utils.helpers import track_usage
                    
                    # --- PROMPT 1 ---
                    prompt_1 = step2_user_1.replace("{url}", url).replace("{content}", content_clipped)
                    call_1_kwargs = {"model": params_1["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_1}, {"role": "user", "content": prompt_1}]}
                    if "temperature" in params_1: call_1_kwargs["temperature"] = params_1["temperature"]
                    if "max_tokens" in params_1:
                            if any(m in params_1["model"] for m in ["gpt-5", "o1", "o3"]): call_1_kwargs["max_completion_tokens"] = params_1["max_tokens"]
                            else: call_1_kwargs["max_tokens"] = params_1["max_tokens"]
                    if "reasoning_effort" in params_1: call_1_kwargs["reasoning_effort"] = params_1["reasoning_effort"]
                    resp1 = client.chat.completions.create(**call_1_kwargs)
                    r1 = resp1.choices[0].message.content
                    if resp1.usage: track_usage(params_1["model"], resp1.usage.prompt_tokens, resp1.usage.completion_tokens)
                    
                    # --- PROMPT 2 ---
                    prompt_2 = step2_user_2.replace("{product_facts_json}", r1)
                    call_2_kwargs = {"model": params_2["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_2}, {"role": "user", "content": prompt_2}]}
                    if "temperature" in params_2: call_2_kwargs["temperature"] = params_2["temperature"]
                    if "max_tokens" in params_2:
                            if any(m in params_2["model"] for m in ["gpt-5", "o1", "o3"]): call_2_kwargs["max_completion_tokens"] = params_2["max_tokens"]
                            else: call_2_kwargs["max_tokens"] = params_2["max_tokens"]
                    if "reasoning_effort" in params_2: call_2_kwargs["reasoning_effort"] = params_2["reasoning_effort"]
                    resp2 = client.chat.completions.create(**call_2_kwargs)
                    r2 = resp2.choices[0].message.content
                    if resp2.usage: track_usage(params_2["model"], resp2.usage.prompt_tokens, resp2.usage.completion_tokens)
                    
                    # --- PROMPT 3 ---
                    prompt_3 = step2_user_3.replace("{product_facts_json}", r1).replace("{max_keywords}", "30")
                    call_3_kwargs = {"model": params_3["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_3}, {"role": "user", "content": prompt_3}]}
                    if "temperature" in params_3: call_3_kwargs["temperature"] = params_3["temperature"]
                    if "max_tokens" in params_3:
                            if any(m in params_3["model"] for m in ["gpt-5", "o1", "o3"]): call_3_kwargs["max_completion_tokens"] = params_3["max_tokens"]
                            else: call_3_kwargs["max_tokens"] = params_3["max_tokens"]
                    if "reasoning_effort" in params_3: call_3_kwargs["reasoning_effort"] = params_3["reasoning_effort"]
                    resp3 = client.chat.completions.create(**call_3_kwargs)
                    r3 = resp3.choices[0].message.content
                    if resp3.usage: track_usage(params_3["model"], resp3.usage.prompt_tokens, resp3.usage.completion_tokens)
                    
                    # --- PROMPT 4 ---
                    prompt_4 = step2_user_4.replace("{product_facts_json}", r1).replace("{expanded_product_analysis_json}", r2).replace("{max_keywords}", "50")
                    call_4_kwargs = {"model": params_4["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_4}, {"role": "user", "content": prompt_4}]}
                    if "temperature" in params_4: call_4_kwargs["temperature"] = params_4["temperature"]
                    if "max_tokens" in params_4:
                            if any(m in params_4["model"] for m in ["gpt-5", "o1", "o3"]): call_4_kwargs["max_completion_tokens"] = params_4["max_tokens"]
                            else: call_4_kwargs["max_tokens"] = params_4["max_tokens"]
                    if "reasoning_effort" in params_4: call_4_kwargs["reasoning_effort"] = params_4["reasoning_effort"]
                    resp4 = client.chat.completions.create(**call_4_kwargs)
                    r4 = resp4.choices[0].message.content
                    if resp4.usage: track_usage(params_4["model"], resp4.usage.prompt_tokens, resp4.usage.completion_tokens)
                    
                    # --- PROMPT 5 ---
                    prompt_5 = step2_user_5.replace("{product_facts_json}", r1).replace("{expanded_product_analysis_json}", r2)
                    call_5_kwargs = {"model": params_5["model"], "messages": [{"role": "system", "content": step2_sys_5}, {"role": "user", "content": prompt_5}]}
                    if "temperature" in params_5: call_5_kwargs["temperature"] = params_5["temperature"]
                    if "max_tokens" in params_5:
                            if any(m in params_5["model"] for m in ["gpt-5", "o1", "o3"]): call_5_kwargs["max_completion_tokens"] = params_5["max_tokens"]
                            else: call_5_kwargs["max_tokens"] = params_5["max_tokens"]
                    if "reasoning_effort" in params_5: call_5_kwargs["reasoning_effort"] = params_5["reasoning_effort"]
                    resp5 = client.chat.completions.create(**call_5_kwargs)
                    r5 = resp5.choices[0].message.content
                    if resp5.usage: track_usage(params_5["model"], resp5.usage.prompt_tokens, resp5.usage.completion_tokens)
                    
                    d1, d2, d3, d4 = {}, {}, {}, {}
                    from utils.helpers import clean_json
                    
                    try: d1 = json.loads(clean_json(r1))
                    except Exception: st.warning("Błąd parsowania JSON dla P1")
                    
                    try: d2 = json.loads(clean_json(r2))
                    except Exception: st.warning("Błąd parsowania JSON dla P2")
                    
                    try: d3 = json.loads(clean_json(r3))
                    except Exception: st.warning("Błąd parsowania JSON dla P3")
                    
                    try: d4 = json.loads(clean_json(r4))
                    except Exception: st.warning("Błąd parsowania JSON dla P4")
                    
                    phrases_3 = [str(x).strip().lower() for x in d3.get("seed_keywords", [])] if d3 else []
                    phrases_4 = [str(x).strip().lower() for x in d4.get("seed_keywords", [])] if d4 else []
                    combined_phrases = list(dict.fromkeys(phrases_3 + phrases_4))
                    
                    md_lines = []
                    if "produkt" in d1:
                        md_lines.append("### 🏷 Fakty wyodrębnione z treści (P1)")
                        p1 = d1["produkt"]
                        md_lines.append(f"- **Nazwa:** {p1.get('nazwa', '')} | **Status:** {p1.get('status_produktu', '')} | **Kategoria:** {p1.get('kategoria', '')}")
                        md_lines.append(f"- **Wskazania wprost:** " + ", ".join([w.get('nazwa', '') for w in d1.get('wskazania_i_zastosowania', []) if isinstance(w, dict)]))
                        md_lines.append("")
                    
                    if "podsumowanie" in d2:
                        p2 = d2["podsumowanie"]
                        md_lines.append("### 🎯 Analiza Rozszerzona (P2)")
                        md_lines.append(f"- **Wniosek:** {p2.get('najwazniejszy_wniosek', '')}")
                        md_lines.append(f"- **Szansa contentowa:** {d2.get('profil_strategiczny_produktu', {}).get('najwieksza_szansa_contentowa', '')}")
                        md_lines.append(f"- **Ryzyko:** {p2.get('najwieksze_ryzyko', '')}")
                        md_lines.append("")
                        
                    md_lines.append("### 🔍 Frazy SEO (P3 + P4)")
                    md_lines.append(f"Wygenerowano łącznie **{len(combined_phrases)}** unikalnych seed keywords.")
                    md_lines.append(f"Przykładowe 10 fraz: {', '.join(combined_phrases[:10])}...")
                    md_lines.append("")

                    md_lines.append("### 📦 Pełne JSONy na dole rozwijanej sekcji")
                    
                    analysis_text = "\n".join(md_lines)
                        
                    return {
                        "url": url,
                        "analysis": analysis_text,
                        "seed_keywords": combined_phrases,
                        "json1": d1,
                        "json2": d2,
                        "json3": d3,
                        "json4": d4,
                        "products_context": r5,
                        "raw_content": content_clipped
                    }
                else:
                    st.warning(f"Brak zawartości do analizy dla {url}")
                    return None
            except Exception as e:
                st.error(f"Błąd analizy {url}: {e}")
                return None
            finally:
                if my_bar:
                    progress_value = min(1.0, (idx + 1) / total)
                    my_bar.progress(progress_value, text=f"Przeanalizowano {idx+1} z {total} produktów.")

    if st.button("Rozpocznij Kaskadę 5 Promptów", type="primary"):
        if not openai_api_key:
            st.error("Wymagany klucz API OpenAI.")
        else:
            product_analysis = []
            
            if input_mode == "Automatycznie przez URL (Jina Reader)":
                urls = [u.strip() for u in product_urls_text.split("\n") if u.strip()]
                if not urls:
                    st.warning("Podaj przynajmniej jeden adres URL.")
                    st.stop()
                items_to_analyze = [{"url": u, "content": None} for u in urls]
            else:
                items_to_analyze = []
                for idx, row in manual_df.iterrows():
                    u = str(row.get("URL/Nazwa", "")).strip()
                    c = str(row.get("Opis", "")).strip()
                    if u and c and c != "Krótki opis produktu...":
                        items_to_analyze.append({"url": u, "content": c})
                if not items_to_analyze:
                    st.warning("Uzupełnij przynajmniej jeden produkt z opisem w tabeli (nie używaj domyślnego tekstu).")
                    st.stop()
            
            progress_text = "Analiza produktów w toku..."
            my_bar = st.progress(0, text=progress_text)
            client = openai.OpenAI(api_key=openai_api_key)
            
            for idx, item in enumerate(items_to_analyze):
                res = analyze_single_product(item["url"], item["content"], client, idx, len(items_to_analyze), my_bar)
                if res:
                    product_analysis.append(res)
                
            st.session_state.product_analysis = product_analysis
            st.success("Kaskada zakończona!")
            
    if "product_analysis" in st.session_state:
        st.subheader("Wyniki Analizy AI")
        
        from utils.helpers import to_excel_multi
        
        p1_fakty_data = []
        p2_zastosowania_data = []
        p2_strategia_data = []
        p3_frazy_data = []
        p4_frazy_data = []
        p5_kontekst_data = []
        
        for item in st.session_state.product_analysis:
            url = item["url"]
            j1 = item.get("json1", {})
            j2 = item.get("json2", {})
            j3 = item.get("json3", {})
            j4 = item.get("json4", {})
            
            with st.expander(f"📊 Analiza dla: {url}", expanded=True):
                st.markdown("### 🏷️ Profil Produktu")
                p1 = j1.get("produkt", {})
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Nazwa", p1.get("nazwa", "Brak"))
                c2.metric("Status", p1.get("status_produktu", "Brak"))
                c3.metric("Kategoria", p1.get("kategoria", "Brak"))
                
                st.markdown("### 🎯 Strategia & Wnioski")
                podsumowanie = j2.get("podsumowanie", {})
                if podsumowanie:
                    if podsumowanie.get("najlepszy_punkt_zaczepienia"):
                        st.info(f"**Najlepszy Punkt Zaczepienia:** {podsumowanie.get('najlepszy_punkt_zaczepienia')}")
                    if podsumowanie.get("najwieksza_szansa_contentowa"):
                        st.success(f"**Szansa Contentowa:** {podsumowanie.get('najwieksza_szansa_contentowa')}")
                    if podsumowanie.get("najwieksze_ryzyko_naduzycia"):
                        st.warning(f"**Największe ryzyko:** {podsumowanie.get('najwieksze_ryzyko_naduzycia')}")
                
                st.markdown("### 🔑 Słowa Kluczowe")
                seed_kw = item.get("seed_keywords", [])
                st.write(f"Wygenerowano łącznie **{len(seed_kw)}** unikalnych seed keywords.")
                if seed_kw:
                    st.write(", ".join(seed_kw[:20]) + ("..." if len(seed_kw)>20 else ""))
                
                st.markdown("### 📝 Kontekst Content Gap (P5)")
                ctx = item.get("products_context", "")
                if ctx:
                    with st.expander("Zobacz wygenerowany kontekst produktu"):
                        st.markdown(ctx)
                
                st.markdown("### 📦 Pełne surowe dane (JSON)")
                if j1:
                    with st.expander("JSON 1: Fakty"): st.json(j1)
                if j2:
                    with st.expander("JSON 2: Analiza Rozszerzona"): st.json(j2)
                if j3:
                    with st.expander("JSON 3: Frazy z Faktów"): st.json(j3)
                if j4:
                    with st.expander("JSON 4: Frazy z Analizy"): st.json(j4)
            from utils.helpers import to_excel_multi, get_step2_excel_sheets
            excel_sheets = get_step2_excel_sheets(st.session_state.product_analysis)
        
        excel_data = to_excel_multi(excel_sheets)
        
        st.markdown("---")
        st.download_button(
            label="📥 Pobierz Raport Krok 2 (Excel)",
            data=excel_data,
            file_name="Raport_Krok2_Analiza_Produktow.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
        
        st.markdown("---")
        st.subheader("🔄 Regeneracja pojedynczego produktu")
        st.info("Jeśli z jakiegoś powodu pobieranie lub analiza dla jednego z produktów się nie udała (lub chcesz ją powtórzyć), wybierz produkt z listy i kliknij przycisk.")
        
        product_urls = [item["url"] for item in st.session_state.product_analysis]
        selected_url_to_regen = st.selectbox("Wybierz URL do ponownej analizy:", product_urls)
        
        if st.button("Ponowna analiza wybranego produktu"):
            if not openai_api_key:
                st.error("Wymagany klucz API OpenAI.")
            else:
                # Find the content from the original input if possible, or leave it None to trigger download
                # We can grab it from manual_df if it was manual, else None
                original_content = None
                if input_mode == "Wpisz ręcznie opisy":
                    for idx, row in manual_df.iterrows():
                        if str(row.get("URL/Nazwa", "")).strip() == selected_url_to_regen:
                            original_content = str(row.get("Opis", "")).strip()
                            break
                            
                client = openai.OpenAI(api_key=openai_api_key)
                progress_text = f"Ponowna analiza dla {selected_url_to_regen}..."
                my_bar = st.progress(0, text=progress_text)
                
                res = analyze_single_product(selected_url_to_regen, original_content, client, 0, 1, my_bar)
                if res:
                    # Update the specific item
                    for i, item in enumerate(st.session_state.product_analysis):
                        if item["url"] == selected_url_to_regen:
                            st.session_state.product_analysis[i] = res
                            break
                    st.success("Ponowna analiza zakończona pomyślnie! Odśwież widok, aby zobaczyć zmiany.")
                    st.rerun()
