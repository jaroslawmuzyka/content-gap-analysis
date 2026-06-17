import streamlit as st
import pandas as pd
import requests
import openai

def render(openai_api_key):
    st.header("Krok 2: Analiza Produktów (Jina Reader + AI)")
    
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
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        
        st.markdown("### 📝 Prompt 1: Analiza Produktu")
        step2_model_a = st.selectbox("Wybierz model dla analizy:", models, index=0, key="step2_model_a")
        step2_sys_a_def = """Jesteś analitykiem medyczno-kosmetycznym, strategiem contentowym i specjalistą SEO dla produktów zdrowotnych, dermokosmetycznych, kosmetycznych i OTC.

Twoim zadaniem nie jest tylko streszczenie treści strony. Twoim zadaniem jest zbudowanie możliwie pełnej mapy zastosowań produktu: jakie problemy rozwiązuje, z czego te problemy mogą wynikać, w jakich sytuacjach życiowych występują, jakie mają skutki, jakie grupy odbiorców mogą ich doświadczać oraz jakie tematy contentowe można na tej podstawie rozwijać.

Zasady bezpieczeństwa i jakości:
1. Nie wymyślaj właściwości leczniczych produktu.
2. Oddzielaj informacje wprost podane na stronie od wniosków i hipotez.
3. Jeżeli coś wynika z wiedzy ogólnej, ale nie jest potwierdzone w treści strony, oznacz to jako "wniosek" albo "hipoteza_contentowa".
4. Jeżeli dany temat może wymagać weryfikacji medycznej, prawnej, regulacyjnej, z ChPL, ulotką, etykietą lub działem regulatory, ustaw "wymaga_weryfikacji": true.
5. Nie podawaj dawkowania, instrukcji leczenia ani obietnic skuteczności, jeżeli nie ma ich w treści źródłowej.
6. Nie sugeruj stosowania produktu poza zakresem, który można racjonalnie uzasadnić opisem, składem, kategorią produktu lub informacjami ze strony.
7. W przypadku leków, terapii, chorób przewlekłych, ciąży, niemowląt, alergii, ran, infekcji lub skóry uszkodzonej zachowaj szczególną ostrożność.
8. Odpowiedź musi być wyłącznie poprawnym obiektem JSON. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
9. Jeżeli brakuje danych, wpisz null, pustą tablicę albo jasno oznacz "brak_danych_w_tresci".
10. Pisz po polsku, precyzyjnie i konkretnie."""
        step2_sys_a = st.text_area("System Prompt (Analiza)", value=step2_sys_a_def, height=250, key="step2_sys_a")
        
        def_user_2_a = """Przeanalizuj opis produktu ze strony internetowej.

Strona:
{url}

Treść strony:
{content}

Cel analizy:
Chcę zrozumieć produkt znacznie szerzej niż wynika to z prostego opisu na stronie. Nie interesuje mnie wyłącznie streszczenie typu "produkt pomaga na suchą skórę". Chcę odkryć pełną mapę problemów, przyczyn, skutków, sytuacji użycia, sezonowości, grup odbiorców, kontekstów lifestyle’owych, kontekstów medyczno-kosmetycznych oraz potencjalnych tematów contentowych.

Analizuj tak, jak product manager, ekspert medyczno-kosmetyczny i strateg SEO jednocześnie.

Szukaj zwłaszcza:
* problemów głównych, na które produkt odpowiada,
* problemów pobocznych i powiązanych,
* przyczyn tych problemów,
* skutków tych problemów,
* sytuacji życiowych, w których problem się pojawia,
* sezonowości, np. zima, lato, wiatr, mróz, słońce, klimatyzacja, ogrzewanie,
* aktywności, np. sport, bieganie, rower, praca fizyczna, podróże,
* grup odbiorców, np. dzieci, dorośli, seniorzy, osoby aktywne, osoby z wrażliwą skórą,
* związków przyczynowo-skutkowych, np. leczenie trądziku może wysuszać skórę, więc produkt może być tematem wspierającym regenerację skóry suchej, ale nie leczenie trądziku,
* tematów edukacyjnych, które nie są oczywiste po pierwszym przeczytaniu strony,
* tematów zdjęć, grafik i artykułów,
* ograniczeń, przeciwwskazań i ryzyk komunikacyjnych,
* tego, czego nie wolno twierdzić bez dodatkowej weryfikacji.

Zwróć wyłącznie poprawny JSON w poniższej strukturze:
{
"produkt": {"nazwa": "", "kategoria": "", "typ_produktu": "", "skladniki_aktywne_lub_kluczowe": [], "deklarowane_dzialanie_na_stronie": [], "status_informacji": {"czy_nazwa_jest_podana_w_tresci": true, "czy_sklad_jest_podany_w_tresci": true, "czy_kategoria_jest_podana_w_tresci": true}},
"glowny_problem": {"opis": "", "problem_medyczny_lub_kosmetyczny": "", "jak_produkt_moze_pomagac_wedlug_tresci": "", "poziom_pewnosci": "wysoki | sredni | niski", "zrodlo": "wprost_z_tresci | wniosek | hipoteza_contentowa"},
"problemy_powiazane": [{"problem": "", "opis": "", "relacja_do_produktu": "", "czy_produkt_rozwiazuje_problem_bezposrednio": true, "czy_produkt_moze_byc_wsparciem": true, "czego_nie_wolno_sugerowac": "", "poziom_pewnosci": "wysoki | sredni | niski", "zrodlo": "wprost_z_tresci | wniosek | hipoteza_contentowa", "wymaga_weryfikacji": true}],
"przyczyny_problemow": [{"przyczyna": "", "jaki_problem_powoduje": "", "mechanizm_lub_logika": "", "przyklad": "", "czy_przyczyna_jest_podana_w_tresci": true, "poziom_pewnosci": "wysoki | sredni | niski"}],
"skutki_i_objawy": [{"skutek_lub_objaw": "", "z_czego_moze_wynikac": "", "jak_laczy_sie_z_produktem": "", "czy_mozna_to_komunikowac_wprost": true, "ryzyko_naduzycia_claimu": "niskie | srednie | wysokie"}],
"konteksty_uzycia": {
  "sezonowe": [{"kontekst": "", "pora_roku_lub_warunki": "", "problem": "", "dlaczego_to_wazne": "", "pomysl_na_artykul": "", "pomysl_na_zdjecie_lub_grafike": "", "poziom_pewnosci": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
  "lifestyle_i_aktywnosc": [{"kontekst": "", "aktywność_lub_sytuacja": "", "problem": "", "zwiazek_z_produktem": "", "pomysl_na_artykul": "", "pomysl_na_zdjecie_lub_grafike": "", "poziom_pewnosci": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
  "medyczno_kosmetyczne": [{"kontekst": "", "problem_pierwotny": "", "problem_wtorny": "", "zwiazek_przyczynowo_skutkowy": "", "rola_produktu": "", "czego_nie_sugerowac": "", "pomysl_na_artykul": "", "poziom_pewnosci": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
  "codzienne_sytuacje": [{"sytuacja": "", "problem": "", "rola_produktu": "", "pomysl_na_content": "", "poziom_pewnosci": "wysoki | sredni | niski"}]
},
"grupy_docelowe": [{"grupa": "", "dlaczego_moze_potrzebowac_produktu": "", "typowe_sytuacje": [], "potencjalne_obawy": [], "komunikat_marketingowy_bezpieczny": "", "komunikat_ryzykowny_lub_do_unikania": "", "poziom_pewnosci": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
"ograniczenia_i_przeciwwskazania": {"wprost_z_tresci": [], "potencjalne_do_weryfikacji": [], "grupy_wymagajace_ostroznosci": [], "czego_brakuje_w_tresci_strony": []},
"mapa_contentowa": [{"temat": "", "intencja_uzytkownika": "informacyjna | poradnikowa | produktowa | porownawcza | sezonowa | problemowa", "problem_ktory_adresuje": "", "przyczyna_lub_kontekst": "", "proponowany_tytul_artykulu": "", "proponowany_h1": "", "sekcje_artykulu": [], "pomysl_na_zdjecie": "", "jak_naturalnie_polaczyc_z_produktem": "", "claimy_bezpieczne": [], "claimy_ryzykowne": [], "priorytet": "wysoki | sredni | niski", "uzasadnienie_priorytetu": ""}],
"nietypowe_insighty": [{"insight": "", "dlaczego_nie_jest_oczywisty": "", "jak_moze_pomoc_w_seo_lub_content_marketingu": "", "przyklad_wykorzystania": "", "poziom_pewnosci": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
"luki_na_stronie": [{"luka": "", "dlaczego_to_problem": "", "co_dodac_na_stronie": "", "typ_materialu": "tekst | artykul | FAQ | zdjecie | grafika | sekcja_produktowa | ostrzezenie | linkowanie_wewnetrzne", "priorytet": "wysoki | sredni | niski"}],
"faq": [{"pytanie": "", "bezpieczna_odpowiedz": "", "czy_wymaga_konsultacji_z_ekspertem": true}],
"slowa_kluczowe_i_encje": {"problemy": [], "objawy": [], "przyczyny": [], "grupy_docelowe": [], "sytuacje_uzycia": [], "sezonowosc": [], "skladniki": [], "tematy_powiazane": []},
"rekomendacje_dla_brand_managera": [{"rekomendacja": "", "uzasadnienie": "", "oczekiwany_efekt": "", "priorytet": "wysoki | sredni | niski", "wymaga_weryfikacji": true}],
"podsumowanie": {"najwazniejszy_wniosek": "", "najwieksza_szansa_contentowa": "", "najwieksze_ryzyko_komunikacyjne": "", "co_sprawdzic_przed_publikacja": []}
}"""
        step2_user_a = st.text_area("User Prompt (Analiza)", value=def_user_2_a, height=350, key="step2_user_a")
        
        ca1, ca2 = st.columns(2)
        with ca1:
            step2_temp_a = st.slider("Temperatura (Analiza)", 0.0, 2.0, 0.7, 0.1, key="step2_temp_a")
        with ca2:
            step2_tokens_a = st.number_input("Max Tokens (Analiza)", 100, 16000, 4000, key="step2_tokens_a")

        st.markdown("---")
        st.markdown("### 🔍 Prompt 2: Generowanie Fraz SEO")
        step2_model_b = st.selectbox("Wybierz model dla fraz SEO:", models, index=0, key="step2_model_b")
        step2_sys_b = st.text_area("System Prompt (Frazy SEO)", value="Jesteś ekspertem SEO.", key="step2_sys_b")
        
        def_user_2_b = """Wygeneruj frazy SEO dla produktu na podstawie jego treści.
Strona: {url}
Treść strony:
{content}

Zadanie:
Zwróć poprawny obiekt JSON z najważniejszymi frazami (max 10, od 1 do 3 słów) w mianowniku, pasującymi do tego produktu.
Struktura JSON:
{
  "seed_keywords": ["fraza 1", "fraza 2"]
}"""
        step2_user_b = st.text_area("User Prompt (Frazy SEO)", value=def_user_2_b, height=180, key="step2_user_b")
        
        cb1, cb2 = st.columns(2)
        with cb1:
            step2_temp_b = st.slider("Temperatura (Frazy SEO)", 0.0, 2.0, 0.7, 0.1, key="step2_temp_b")
        with cb2:
            step2_tokens_b = st.number_input("Max Tokens (Frazy SEO)", 100, 16000, 4000, key="step2_tokens_b")
        
    if st.button("Rozpocznij Analizę", type="primary"):
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
                        client = openai.OpenAI(api_key=openai_api_key)
                        
                        # Call 1
                        prompt_a = step2_user_a.replace("{url}", url).replace("{content}", content[:4000])
                        ai_response_a = client.chat.completions.create(
                            model=step2_model_a,
                            temperature=step2_temp_a,
                            max_tokens=step2_tokens_a,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step2_sys_a},
                                {"role": "user", "content": prompt_a}
                            ]
                        )
                        result_a = ai_response_a.choices[0].message.content
                        
                        # Call 2
                        prompt_b = step2_user_b.replace("{url}", url).replace("{content}", content[:4000])
                        ai_response_b = client.chat.completions.create(
                            model=step2_model_b,
                            temperature=step2_temp_b,
                            max_tokens=step2_tokens_b,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step2_sys_b},
                                {"role": "user", "content": prompt_b}
                            ]
                        )
                        result_b = ai_response_b.choices[0].message.content
                        
                        import json
                        try:
                            data_a = json.loads(result_a)
                            
                            md_lines = []
                            if "podsumowanie" in data_a:
                                p = data_a["podsumowanie"]
                                md_lines.append("### 🎯 Podsumowanie")
                                md_lines.append(f"- **Wniosek:** {p.get('najwazniejszy_wniosek', '')}")
                                md_lines.append(f"- **Szansa contentowa:** {p.get('najwieksza_szansa_contentowa', '')}")
                                md_lines.append(f"- **Ryzyko:** {p.get('najwieksze_ryzyko_komunikacyjne', '')}")
                                md_lines.append("")
                                
                            if "glowny_problem" in data_a:
                                gp = data_a["glowny_problem"]
                                md_lines.append(f"**Główny Problem:** {gp.get('opis', '')} ({gp.get('problem_medyczny_lub_kosmetyczny', '')})")
                                md_lines.append("")
                                
                            if "konteksty_uzycia" in data_a:
                                md_lines.append("### 🌍 Konteksty Użycia")
                                k = data_a["konteksty_uzycia"]
                                if "sezonowe" in k and k["sezonowe"]:
                                    md_lines.append("**Sezonowe:** " + ", ".join([s.get("pora_roku_lub_warunki","") for s in k["sezonowe"] if isinstance(s, dict) and s.get("pora_roku_lub_warunki")]))
                                if "lifestyle_i_aktywnosc" in k and k["lifestyle_i_aktywnosc"]:
                                    md_lines.append("**Lifestyle/Aktywność:** " + ", ".join([s.get("aktywność_lub_sytuacja","") for s in k["lifestyle_i_aktywnosc"] if isinstance(s, dict) and s.get("aktywność_lub_sytuacja")]))
                                if "medyczno_kosmetyczne" in k and k["medyczno_kosmetyczne"]:
                                    md_lines.append("**Medyczno-Kosmetyczne:** " + ", ".join([s.get("problem_wtorny","") for s in k["medyczno_kosmetyczne"] if isinstance(s, dict) and s.get("problem_wtorny")]))
                                md_lines.append("")
                                
                            if "mapa_contentowa" in data_a and isinstance(data_a["mapa_contentowa"], list):
                                md_lines.append("### 📝 Przykładowe Tematy Artykułów")
                                for m in data_a["mapa_contentowa"][:3]:
                                    if isinstance(m, dict):
                                        md_lines.append(f"- **{m.get('proponowany_tytul_artykulu', m.get('temat', ''))}** (Intencja: {m.get('intencja_uzytkownika', '')})")
                                md_lines.append("")

                            md_lines.append("### 📦 Pełny profil analizy JSON")
                            md_lines.append("```json\n" + json.dumps(data_a, indent=2, ensure_ascii=False) + "\n```")
                            
                            analysis_text = "\n".join(md_lines)
                        except Exception as e:
                            analysis_text = f"Błąd parsowania JSON (Prompt 1): {result_a}\n\nWyjątek: {e}"
                            st.warning(f"Błąd parsowania JSON dla {url}")
                            
                        try:
                            data_b = json.loads(result_b)
                            raw_phrases = data_b.get('seed_keywords', [])
                            phrases = [str(p).replace('*', '').strip().lower() for p in raw_phrases if str(p).strip()]
                        except Exception as e:
                            phrases = []
                            st.warning(f"Błąd parsowania JSON (Prompt 2): {result_b}")
                            
                        product_analysis.append({
                            "url": url,
                            "analysis": analysis_text,
                            "seed_keywords": phrases
                        })
                    else:
                        st.warning(f"Brak zawartości do analizy dla {url}")
                except Exception as e:
                    st.error(f"Błąd analizy {url}: {e}")
                    
                progress_value = min(1.0, (idx + 1) / len(items_to_analyze))
                my_bar.progress(progress_value, text=f"Przeanalizowano {idx+1} z {len(items_to_analyze)} produktów.")
                
            st.session_state.product_analysis = product_analysis
            st.success("Analiza zakończona!")
            
    if "product_analysis" in st.session_state:
        st.subheader("Wyniki Analizy AI")
        for item in st.session_state.product_analysis:
            with st.expander(item["url"]):
                st.markdown(item["analysis"])
