import streamlit as st
import pandas as pd
import requests
import openai
import json

def render(openai_api_key):
    st.header("Krok 2: Analiza Produktów (Kaskada 4 Promptów)")
    
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
        
        template_all = st.radio("Szablon Ustawień:", ["Domyślny (Ręczne parametry)", "Rekomendowany (Kaskada GPT-5.5 -> GPT-5.4-mini)"], index=1, key="template_all")
        
        if template_all == "Rekomendowany (Kaskada GPT-5.5 -> GPT-5.4-mini)":
            st.info("Zastosowano kaskadę 5 promptów (wg. nowych zaleceń).")
            params_1 = {"model": "gpt-5.5", "temperature": 0.0, "max_tokens": 16000, "reasoning_effort": "medium"}
            params_2 = {"model": "gpt-5.5", "temperature": 0.1, "max_tokens": 16000, "reasoning_effort": "medium"}
            params_3 = {"model": "gpt-5.4-mini", "temperature": 0.1, "max_tokens": 16000, "reasoning_effort": "low"}
            params_4 = {"model": "gpt-5.4-mini", "temperature": 0.1, "max_tokens": 16000, "reasoning_effort": "low"}
            params_5 = {"model": "gpt-5.5", "temperature": 0.0, "max_tokens": 16000, "reasoning_effort": "medium"}
        else:
            st.warning("Ustawiasz parametry ręcznie dla każdego z 5 promptów.")
            t1p, t2p, t3p, t4p, t5p = st.tabs(["Parametry P1", "Parametry P2", "Parametry P3", "Parametry P4", "Parametry P5"])
            with t1p:
                m1 = st.selectbox("Model P1", models_list, index=models_list.index("gpt-5.4-mini"), key="m1")
                t1 = st.slider("Temp P1", 0.0, 2.0, 0.0, 0.1, key="t1")
                r1 = st.selectbox("Reasoning P1", reasoning_efforts, index=1, key="r1")
                params_1 = {"model": m1, "temperature": t1, "max_tokens": 16000, "reasoning_effort": r1}
            with t2p:
                m2 = st.selectbox("Model P2", models_list, index=models_list.index("gpt-5.4-mini"), key="m2")
                t2 = st.slider("Temp P2", 0.0, 2.0, 0.1, 0.1, key="t2")
                r2 = st.selectbox("Reasoning P2", reasoning_efforts, index=1, key="r2")
                params_2 = {"model": m2, "temperature": t2, "max_tokens": 16000, "reasoning_effort": r2}
            with t3p:
                m3 = st.selectbox("Model P3", models_list, index=models_list.index("gpt-5.4-mini"), key="m3")
                t3 = st.slider("Temp P3", 0.0, 2.0, 0.1, 0.1, key="t3")
                r3 = st.selectbox("Reasoning P3", reasoning_efforts, index=0, key="r3")
                params_3 = {"model": m3, "temperature": t3, "max_tokens": 16000, "reasoning_effort": r3}
            with t4p:
                m4 = st.selectbox("Model P4", models_list, index=models_list.index("gpt-5.4-mini"), key="m4")
                t4 = st.slider("Temp P4", 0.0, 2.0, 0.1, 0.1, key="t4")
                r4 = st.selectbox("Reasoning P4", reasoning_efforts, index=0, key="r4")
                params_4 = {"model": m4, "temperature": t4, "max_tokens": 16000, "reasoning_effort": r4}
            with t5p:
                m5 = st.selectbox("Model P5", models_list, index=models_list.index("gpt-5.5"), key="m5")
                t5 = st.slider("Temp P5", 0.0, 2.0, 0.0, 0.1, key="t5")
                r5 = st.selectbox("Reasoning P5", reasoning_efforts, index=1, key="r5")
                params_5 = {"model": m5, "temperature": t5, "max_tokens": 16000, "reasoning_effort": r5}

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

