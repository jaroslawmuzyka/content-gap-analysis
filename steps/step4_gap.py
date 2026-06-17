import streamlit as st
import pandas as pd
import openai
from utils.helpers import to_excel

def render(openai_api_key):
    st.header("Krok 4: Mapowanie Content Gap (Non-Brand)")
    
    st.markdown("Wgraj plik wyeksportowany z Ahrefs: **Traffic share -> By page** (czyli adresy url i tytuły innych domen na bazie zbadanych wcześniej fraz).")
    
    gap_file = st.file_uploader("Wgraj plik z Ahrefs (CSV UTF-16LE, standardowe CSV lub XLSX)", type=['csv', 'xlsx', 'xls'])
    
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-5.5", "gpt-5.4-mini", "o1-mini", "o3-mini"]
        
        template_4 = st.radio("Szablon Ustawień (Content Gap):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: low, temp: 0.1)"], key="template_4")
        if template_4 == "Domyślny (Ręczne parametry)":
            step4_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step4_model")
            col1, col2 = st.columns(2)
            with col1:
                step4_temp = st.slider("Temperatura", 0.0, 2.0, 0.7, 0.1, key="step4_temp")
            with col2:
                step4_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step4_tokens")
            params_4 = {"model": step4_model, "temperature": step4_temp, "max_tokens": step4_tokens}
        else:
            st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=0.1, reasoning_effort=low.")
            params_4 = {"model": "gpt-5.4-mini", "temperature": 0.1, "reasoning_effort": "low"}
        
        step4_sys_def = """Jesteś ekspertem SEO i analitykiem Content Gap dla e-commerce oraz marek medycznych, kosmetycznych, dermokosmetycznych i OTC.

Twoim zadaniem jest bardzo rygorystyczna ocena, czy dana strona konkurencji prawdopodobnie nadaje się jako inspiracja do stworzenia artykułu poradnikowego na stronie klienta.

Masz dostęp wyłącznie do URL-a oraz Title strony konkurencji. Nie znasz pełnej treści strony. Nie wolno Ci zakładać, że na stronie znajduje się coś, czego nie da się wywnioskować z URL-a lub Title.

Oceniaj konserwatywnie:
* jeśli strona wyraźnie wygląda na artykuł, poradnik, blog lub treść edukacyjną — możesz zaakceptować,
* jeśli wygląda na kategorię sklepu, kartę produktu, listing, ranking, stronę ofertową, aptekę, forum, tag, paginację lub stronę główną — odrzuć,
* jeśli typ strony jest niejasny — odrzuć,
* jeśli temat jest tylko luźno powiązany z produktem klienta — odrzuć,
* jeśli produkt klienta nie odpowiada bezpośrednio na problem z Title lub URL — odrzuć,
* jeśli artykuł wymagałby naciągania powiązania z produktem — odrzuć,
* jeśli temat wymagałby sugerowania działania produktu, którego nie potwierdza kontekst produktów klienta — odrzuć.

Domyślna decyzja to "ODRZUCAM". Akceptuj tylko mocne, oczywiste dopasowania.

Ważne:
* Nie oceniaj, czy temat jest ogólnie ciekawy.
* Nie oceniaj, czy konkurencja jest silna.
* Nie oceniaj potencjału ruchu.
* Oceniaj wyłącznie, czy na podstawie URL-a i Title można stworzyć bezpieczny, poradnikowy artykuł prowadzący do jednego z produktów klienta.
* Jeżeli produkt może wspierać tylko skutek problemu, ale nie problem pierwotny, zaakceptuj wyłącznie wtedy, gdy Title lub URL jasno wskazuje na ten skutek.
* Przykład: jeśli produkt pomaga na suchą skórę, a Title dotyczy trądziku, odrzuć. Możesz zaakceptować tylko wtedy, gdy Title lub URL dotyczy przesuszenia skóry po terapii przeciwtrądzikowej.
* Zwróć wyłącznie poprawny JSON. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em."""
        step4_sys = st.text_area("System Prompt", value=step4_sys_def, height=300, key="step4_sys")
        
        def_user_4 = """Zadanie: analiza Content Gap na podstawie ograniczonych danych.

Dane strony konkurencji:
URL:
{target_url}

Title:
{target_title}

Produkty klienta:
{products_context}

Cel:
Oceń bardzo rygorystycznie, czy ta strona konkurencji prawdopodobnie jest artykułem poradnikowym, blogowym lub edukacyjnym, który nadaje się na inspirację do wpisu na naszej stronie i może naturalnie prowadzić do sprzedaży jednego z produktów klienta.

Masz tylko URL i Title, więc nie zakładaj pełnej treści strony.

Zaakceptuj tylko wtedy, gdy jednocześnie:
* URL lub Title wyraźnie sugeruje artykuł poradnikowy, blogowy albo edukacyjny,
* temat dotyczy konkretnego problemu użytkownika,
* problem jest bezpośrednio powiązany z jednym z produktów klienta,
* produkt klienta może być naturalnym rozwiązaniem lub wsparciem w tym problemie,
* powiązanie z produktem nie jest naciągane,
* nie trzeba sugerować właściwości produktu, których nie ma w kontekście produktów klienta.

Odrzuć, jeśli:
* URL lub Title wskazuje na kategorię sklepu,
* URL lub Title wskazuje na kartę produktu,
* URL lub Title wskazuje na listing produktów,
* URL lub Title wskazuje na ranking, porównanie ofert, aptekę, forum, tag, paginację lub stronę główną,
* temat jest zbyt ogólny,
* temat jest tylko luźno powiązany z produktem,
* temat dotyczy problemu, którego produkt klienta bezpośrednio nie rozwiązuje,
* typ strony jest niejasny,
* brakuje wystarczających danych do pewnej akceptacji.

Zwróć wyłącznie poprawny JSON w strukturze:
{
"ocena": "ZAAKCEPTOWANO lub ODRZUCAM",
"produkt": "adres URL najlepiej dopasowanego produktu klienta albo pusty string",
"segment": "kategoria, problem lub potrzeba użytkownika, np. sucha skóra, otarcia, regeneracja skóry",
"prawdopodobny_typ_strony": "artykul_poradnikowy | blog | poradnik | kategoria_sklepu | karta_produktu | listing | ranking | forum | apteka | tag | strona_glowna | inny | niejasne",
"prawdopodobna_intencja": "informacyjna | poradnikowa | produktowa | transakcyjna | porownawcza | nawigacyjna | niejasna",
"dopasowanie_do_produktu": "bezposrednie | posrednie | luzne | brak",
"czy_moze_prowadzic_do_sprzedazy": true,
"ryzyko_claimow": "niskie | srednie | wysokie",
"pewnosc_oceny": "wysoka | srednia | niska",
"sygnaly_z_url": [
"krótkie sygnały z URL, które wpłynęły na ocenę"
],
"sygnaly_z_title": [
"krótkie sygnały z Title, które wpłynęły na ocenę"
],
"uzasadnienie": "jedno krótkie zdanie wyjaśniające decyzję"
}"""
        step4_user = st.text_area("User Prompt", value=def_user_4, height=350, key="step4_user")
            
    if st.button("Rozpocznij Dopasowywanie AI", type="primary"):
        if gap_file and "product_analysis" in st.session_state:
            with st.spinner("Parsowanie pliku..."):
                try:
                    if gap_file.name.endswith('.xlsx') or gap_file.name.endswith('.xls'):
                        df_gap = pd.read_excel(gap_file)
                    else:
                        try:
                            df_gap = pd.read_csv(gap_file, encoding="utf-16le", sep="\t")
                            if len(df_gap.columns) <= 1:
                                raise ValueError("To nie jest plik rozdzielany tabulatorem")
                        except:
                            gap_file.seek(0)
                            df_gap = pd.read_csv(gap_file)
                except Exception as e:
                    st.error(f"Nie udało się odczytać pliku: {e}")
                    df_gap = pd.DataFrame()
                
                if "URL" not in df_gap.columns:
                    st.error("Plik nie zawiera kolumny 'URL'.")
                else:
                    df_gap = df_gap.drop_duplicates(subset=["URL"])
                        
                    st.success(f"Wczytano {len(df_gap)} unikalnych stron do analizy. Uruchamiam AI w trybie paczkowym...")
                    
                    products_context = "Lista naszych produktów wraz z analizą:\n"
                    for item in st.session_state.product_analysis:
                        products_context += f"- Produkt: {item['url']}\n  Analiza: {item['analysis']}\n\n"
                        
                    progress_text = "Analiza stron konkurencji..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    results = []
                    client = openai.OpenAI(api_key=openai_api_key)
                    
                    for idx, row in df_gap.iterrows():
                        target_url = row.get("URL", "")
                        target_title = row.get("Title", "")
                        
                        prompt = step4_user.replace("{target_url}", target_url).replace("{target_title}", target_title).replace("{products_context}", products_context)
                        
                        try:
                            call_4_kwargs = {
                                "model": params_4["model"],
                                "response_format": { "type": "json_object" },
                                "messages": [
                                    {"role": "system", "content": step4_sys},
                                    {"role": "user", "content": prompt}
                                ]
                            }
                            if "temperature" in params_4: call_4_kwargs["temperature"] = params_4["temperature"]
                            if "max_tokens" in params_4: call_4_kwargs["max_tokens"] = params_4["max_tokens"]
                            if "reasoning_effort" in params_4: call_4_kwargs["reasoning_effort"] = params_4["reasoning_effort"]
                                
                            ai_response = client.chat.completions.create(**call_4_kwargs)
                            ans = ai_response.choices[0].message.content.strip()
                            
                            import json
                            try:
                                data = json.loads(ans)
                                ocena = data.get("ocena", "ODRZUCAM").upper()
                                produkt = data.get("produkt", "")
                                segment = data.get("segment", "")
                                page_type = data.get("prawdopodobny_typ_strony", "")
                                intent = data.get("prawdopodobna_intencja", "")
                                match_level = data.get("dopasowanie_do_produktu", "")
                                can_sell = data.get("czy_moze_prowadzic_do_sprzedazy", False)
                                risk = data.get("ryzyko_claimow", "")
                                confidence = data.get("pewnosc_oceny", "")
                                sig_url = ", ".join(data.get("sygnaly_z_url", [])) if isinstance(data.get("sygnaly_z_url"), list) else str(data.get("sygnaly_z_url", ""))
                                sig_title = ", ".join(data.get("sygnaly_z_title", [])) if isinstance(data.get("sygnaly_z_title"), list) else str(data.get("sygnaly_z_title", ""))
                                uzasadnienie = data.get("uzasadnienie", "")
                                
                                row_result = row.to_dict()
                                row_result.update({
                                    "AI Verdict": ocena,
                                    "Recommended Product": produkt,
                                    "Segment": segment,
                                    "Page Type": page_type,
                                    "Intent": intent,
                                    "Product Match": match_level,
                                    "Can Sell": can_sell,
                                    "Claim Risk": risk,
                                    "Confidence": confidence,
                                    "URL Signals": sig_url,
                                    "Title Signals": sig_title,
                                    "Reasoning": uzasadnienie
                                })
                                results.append(row_result)
                            except:
                                row_result = row.to_dict()
                                row_result.update({
                                    "AI Verdict": "BŁĄD/ODRZUCAM",
                                    "Recommended Product": "Błąd JSON",
                                    "Segment": "",
                                    "Page Type": "",
                                    "Intent": "",
                                    "Product Match": "",
                                    "Can Sell": "",
                                    "Claim Risk": "",
                                    "Confidence": "",
                                    "URL Signals": "",
                                    "Title Signals": "",
                                    "Reasoning": ans
                                })
                                results.append(row_result)
                        except Exception as e:
                            st.warning(f"Błąd OpenAI przy wierszu {idx}: {e}")
                            
                        progress_value = min(1.0, (idx + 1) / len(df_gap))
                        my_bar.progress(progress_value, text=f"Przeanalizowano {idx+1}/{len(df_gap)} wierszy.")
                    
                    if results:
                        df_results = pd.DataFrame(results)
                        st.session_state.df_gap_results = df_results
                        st.success("Analiza zakończona!")
                        
                        df_accepted = df_results[df_results['AI Verdict'].str.contains("ZAAKCEPTOWANO", na=False)]
                        df_rejected = df_results[~df_results['AI Verdict'].str.contains("ZAAKCEPTOWANO", na=False)]
                        
                        tab1, tab2 = st.tabs(["✅ Zaakceptowane", "❌ Odrzucone"])
                        with tab1:
                            st.write(f"Zaakceptowano: {len(df_accepted)}")
                            st.dataframe(df_accepted)
                        with tab2:
                            st.write(f"Odrzucono: {len(df_rejected)}")
                            st.dataframe(df_rejected)
                        
                        st.download_button(
                            label="📥 Pobierz WSZYSTKIE wyniki Gap (XLSX)",
                            data=to_excel(df_results),
                            file_name='content_gap_wyniki_wszystkie.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    else:
                        st.warning("Żaden z adresów nie został przeanalizowany.")
        else:
            st.warning("Upewnij się, że wgrałeś plik oraz że w Kroku 2 zostały przeanalizowane produkty.")
