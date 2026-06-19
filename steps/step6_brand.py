import streamlit as st
import pandas as pd
import openai
import json
import os

def render(openai_api_key):
    st.header("Krok 5: Analiza Brandu (2 Etapy)")
    
    # 1. Sprawdzanie czy istnieje plik awaryjny JSON
    if os.path.exists("temp_brand_results_backup.json"):
        st.warning("⚠️ Wykryto niezakończoną analizę Etapu 1 z poprzedniej sesji!")
        try:
            with open("temp_brand_results_backup.json", "r", encoding="utf-8") as f:
                json_backup = f.read()
                data_len = len(json.loads(json_backup))
            st.download_button(
                label=f"📥 Pobierz uratowane wyniki JSON ({data_len} rekordów)",
                data=json_backup,
                file_name="uratowane_wyniki_krok6_etap1.json",
                mime="application/json",
                type="primary"
            )
        except Exception as e:
            st.error(f"Nie udało się wczytać pliku backupu: {e}")
            
    st.markdown("---")
    
    # 2. Wybór trybu pracy
    mode = st.radio(
        "Wybierz tryb pracy w Kroku 6:",
        ["Analiza AI nowej listy", "Wgraj gotowy plik JSON z wynikami (ominięcie Etapu 1)"]
    )
    
    if mode == "Wgraj gotowy plik JSON z wynikami (ominięcie Etapu 1)":
        st.info("Wgraj plik JSON zawierający przetworzone wyniki Etapu 1 (z tablicą obiektów). System natychmiast załaduje te dane i pozwoli przejść od razu do szybkiego Etapu 2 (Klastrowanie).")
        ready_file = st.file_uploader("Wgraj gotowy plik JSON", type=['json'], key="ready_file_brand")
        if ready_file:
            try:
                data = json.load(ready_file)
                st.success(f"Pomyślnie wczytano plik z {len(data)} przeanalizowanymi frazami!")
                if st.button("Zapisz te wyniki i przejdź do Etapu 2", type="primary"):
                    st.session_state.brand_analysis_results = data
                    st.success("Zapisano! Przejdź niżej i kliknij 'Rozpocznij Analizę Brandu', aby wykonać tylko Etap 2.")
            except Exception as e:
                st.error(f"Błąd podczas wczytywania gotowego pliku: {e}")
        
    st.markdown("---")
    st.markdown("Wgraj pliki zawierające zapytania brandowe (np. z Ahrefs i Senuto).")
    
    col1, col2 = st.columns(2)
    with col1:
        brand_ahrefs = st.file_uploader("Brand Keywords Ahrefs (CSV)", type=['csv'])
    with col2:
        brand_senuto = st.file_uploader("Brand Keywords Senuto (XLSX)", type=['xlsx', 'xls'])
        
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-5.5", "gpt-5.4-mini", "o1-mini", "o3-mini"]
        
        st.markdown("### 📝 Prompt 1: Analiza Pojedynczej Frazy")
        template_5a = st.radio("Szablon Ustawień (Fraza):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: medium, temp: 1.0)"], key="template_5a")
        if template_5a == "Domyślny (Ręczne parametry)":
            step5_model_a = st.selectbox("Wybierz model:", models, index=models.index("gpt-5.4-mini") if "gpt-5.4-mini" in models else 0, key="step5_model_a")
            ca1, ca2 = st.columns(2)
            with ca1:
                step5_temp_a = st.slider("Temperatura", 0.0, 2.0, 1.0 if step5_model_a == "gpt-5.4-mini" else 0.7, 0.1, key="step5_temp_a")
            with ca2:
                step5_tokens_a = st.number_input("Max Tokens", 100, 16000, 4000, key="step5_tokens_a")
            params_5a = {"model": step5_model_a, "temperature": 1.0 if step5_model_a == "gpt-5.4-mini" else step5_temp_a, "max_tokens": step5_tokens_a}
        else:
            st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=1.0, reasoning_effort=medium.")
            params_5a = {"model": "gpt-5.4-mini", "temperature": 1.0, "reasoning_effort": "medium"}
            
        sys_5a_def = """Jesteś ekspertem SEO, content strategistą i analitykiem fraz brandowych dla produktów medycznych, kosmetycznych, dermokosmetycznych i OTC.

Analizujesz pojedyncze słowo kluczowe zawierające nazwę marki lub produktu. Twoim zadaniem jest ocenić, jaka jest intencja użytkownika, czego użytkownik prawdopodobnie szuka, czy strona klienta powinna odpowiadać na to zapytanie oraz jakiego typu treść należy przygotować.

Nie oceniasz wyłącznie potencjału SEO. Oceniasz również:
* dopasowanie frazy do produktu,
* potencjał sprzedażowy,
* ryzyko komunikacyjne,
* ryzyko claimów medycznych,
* potrzebę stworzenia nowej podstrony,
* potrzebę rozbudowy istniejącej strony,
* możliwość obsłużenia frazy przez FAQ,
* zasadność stworzenia artykułu, landing page’a, porównania lub sekcji zakupowej.

Zasady analizy:
* niskie volume + fraza bezpieczeństwa lub zakupowa może nadal mieć sens,
* niskie volume + luźne dopasowanie = niski priorytet albo odrzucenie.
12. Frazy brandowe często są blisko decyzji zakupowej, dlatego zwracaj uwagę na zapytania typu: cena, skład, opinie, ulotka, jak stosować, od jakiego wieku, na co, czy można, zamiennik, porównanie z konkurencją.
13. Odrzucaj albo oznaczaj jako ryzykowne frazy, które mogą prowadzić do niezgodnych claimów.
14. Zachowaj rygor: lepiej zarekomendować krótkie FAQ niż niepotrzebną osobną podstronę."""
        step5_sys_a = st.text_area("System Prompt (Analiza Frazy)", value=sys_5a_def, height=250, key="step5_sys_a")
        
        user_5a_def = """Przeanalizuj paczkę fraz brandowych na podstawie danych SEO oraz kontekstu produktów klienta.

Dane paczki (lista obiektów):
{batch_data}

Kontekst produktów klienta:
{products_context}

Cel analizy:
Dla KAŻDEJ frazy z paczki sprawdź, czy klient powinien na nią odpowiedzieć poprzez:
* stworzenie nowej podstrony,
* rozbudowę istniejącej strony produktu,
* dodanie sekcji FAQ,
* stworzenie artykułu poradnikowego,
* stworzenie landing page’a,
* stworzenie porównania,
* dodanie sekcji „gdzie kupić”,
* dodanie informacji o składzie, bezpieczeństwie, stosowaniu lub przeciwwskazaniach,
* albo nietworzenie żadnej treści.

Zwróć wyłącznie poprawny JSON o następującej strukturze:
{
  "results": [
    {
      "id": "identyfikator podany w batch_data",
      "keyword": "analizowana fraza",
      "position": "pozycja podana w batch_data",
      "volume": "wolumen podany w batch_data",
      "typ_frazy": "produktowa | problemowa | zastosowanie | pytanie_o_stosowanie | bezpieczenstwo | sklad | przeciwwskazania | porownawcza | zakupowa | opinie | wariant_produktu | wiek_lub_grupa_docelowa | niejasna",
      "intencja": "informacyjna | poradnikowa | produktowa | transakcyjna | porownawcza | nawigacyjna | bezpieczeństwo | niejasna",
      "etap_sciezki_uzytkownika": "poznanie | rozważanie | decyzja | po_zakupie | niejasne",
      "produkt": "najlepiej dopasowany produkt lub adres URL produktu z kontekstu klienta albo pusty string",
      "segment": "problem, potrzeba lub kategoria",
      "problem_uzytkownika": "krótki opis tego, czego użytkownik prawdopodobnie szuka",
      "dopasowanie_do_produktu": "bezposrednie | posrednie | luzne | brak",
      "czy_obecna_strona_powinna_odpowiadac": true,
      "czy_potrzebna_nowa_podstrona": true,
      "rekomendowany_typ_tresci": "DODAJ_FAQ | ROZBUDUJ_STRONE_PRODUKTU | STWORZ_ARTYKUL | STWORZ_LANDING | STWORZ_POROWNANIE | DODAJ_SEKCJE_GDZIE_KUPIC | DODAJ_SEKCJE_SKLAD | DODAJ_SEKCJE_BEZPIECZENSTWO | NIE_TWORZ_TRESCI | WYMAGA_WERYFIKACJI_MEDYCZNEJ",
      "proponowany_temat_lub_sekcja": "proponowany temat artykułu, nazwa sekcji, FAQ albo landing page",
      "bezpieczny_kierunek_odpowiedzi": "jak bezpiecznie odpowiedzieć na zapytanie użytkownika",
      "czego_nie_sugerowac": "jakich claimów, obietnic lub zastosowań nie należy sugerować",
      "czy_fraza_moze_byc_czescia_wiekszego_klastra": true,
      "proponowany_klaster": "nazwa klastra",
      "potencjal_sprzedazowy": "wysoki | sredni | niski",
      "ryzyko_claimow": "niskie | srednie | wysokie",
      "wymaga_weryfikacji": true,
      "priorytet": "wysoki | sredni | niski",
      "uzasadnienie_priorytetu": "krótkie wyjaśnienie priorytetu",
      "uzasadnienie": "jedno krótkie zdanie wyjaśniające rekomendację"
    }
  ]
}"""
        step5_user_a = st.text_area("User Prompt (Analiza Frazy)", value=user_5a_def, height=250, key="step5_user_a")

        st.markdown("---")
        st.markdown("### 📦 Prompt 2: Grupowanie Fraz (Klastry)")
        template_5b = st.radio("Szablon Ustawień (Grupowanie):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: medium, temp: 1.0)"], key="template_5b")
        if template_5b == "Domyślny (Ręczne parametry)":
            step5_model_b = st.selectbox("Wybierz model:", models, index=models.index("gpt-5.4-mini") if "gpt-5.4-mini" in models else 0, key="step5_model_b")
            cb1, cb2 = st.columns(2)
            with cb1:
                step5_temp_b = st.slider("Temperatura", 0.0, 2.0, 1.0 if step5_model_b == "gpt-5.4-mini" else 0.7, 0.1, key="step5_temp_b")
            with cb2:
                step5_tokens_b = st.number_input("Max Tokens", 100, 16000, 16000, key="step5_tokens_b")
            params_5b = {"model": step5_model_b, "temperature": 1.0 if step5_model_b == "gpt-5.4-mini" else step5_temp_b, "max_tokens": step5_tokens_b}
        else:
            st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=1.0, max_tokens=16000, reasoning_effort=medium.")
            params_5b = {"model": "gpt-5.4-mini", "temperature": 1.0, "max_tokens": 16000, "reasoning_effort": "medium"}
            
        sys_5b_def = """Jesteś ekspertem SEO, content strategistą i architektem informacji dla stron produktowych, e-commerce oraz marek medycznych, kosmetycznych, dermokosmetycznych i OTC.

Twoim zadaniem jest pogrupowanie przeanalizowanych fraz brandowych w logiczne klastry contentowe i przygotowanie rekomendacji, jakie treści klient powinien stworzyć albo rozbudować.

Nie tworzysz osobnej podstrony dla każdej frazy. Grupujesz frazy tak, aby:
* unikać kanibalizacji,
* wzmacniać istniejące strony produktowe,
* tworzyć tylko te nowe podstrony, które mają realny sens,
* obsłużyć podobne intencje jedną sekcją, FAQ, artykułem albo landing page’em,
* oddzielić frazy sprzedażowe od informacyjnych,
* oddzielić frazy bezpieczne od fraz wymagających weryfikacji medycznej, prawnej lub regulatory.

Zasady grupowania:
1. Zwracaj wyłącznie poprawny obiekt JSON.
2. Odpowiadaj WYŁĄCZNIE surowym tekstem JSON (bez formatowania Markdown i bloków kodu ```json). Wewnątrz wartości tekstowych używaj wyłącznie pojedynczych apostrofów ('), unikaj podwójnych cudzysłowów ("), aby nie zepsuć parsowania JSON.
3. Grupuj frazy według wspólnej intencji, problemu, produktu, zastosowania lub etapu ścieżki użytkownika.
4. Nie grupuj razem fraz, które mają różną intencję, np. „cena” i „jak stosować”, chyba że mają trafić do jednej rozbudowanej strony produktu jako osobne sekcje.
5. Nie rekomenduj osobnych podstron dla bliskich wariantów tej samej frazy, np. „linomag sucha skóra”, „linomag na suchą skórę”, „linomag przesuszona skóra”.
6. Osobną podstronę rekomenduj tylko wtedy, gdy klaster ma wyraźną intencję, odpowiedni potencjał SEO, bezpieczne dopasowanie do produktu i nie będzie kanibalizował strony produktu.
7. Jeżeli klaster dotyczy pytań prostych, bezpieczeństwa, składu, przeciwwskazań, wieku, stosowania lub krótkich odpowiedzi, preferuj FAQ albo sekcję na stronie produktu.
8. Jeżeli klaster dotyczy problemu poradnikowego, który można rozwinąć edukacyjnie i naturalnie połączyć z produktem, rekomenduj artykuł poradnikowy.
9. Jeżeli klaster dotyczy ceny, aptek, dostępności lub zakupu, rekomenduj sekcję „gdzie kupić”, landing zakupowy albo rozbudowę strony produktu.
10. Jeżeli klaster dotyczy porównań z konkurencją, rekomenduj porównanie tylko przy niskim lub średnim ryzyku claimów. Przy wysokim ryzyku oznacz konieczność weryfikacji.
11. Jeżeli klaster dotyczy chorób, leczenia, ciąży, niemowląt, ran, infekcji, działań niepożądanych, przeciwwskazań albo stosowania poza oczywistym zakresem produktu, oznacz konieczność weryfikacji.
12. Priorytetyzuj klastry według:
* sumy volume fraz w klastrze,
* aktualnych pozycji,
* dopasowania do produktu,
* potencjału sprzedażowego,
* ryzyka claimów,
* łatwości wdrożenia.
13. Nie twórz klastra tylko dlatego, że istnieje pojedyncza fraza. Jeśli fraza jest odosobniona, niskiej jakości lub ryzykowna, oznacz ją jako „do_monitorowania” albo „odrzucone”.
14. Zanim zaproponujesz DODAJ_FAQ lub ROZBUDUJ_STRONE_PRODUKTU, przeszukaj "Aktualną treść na stronie" podaną dla danego produktu. Jeśli rekomendowana sekcja lub informacja już w nim jest, zwróć rekomendację NIE_TWORZ_TRESCI lub zalecaj jedynie drobną optymalizację.
15. Zanim zaproponujesz STWORZ_ARTYKUL, sprawdź "Listę własnych stron klienta". Jeśli znajdziesz adres (np. wpis na blogu) odpowiadający intencji klastra, nie twórz nowego artykułu, tylko ustaw rekomendację na ROZBUDUJ_ISTNIEJACY_ARTYKUL i wskaż znaleziony adres w polu `docelowa_istniejaca_strona`.
16. Wskazuj rekomendacje wybierając z: nowa podstrona, rozbudowa istniejącej strony produktu, rozbudowa istniejącego artykułu, sekcja FAQ, artykuł poradnikowy, landing page, sekcja zakupowa, lub nie twórz treści."""
        step5_sys_b = st.text_area("System Prompt (Grupowanie)", value=sys_5b_def, height=250, key="step5_sys_b")
        
        user_5b_def = """Pogrupuj przeanalizowane frazy brandowe w klastry contentowe i przygotuj rekomendacje dla klienta.

Dane wejściowe:
{brand_keyword_analysis_json}

Kontekst produktów i stron klienta:
{full_context}

Cel:
Chcę wiedzieć, jakie działania contentowe klient powinien wykonać na podstawie brandowych fraz SEO.

Nie chcę osobnej rekomendacji dla każdej frazy. Chcę pogrupowania fraz w sensowne klastry i decyzji:
* czy rozbudować istniejącą stronę produktu,
* czy dodać FAQ,
* czy stworzyć nowy artykuł,
* czy stworzyć landing,
* czy stworzyć porównanie,
* czy dodać sekcję „gdzie kupić”,
* czy nie tworzyć treści,
* czy temat wymaga weryfikacji medycznej, prawnej lub regulatory.

Zwróć wyłącznie poprawny JSON w strukturze:
{
"podsumowanie": {
"liczba_przeanalizowanych_fraz": 0,
"liczba_klastrow": 0,
"liczba_rekomendowanych_nowych_podstron": 0,
"liczba_rekomendowanych_rozbudow": 0,
"liczba_tematow_wymagajacych_weryfikacji": 0,
"najwieksza_szansa": "",
"najwieksze_ryzyko": ""
},
"klastry": [
{
"nazwa_klastra": "",
"typ_klastra": "produktowy | problemowy | zastosowanie | bezpieczenstwo | sklad | zakupowy | porownawczy | opinie | wariant_produktu | mieszany | ryzykowny",
"intencja_glowna": "informacyjna | poradnikowa | produktowa | transakcyjna | porownawcza | nawigacyjna | bezpieczeństwo | mieszana | niejasna",
"produkt": "najlepiej dopasowany produkt lub adres URL produktu z kontekstu klienta albo pusty string",
"segment": "problem, potrzeba lub kategoria",
"frazy_w_klastrze": [{"keyword": "", "position": 0, "volume": 0, "rola_w_klastrze": "glowna | wspierajaca | faq | long_tail | ryzykowna"}],
"suma_volume": 0,
"najlepsza_pozycja": 0,
"najgorsza_pozycja": 0,
"srednia_pozycja": 0,
"dominujace_dopasowanie_do_produktu": "bezposrednie | posrednie | luzne | brak",
"potencjal_sprzedazowy": "wysoki | sredni | niski",
"ryzyko_claimow": "niskie | srednie | wysokie",
"wymaga_weryfikacji": true,
"rekomendacja": "ROZBUDUJ_STRONE_PRODUKTU | ROZBUDUJ_ISTNIEJACY_ARTYKUL | DODAJ_FAQ | STWORZ_ARTYKUL | STWORZ_LANDING | STWORZ_POROWNANIE | DODAJ_SEKCJE_GDZIE_KUPIC | DODAJ_SEKCJE_SKLAD | DODAJ_SEKCJE_BEZPIECZENSTWO | NIE_TWORZ_TRESCI | DO_MONITOROWANIA | WYMAGA_WERYFIKACJI_MEDYCZNEJ",
"czy_nowa_podstrona": true,
"czy_rozbudowa_istniejacej_strony": true,
"docelowa_istniejaca_strona": "adres URL produktu lub strony, którą należy rozbudować, albo pusty string",
"proponowany_url_lub_slug": "",
"proponowany_title": "",
"proponowany_h1": "",
"proponowane_sekcje": [{"naglowek": "", "cel_sekcji": "", "frazy_do_obsluzenia": []}],
"proponowane_faq": [{"pytanie": "", "bezpieczna_odpowiedz": "", "frazy_do_obsluzenia": [], "wymaga_weryfikacji": true}],
"bezpieczny_kierunek_tresci": "",
"czego_nie_sugerowac": "",
"priorytet": "wysoki | sredni | niski",
"uzasadnienie_priorytetu": "",
"uzasadnienie_rekomendacji": ""
}
],
"frazy_odrzucone_lub_do_monitorowania": [{"keyword": "", "position": 0, "volume": 0, "powod": "brak_dopasowania | zbyt_ryzykowne | zbyt_male_volume | niejasna_intencja | kanibalizacja | obsluzone_przez_inny_klaster", "rekomendacja": "NIE_TWORZ_TRESCI | DO_MONITOROWANIA | WYMAGA_WERYFIKACJI"}],
"priorytetowe_dzialania": [{"kolejnosc": 1, "dzialanie": "", "typ_dzialania": "rozbudowa | faq | artykul | landing | porownanie | sekcja_zakupowa | weryfikacja", "powiazany_klaster": "", "uzasadnienie": ""}],
"ryzyka_i_uwagi": [{"obszar": "", "ryzyko": "", "jak_ograniczyc_ryzyko": ""}]
}"""
        step5_user_b = st.text_area("User Prompt (Grupowanie)", value=user_5b_def, height=250, key="step5_user_b")
            
    if st.button("Rozpocznij Analizę Brandu AI", type="primary"):
        brand_data = []
        
        def extract_data(df):
            k_col = next((c for c in df.columns if 'keyword' in str(c).lower() or 'słowo' in str(c).lower()), df.columns[0])
            p_col = next((c for c in df.columns if 'pos' in str(c).lower() or 'poz' in str(c).lower()), None)
            v_col = next((c for c in df.columns if 'vol' in str(c).lower() or 'wyszuk' in str(c).lower()), None)
            
            extracted = []
            for _, row in df.iterrows():
                kw = str(row[k_col]).strip() if pd.notna(row[k_col]) else ""
                pos = int(row[p_col]) if p_col and pd.notna(row[p_col]) else 0
                vol = int(row[v_col]) if v_col and pd.notna(row[v_col]) else 0
                if kw:
                    extracted.append({"keyword": kw, "position": pos, "volume": vol})
            return extracted
            
        if brand_ahrefs:
            try:
                df_b_ahrefs = pd.read_csv(brand_ahrefs, encoding="utf-16le", sep="\t")
                if len(df_b_ahrefs.columns) <= 1:
                    brand_ahrefs.seek(0)
                    df_b_ahrefs = pd.read_csv(brand_ahrefs)
                brand_data.extend(extract_data(df_b_ahrefs))
            except Exception as e:
                st.error(f"Błąd parsowania Ahrefs: {e}")
        if brand_senuto:
            try:
                df_b_senuto = pd.read_excel(brand_senuto)
                brand_data.extend(extract_data(df_b_senuto))
            except Exception as e:
                st.error(f"Błąd parsowania Senuto: {e}")

        # Budowanie kontekstu jest potrzebne dla obu etapów
        products_analysis_context = "Lista naszych produktów wraz z analizą:\n"
        if "product_analysis" in st.session_state:
            for item in st.session_state.product_analysis:
                products_analysis_context += f"- Produkt: {item['url']}\n  Analiza eksperta: {item['analysis']}\n\n"
                
        products_context = "Lista naszych produktów wraz z analizą i surową treścią ze strony:\n"
        if "product_analysis" in st.session_state:
            for item in st.session_state.product_analysis:
                products_context += f"- Produkt: {item['url']}\n  Analiza eksperta: {item['analysis']}\n  Aktualna treść na stronie (Surowy Markdown): {item.get('raw_content', 'Brak pobranego tekstu')}\n\n"
        
        user_pages_context = "Lista naszych własnych stron (Blog/Baza wiedzy/inne):\n"
        if "my_pages_df" in st.session_state:
            df_my_pages = st.session_state.my_pages_df
            u_col = next((c for c in df_my_pages.columns if 'url' in str(c).lower() or 'address' in str(c).lower()), df_my_pages.columns[0])
            t_col = next((c for c in df_my_pages.columns if 'title' in str(c).lower() or 'tytuł' in str(c).lower()), df_my_pages.columns[1] if len(df_my_pages.columns)>1 else None)
            
            for idx, row in df_my_pages.iterrows():
                u = str(row[u_col]).strip() if pd.notna(row[u_col]) else ""
                t = str(row[t_col]).strip() if t_col and pd.notna(row[t_col]) else ""
                if u:
                    user_pages_context += f"- URL: {u} | Tytuł: {t}\n"
        else:
            user_pages_context += "Brak wgranych własnych stron (Pominięto Krok 5).\n"
            
        full_context = f"--- PRODUKTY KLIENTA ---\n{products_context}\n\n--- WŁASNE STRONY KLIENTA ---\n{user_pages_context}"
        
        client = openai.OpenAI(api_key=openai_api_key)

        # Etap 1: Analiza pojedynczych fraz (tylko jeśli brak ich w sesji)
        if "brand_analysis_results" not in st.session_state:
            if not brand_data:
                st.warning("Nie znaleziono poprawnych fraz w plikach.")
                return
                
            # Deduplicate
            seen = set()
            unique_brand_data = []
            for item in brand_data:
                if item["keyword"] not in seen:
                    seen.add(item["keyword"])
                    unique_brand_data.append(item)
                    
            st.info(f"Znaleziono {len(unique_brand_data)} unikalnych zapytań brandowych. Rozpoczynam Etap 1: Analiza każdej frazy...")

            analyzed_keywords = []
            my_bar_1 = st.progress(0, text="Analiza fraz w toku...")
            st.markdown("### Podgląd wyników na żywo (Etap 1):")
            table_placeholder = st.empty()
            
            import time
            batch_size = 15
            
            for i in range(0, len(unique_brand_data), batch_size):
                batch = unique_brand_data[i:i+batch_size]
                
                batch_data_list = []
                for idx, item in enumerate(batch):
                    batch_data_list.append({
                        "id": i + idx,
                        "keyword": str(item["keyword"]),
                        "position": str(item["position"]),
                        "volume": str(item["volume"])
                    })
                    
                batch_data_str = json.dumps(batch_data_list, ensure_ascii=False)
                prompt = step5_user_a.replace("{batch_data}", batch_data_str).replace("{products_context}", products_analysis_context)
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        call_a_kwargs = {
                            "model": params_5a["model"],
                            "response_format": { "type": "json_object" },
                            "messages": [
                                {"role": "system", "content": step5_sys_a},
                                {"role": "user", "content": prompt}
                            ]
                        }
                        if "temperature" in params_5a: call_a_kwargs["temperature"] = params_5a["temperature"]
                        if "max_tokens" in params_5a:
                            if any(m in params_5a["model"] for m in ["gpt-5", "o1", "o3"]): call_a_kwargs["max_completion_tokens"] = params_5a["max_tokens"]
                            else: call_a_kwargs["max_tokens"] = params_5a["max_tokens"]
                        if "reasoning_effort" in params_5a: call_a_kwargs["reasoning_effort"] = params_5a["reasoning_effort"]
                            
                        resp_a = client.chat.completions.create(**call_a_kwargs)
                        if resp_a.usage:
                            from utils.helpers import track_usage
                            track_usage(params_5a["model"], resp_a.usage.prompt_tokens, resp_a.usage.completion_tokens)
                                
                        res_a = resp_a.choices[0].message.content.strip()
                        
                        try:
                            from utils.helpers import clean_json
                            json_res = json.loads(clean_json(res_a))
                            results_array = json_res.get("results", [])
                            
                            for res in results_array:
                                if "id" in res:
                                    del res["id"]
                                analyzed_keywords.append(res)
                                
                        except Exception as je:
                            st.warning(f"Błąd parsowania JSON dla paczki {i}-{i+batch_size}: {je}")
                        break # Success, exit retry loop
                        
                    except Exception as e:
                        if "rate" in str(e).lower() or "429" in str(e) or "limit" in str(e).lower():
                            if attempt < max_retries - 1:
                                my_bar_1.progress(min(1.0, i / len(unique_brand_data)), text=f"Analiza: {i}/{len(unique_brand_data)} fraz. (Rate Limit - czekam 10s...)")
                                time.sleep(10)
                            else:
                                st.warning(f"Błąd Rate Limit przy paczce {i}-{i+batch_size} po 3 próbach: {e}")
                        else:
                            st.warning(f"Błąd przy paczce {i}-{i+batch_size}: {e}")
                            break
                    
                progress_value = min(1.0, (i + len(batch)) / len(unique_brand_data))
                my_bar_1.progress(progress_value, text=f"Analiza: {i+len(batch)}/{len(unique_brand_data)} fraz.")
                
                if analyzed_keywords:
                    df_current = pd.DataFrame(analyzed_keywords)
                    table_placeholder.dataframe(df_current)
                    with open("temp_brand_results_backup.json", "w", encoding="utf-8") as f:
                        json.dump(analyzed_keywords, f, ensure_ascii=False, indent=2)
                
            if not analyzed_keywords:
                st.error("Nie powiodła się analiza żadnej frazy.")
                return
                
            st.session_state.brand_analysis_results = analyzed_keywords
            if os.path.exists("temp_brand_results_backup.json"):
                os.remove("temp_brand_results_backup.json")
                
            st.info("Etap 1 zakończony. Rozpoczynam Etap 2: Grupowanie i klastrowanie...")
            analyzed_keywords_to_process = analyzed_keywords
        else:
            st.info("Znaleziono wgrane wyniki Etapu 1. Pomijam powtórną analizę fraz i przechodzę od razu do Etapu 2 (Klastrowanie).")
            analyzed_keywords_to_process = st.session_state.brand_analysis_results
            
        # Etap 2: Grupowanie
        prompt_5b = step5_user_b.replace("{brand_keyword_analysis_json}", json.dumps(analyzed_keywords_to_process, ensure_ascii=False)).replace("{full_context}", full_context)
            
        try:
            call_b_kwargs = {
                "model": params_5b["model"],
                "response_format": { "type": "json_object" },
                "messages": [
                    {"role": "system", "content": step5_sys_b},
                    {"role": "user", "content": prompt_5b}
                ]
            }
            if "temperature" in params_5b: call_b_kwargs["temperature"] = params_5b["temperature"]
            if "max_tokens" in params_5b:
                if any(m in params_5b["model"] for m in ["gpt-5", "o1", "o3"]): call_b_kwargs["max_completion_tokens"] = params_5b["max_tokens"]
                else: call_b_kwargs["max_tokens"] = params_5b["max_tokens"]
            if "reasoning_effort" in params_5b: call_b_kwargs["reasoning_effort"] = params_5b["reasoning_effort"]
                
            resp_b = client.chat.completions.create(**call_b_kwargs)
            if resp_b.usage:
                from utils.helpers import track_usage
                track_usage(params_5b["model"], resp_b.usage.prompt_tokens, resp_b.usage.completion_tokens)
                
            from utils.helpers import clean_json
            final_json = json.loads(clean_json(resp_b.choices[0].message.content))
            
            st.session_state.brand_clusters = final_json
            st.success("Analiza i klastrowanie zakończone pomyślnie!")
            
        except Exception as e:
            st.error(f"Błąd w Etapie 2 (Grupowanie): {e}")

    if "brand_clusters" in st.session_state:
        st.markdown("---")
        st.subheader("Wyniki Analizy Brandu")
        
        final_json = st.session_state.brand_clusters
        
        # Display nicely
        md = []
        podsumowanie = final_json.get("podsumowanie", {})
        md.append("## 🎯 Podsumowanie Analizy Brandu")
        md.append(f"- Przeanalizowane frazy: **{podsumowanie.get('liczba_przeanalizowanych_fraz', 0)}**")
        md.append(f"- Klastry: **{podsumowanie.get('liczba_klastrow', 0)}**")
        md.append(f"- Rekomendowane nowe podstrony: **{podsumowanie.get('liczba_rekomendowanych_nowych_podstron', 0)}**")
        md.append(f"- Rekomendowane rozbudowy: **{podsumowanie.get('liczba_rekomendowanych_rozbudow', 0)}**")
        md.append(f"**Największa szansa:** {podsumowanie.get('najwieksza_szansa', '')}")
        md.append(f"**Największe ryzyko:** {podsumowanie.get('najwieksze_ryzyko', '')}")
        md.append("---")
        
        klastry = final_json.get("klastry", [])
        for i, k in enumerate(klastry):
            md.append(f"### {i+1}. {k.get('nazwa_klastra', 'Bez nazwy')} ({k.get('typ_klastra', '')})")
            md.append(f"**Rekomendacja:** {k.get('rekomendacja', '')} ({k.get('priorytet', 'brak')})")
            if k.get("proponowany_title"):
                md.append(f"- **Proponowany Title:** {k.get('proponowany_title')}")
            if k.get("proponowany_h1"):
                md.append(f"- **Proponowany H1:** {k.get('proponowany_h1')}")
            
            f_list = [f"{f.get('keyword', '')} (Vol: {f.get('volume', 0)}, Poz: {f.get('position', 0)})" for f in k.get("frazy_w_klastrze", [])]
            md.append("- **Frazy:** " + ", ".join(f_list))
            md.append(f"- **Uzasadnienie:** {k.get('uzasadnienie_rekomendacji', '')}")
            md.append("\n")
            
        st.markdown("\n".join(md))
        
        with st.expander("📦 Pełny profil JSON"):
            st.json(final_json)
            
        from utils.helpers import to_excel_multi
        
        sheets = {}
        cluster_data = []
        for k in klastry:
            frazy = k.get("frazy_w_klastrze", [])
            frazy_str = ", ".join([str(f.get("keyword", "")) for f in frazy])
            vol_sum = sum([int(f.get("volume", 0)) for f in frazy if str(f.get("volume")).isdigit()])
            url_title = k.get("proponowany_title", k.get("proponowany_h1", k.get("nazwa_klastra", "")))
            url_target = k.get("docelowa_istniejaca_strona", k.get("produkt", ""))
            sekcje_str = "\n".join([f"- {s.get('naglowek', '')}: {s.get('cel_sekcji', '')}" for s in k.get("proponowane_sekcje", [])])
            faq_str = "\n".join([f"- Q: {f.get('pytanie', '')}\n  A: {f.get('bezpieczna_odpowiedz', '')}" for f in k.get("proponowane_faq", [])])
            
            cluster_data.append({
                "Adres URL (Docelowy / Produkt)": url_target,
                "Proponowany Title / H1": url_title,
                "Nazwa Klastra": k.get("nazwa_klastra", ""),
                "Frazy w klastrze": frazy_str,
                "Łączny Volume": vol_sum,
                "Rekomendowana Akcja": k.get("rekomendacja", ""),
                "Priorytet": k.get("priorytet", ""),
                "Typ Klastra": k.get("typ_klastra", ""),
                "Bezpieczny Kierunek": k.get("bezpieczny_kierunek_tresci", ""),
                "Czego NIE sugerować": k.get("czego_nie_sugerowac", ""),
                "Uzasadnienie": k.get("uzasadnienie_rekomendacji", ""),
                "Proponowane Sekcje": sekcje_str,
                "Proponowane FAQ": faq_str
            })
        if cluster_data:
            sheets["6. Brand Klastry"] = pd.DataFrame(cluster_data)
            
        if "brand_analysis_results" in st.session_state:
            frazy_data = []
            for item in st.session_state.brand_analysis_results:
                frazy_data.append({
                    "Fraza (Keyword)": item.get("keyword", ""),
                    "Volume": item.get("volume", 0),
                    "Pozycja": item.get("position", 0),
                    "Dopasowany Produkt": item.get("produkt", ""),
                    "Intencja": item.get("intencja", ""),
                    "Etap Ścieżki": item.get("etap_sciezki_uzytkownika", ""),
                    "Problem Użytkownika": item.get("problem_uzytkownika", ""),
                    "Dopasowanie": item.get("dopasowanie_do_produktu", ""),
                    "Proponowany Temat/Sekcja": item.get("proponowany_temat_lub_sekcja", ""),
                    "Rekomendowany Typ Treści": item.get("rekomendowany_typ_tresci", ""),
                    "Ryzyko Claimów": item.get("ryzyko_claimow", ""),
                    "Bezpieczny Kierunek": item.get("bezpieczny_kierunek_odpowiedzi", ""),
                    "Czego NIE sugerować": item.get("czego_nie_sugerowac", ""),
                    "Uzasadnienie": item.get("uzasadnienie", "")
                })
            if frazy_data:
                sheets["6a. Brand Frazy"] = pd.DataFrame(frazy_data)
                
        if sheets:
            excel_data = to_excel_multi(sheets)
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Pobierz Analizę Brandu (XLSX)",
                    data=excel_data,
                    file_name='analiza_brandu.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    type="primary"
                )
            with col2:
                # Prepare combined JSON
                combined_json = {
                    "etap1_frazy": st.session_state.get("brand_analysis_results", []),
                    "etap2_klastry": st.session_state.get("brand_clusters", {})
                }
                json_str = json.dumps(combined_json, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 Pobierz Pełny JSON (Etap 1 + Etap 2)",
                    data=json_str,
                    file_name='analiza_brandu_pelny.json',
                    mime='application/json',
                    type="secondary"
                )