Zwróć wyłącznie JSON w strukturze:
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
        sys_2_def = """Jesteś analitykiem medyczno-kosmetycznym, strategiem SEO, product managerem i strategiem contentowym.

Twoim zadaniem jest wykonanie rozszerzonej analizy produktu na podstawie uporządkowanych faktów z poprzedniego kroku.

Nie analizujesz już surowej strony. Analizujesz skonsolidowane fakty o produkcie.

Cel:
Masz zbudować pełną mapę zastosowań produktu, przyczyn problemów, skutków, grup odbiorców, sezonowości, kontekstów lifestyle’owych, kontekstów medyczno-kosmetycznych oraz szans contentowych.

Zasady:
1. Zwróć wyłącznie poprawny JSON.
2. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
3. Każde zastosowanie z "kanoniczna_lista_zastosowan_do_dalszej_analizy" musi zostać przeanalizowane osobno.
4. Nie pomijaj żadnego wskazania ani zastosowania z poprzedniego kroku.
5. Oddzielaj zastosowania podane wprost od wniosków i hipotez contentowych.
6. Nie sugeruj leczenia problemów, których produkt nie leczy według danych źródłowych.
7. Jeżeli produkt łagodzi objawy albo wspiera regenerację, nie zmieniaj tego w claim "leczy chorobę".
8. Jeżeli analizujesz chorobę, leczenie, dzieci, niemowlęta, ciążę, rany, infekcje, alergie, łuszczycę, wyprysk lub inne stany medyczne, ustaw "wymaga_weryfikacji": true.
9. Jeżeli wniosek wynika z ogólnej logiki, ale nie z treści strony, oznacz go jako "wniosek".
10. Jeżeli temat jest pomysłem contentowym wykraczającym poza treść, oznacz go jako "hipoteza_contentowa".
11. Pisz konkretnie, praktycznie i pod kątem późniejszego SEO."""
        
        usr_2_def = """Wykonaj rozszerzoną analizę produktu na podstawie skonsolidowanych faktów z poprzedniego kroku.

Dane wejściowe:
{product_facts_json}

Cel analizy:
Chcę wiedzieć, do jakich problemów, sytuacji, grup odbiorców i tematów contentowych można bezpiecznie dopasować produkt.

Nie chcę tylko listy wskazań. Chcę pełen związek przyczynowo-skutkowy:
problem → przyczyna → objaw/skutek → sytuacja życiowa → grupa odbiorców → rola produktu → bezpieczny temat contentowy.

Zwróć uwagę na:
* każde wskazanie z produktu,
* przyczyny każdego problemu,
* skutki i objawy,
* sezonowość,
* sport i aktywność,
* pracę fizyczną,
* podróże,
* pielęgnację codzienną,
* dzieci, dorosłych, seniorów i inne grupy,
* leczenie lub terapie, które mogą powodować problemy wtórne,
* konteksty, gdzie produkt może być wsparciem, ale nie rozwiązaniem problemu pierwotnego,
* ryzykowne claimy,
* bezpieczne kierunki komunikacji,
* tematy artykułów,
* zdjęcia, grafiki i sekcje na stronie.

Zwróć wyłącznie JSON w strukturze:
{
"profil_strategiczny_produktu": {
"krotki_opis": "",
"glowna_rola_produktu": "",
"najwazniejsze_obszary_zastosowan": [],
"czy_produkt_ma_wiele_zastosowan": true,
"najwazniejsze_ograniczenie_komunikacyjne": "",
"najwieksza_szansa_contentowa": ""
},
"analiza_zastosowan": [
{
"zastosowanie": "",
"podstawa_zrodlowa": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"typ": "choroba | objaw | stan_skory | problem_kosmetyczny | zastosowanie | mechanizm | claim | inne",
"problem_uzytkownika": "",
"czy_produkt_odpowiada_bezposrednio": true,
"czy_produkt_jest_wsparciem": true,
"rola_produktu": "",
"mechanizm_powiazany_z_produktem": "",
"przyczyny": [
{
"przyczyna": "",
"mechanizm_przyczynowo_skutkowy": "",
"przyklad_sytuacji": "",
"status": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"poziom_pewnosci": "wysoki | sredni | niski"
}
],
"objawy_i_skutki": [
{
"objaw_lub_skutek": "",
"dlaczego_wystepuje": "",
"jak_laczy_sie_z_produktem": "",
"czy_mozna_komunikowac_wprost": true,
"ryzyko_claimu": "niskie | srednie | wysokie"
}
],
"grupy_odbiorcow": [
{
"grupa": "",
"dlaczego_dotyczy_tej_grupy": "",
"typowe_sytuacje": [],
"potrzeby_i_obawy": [],
"bezpieczny_komunikat": "",
"czego_nie_sugerowac": "",
"status": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"wymaga_weryfikacji": true
}
],
"konteksty_sezonowe": [
{
"kontekst": "",
"pora_roku_lub_warunki": "",
"problem": "",
"jak_polaczyc_z_produktem": "",
"pomysl_na_content": "",
"status": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"wymaga_weryfikacji": true
}
],
"konteksty_lifestyle": [
{
"kontekst": "",
"sytuacja_lub_aktywnosc": "",
"problem": "",
"jak_polaczyc_z_produktem": "",
"pomysl_na_content": "",
"status": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"wymaga_weryfikacji": true
}
],
"konteksty_medyczno_kosmetyczne": [
{
"problem_pierwotny": "",
"problem_wtorny": "",
"zwiazek_przyczynowo_skutkowy": "",
"rola_produktu": "",
"bezpieczne_zawężenie_tematu": "",
"czego_nie_sugerowac": "",
"status": "wprost_z_tresci | wniosek | hipoteza_contentowa",
"wymaga_weryfikacji": true
}
],
"claimy_bezpieczne": [],
"claimy_ryzykowne_lub_do_unikania": [],
"tematy_contentowe": [
{
"temat": "",
"proponowany_tytul": "",
"proponowany_h1": "",
"intencja": "informacyjna | poradnikowa | problemowa | sezonowa | produktowa | porownawcza",
"sekcje_artykulu": [],
"jak_naturalnie_polaczyc_z_produktem": "",
"pomysl_na_zdjecie_lub_grafike": "",
"priorytet": "wysoki | sredni | niski",
"uzasadnienie": ""
}
],
"poziom_pewnosci": "wysoki | sredni | niski",
"wymaga_weryfikacji": true
}
],
"mapa_grup_odbiorcow": [
{
"grupa": "",
"problemy": [],
"sytuacje_wyzwalajace_problem": [],
"potrzeby": [],
"obawy": [],
"najlepszy_kierunek_contentu": "",
"powiazane_zastosowania_produktu": [],
"priorytet": "wysoki | sredni | niski"
}
],
"nietypowe_insighty": [
{
"insight": "",
"dlaczego_nie_jest_oczywisty": "",
"zwiazek_przyczynowo_skutkowy": "",
"jak_wykorzystac_w_seo": "",
"przykladowy_temat": "",
"powiazane_zastosowanie": "",
"poziom_pewnosci": "wysoki | sredni | niski",
"wymaga_weryfikacji": true
}
],
"luki_i_szanse_na_stronie": [
{
"luka_lub_szansa": "",
"powiazane_zastosowanie": "",
"dlaczego_to_wazne": "",
"co_dodac": "",
"typ_materialu": "sekcja_produktowa | artykul | FAQ | grafika | zdjecie | tabela | linkowanie_wewnetrzne | ostrzezenie | inne",
"priorytet": "wysoki | sredni | niski"
}
],
"bezpieczne_ramowanie_komunikacji": {
"mozna_komunikowac": [],
"komunikowac_ostroznie": [],
"nie_komunikowac_bez_weryfikacji": [],
"wymaga_sprawdzenia_z_regulatory_lub_ekspertem": []
},
"podsumowanie": {
"najwazniejszy_wniosek": "",
"najlepsze_grupy_odbiorcow": [],
"najlepsze_konteksty_contentowe": [],
"najwieksze_ryzyko": "",
"co_sprawdzic_przed_publikacja": []
}
}"""

        # PROMPT 3
        sys_3_def = """Jesteś ekspertem SEO specjalizującym się w researchu słów kluczowych dla produktów zdrowotnych, medycznych, kosmetycznych, dermokosmetycznych, OTC i leków bez recepty.

Twoim zadaniem jest wygenerowanie krótkich seed keywords do dalszej analizy w Ahrefs Matching Terms.

Seed keyword to krótka fraza bazowa, która po wpisaniu w Ahrefs może odkryć całą rodzinę powiązanych zapytań.

Nie generujesz long-taili, tytułów artykułów ani fraz poradnikowych. Nie generujesz fraz typu „po bieganiu”, „zimą”, „dla dzieci”, „jak stosować”, jeśli nie są samodzielnym głównym tematem. Ahrefs odkryje takie rozwinięcia później.

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
                url = item["url"]
                content = item["content"]
                
                try:
                    if content is None:
                        headers = {"Accept": "application/json"}
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
                            continue
                        
                    if content:
                        content_clipped = content[:8000]
                        
                        # --- PROMPT 1 ---
                        prompt_1 = step2_user_1.replace("{url}", url).replace("{content}", content_clipped)
                        call_1_kwargs = {"model": params_1["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_1}, {"role": "user", "content": prompt_1}]}
                        if "temperature" in params_1: call_1_kwargs["temperature"] = params_1["temperature"]
                        if "max_tokens" in params_1: call_1_kwargs["max_tokens"] = params_1["max_tokens"]
                        if "reasoning_effort" in params_1: call_1_kwargs["reasoning_effort"] = params_1["reasoning_effort"]
                        r1 = client.chat.completions.create(**call_1_kwargs).choices[0].message.content
                        
                        # --- PROMPT 2 ---
                        prompt_2 = step2_user_2.replace("{product_facts_json}", r1)
                        call_2_kwargs = {"model": params_2["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_2}, {"role": "user", "content": prompt_2}]}
                        if "temperature" in params_2: call_2_kwargs["temperature"] = params_2["temperature"]
                        if "max_tokens" in params_2: call_2_kwargs["max_tokens"] = params_2["max_tokens"]
                        if "reasoning_effort" in params_2: call_2_kwargs["reasoning_effort"] = params_2["reasoning_effort"]
                        r2 = client.chat.completions.create(**call_2_kwargs).choices[0].message.content
                        
                        # --- PROMPT 3 ---
                        prompt_3 = step2_user_3.replace("{product_facts_json}", r1).replace("{max_keywords}", "30")
                        call_3_kwargs = {"model": params_3["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_3}, {"role": "user", "content": prompt_3}]}
                        if "temperature" in params_3: call_3_kwargs["temperature"] = params_3["temperature"]
                        if "max_tokens" in params_3: call_3_kwargs["max_tokens"] = params_3["max_tokens"]
                        if "reasoning_effort" in params_3: call_3_kwargs["reasoning_effort"] = params_3["reasoning_effort"]
                        r3 = client.chat.completions.create(**call_3_kwargs).choices[0].message.content
                        
                        # --- PROMPT 4 ---
                        prompt_4 = step2_user_4.replace("{product_facts_json}", r1).replace("{expanded_product_analysis_json}", r2).replace("{max_keywords}", "50")
                        call_4_kwargs = {"model": params_4["model"], "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": step2_sys_4}, {"role": "user", "content": prompt_4}]}
                        if "temperature" in params_4: call_4_kwargs["temperature"] = params_4["temperature"]
                        if "max_tokens" in params_4: call_4_kwargs["max_tokens"] = params_4["max_tokens"]
                        if "reasoning_effort" in params_4: call_4_kwargs["reasoning_effort"] = params_4["reasoning_effort"]
                        r4 = client.chat.completions.create(**call_4_kwargs).choices[0].message.content
                        
                        # --- PROMPT 5 ---
                        prompt_5 = step2_user_5.replace("{product_facts_json}", r1).replace("{expanded_product_analysis_json}", r2)
                        call_5_kwargs = {"model": params_5["model"], "messages": [{"role": "system", "content": step2_sys_5}, {"role": "user", "content": prompt_5}]}
                        if "temperature" in params_5: call_5_kwargs["temperature"] = params_5["temperature"]
                        if "max_tokens" in params_5: call_5_kwargs["max_tokens"] = params_5["max_tokens"]
                        if "reasoning_effort" in params_5: call_5_kwargs["reasoning_effort"] = params_5["reasoning_effort"]
                        r5 = client.chat.completions.create(**call_5_kwargs).choices[0].message.content
                        
                        try:
                            d1 = json.loads(r1)
                            d2 = json.loads(r2)
                            d3 = json.loads(r3)
                            d4 = json.loads(r4)
                            
                            phrases_3 = [str(x).strip().lower() for x in d3.get("seed_keywords", [])]
                            phrases_4 = [str(x).strip().lower() for x in d4.get("seed_keywords", [])]
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
                        except Exception as e:
                            analysis_text = f"Błąd parsowania JSON w kaskadzie: {e}"
                            st.warning(f"Błąd parsowania JSON dla {url}")
                            combined_phrases = []
                            d1, d2, d3, d4 = {}, {}, {}, {}
                            
                        product_analysis.append({
                            "url": url,
                            "analysis": analysis_text,
                            "seed_keywords": combined_phrases,
                            "json1": d1 if 'd1' in locals() else {},
                            "json2": d2 if 'd2' in locals() else {},
                            "json3": d3 if 'd3' in locals() else {},
                            "json4": d4 if 'd4' in locals() else {},
                            "products_context": r5 if 'r5' in locals() else ""
                        })
                    else:
                        st.warning(f"Brak zawartości do analizy dla {url}")
                except Exception as e:
                    st.error(f"Błąd analizy {url}: {e}")
                    
                progress_value = min(1.0, (idx + 1) / len(items_to_analyze))
                my_bar.progress(progress_value, text=f"Przeanalizowano {idx+1} z {len(items_to_analyze)} produktów.")
                
            st.session_state.product_analysis = product_analysis
            st.success("Kaskada zakończona!")
            
    if "product_analysis" in st.session_state:
        st.subheader("Wyniki Analizy AI")
        
        from utils.helpers import to_excel_multi
        
        products_data = []
        keywords_data = []
        zastosowania_data = []
        
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
                strat = j2.get("profil_strategiczny_produktu", {})
                if strat:
                    st.info(f"**Główna Rola:** {strat.get('glowna_rola_produktu', '')}\n\n**Szansa Contentowa:** {strat.get('najwieksza_szansa_contentowa', '')}")
                
                podsumowanie = j2.get("podsumowanie", {})
                if podsumowanie:
                    if podsumowanie.get("najwazniejszy_wniosek"):
                        st.success(f"**Najważniejszy wniosek:** {podsumowanie.get('najwazniejszy_wniosek')}")
                    if podsumowanie.get("najwieksze_ryzyko"):
                        st.warning(f"**Największe ryzyko:** {podsumowanie.get('najwieksze_ryzyko')}")
                
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
            
            # Zebranie danych do Excela
            products_data.append({
                "URL": url,
                "Nazwa": p1.get("nazwa", ""),
                "Status": p1.get("status_produktu", ""),
                "Kategoria": p1.get("kategoria", ""),
                "Postać": p1.get("postac", ""),
                "Dostępny bez recepty": p1.get("czy_dostepny_bez_recepty", ""),
                "Najważniejszy Wniosek": podsumowanie.get("najwazniejszy_wniosek", "") if podsumowanie else "",
                "Szansa Contentowa": strat.get("najwieksza_szansa_contentowa", "") if strat else "",
                "Największe Ryzyko": podsumowanie.get("najwieksze_ryzyko", "") if podsumowanie else ""
            })
            
            for k in j3.get("keyword_details", []):
                keywords_data.append({
                    "URL": url,
                    "Fraza": k.get("fraza", ""),
                    "Źródło": "Fakty",
                    "Typ": k.get("typ", ""),
                    "Priorytet": k.get("priorytet", ""),
                    "Uwaga / Podstawa": k.get("podstawa_w_faktach", "")
                })
            for k in j4.get("keyword_details", []):
                keywords_data.append({
                    "URL": url,
                    "Fraza": k.get("fraza", ""),
                    "Źródło": "Analiza Rozszerzona",
                    "Typ": k.get("typ", ""),
                    "Priorytet": k.get("priorytet", ""),
                    "Uwaga / Podstawa": k.get("uwaga_komunikacyjna", "")
                })
                
            for zast in j2.get("analiza_zastosowan", []):
                zastosowania_data.append({
                    "URL": url,
                    "Zastosowanie": zast.get("zastosowanie", ""),
                    "Typ": zast.get("typ", ""),
                    "Rola Produktu": zast.get("rola_produktu", ""),
                    "Poziom Pewności": zast.get("poziom_pewnosci", ""),
                    "Wymaga Weryfikacji": zast.get("wymaga_weryfikacji", "")
                })
        
        excel_sheets = {
            "Produkty": pd.DataFrame(products_data),
            "Słowa Kluczowe": pd.DataFrame(keywords_data),
            "Zastosowania": pd.DataFrame(zastosowania_data)
        }
        
        excel_data = to_excel_multi(excel_sheets)
        
        st.markdown("---")
        st.download_button(
            label="📥 Pobierz Raport Krok 2 (Excel)",
            data=excel_data,
            file_name="Raport_Krok2_Analiza_Produktow.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
