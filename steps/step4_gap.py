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
        
        template_4 = st.radio("Szablon Ustawień (Content Gap):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: low, temp: 1.0)"], key="template_4")
        if template_4 == "Domyślny (Ręczne parametry)":
            step4_model = st.selectbox("Wybierz model OpenAI:", models, index=models.index("gpt-5.4-mini") if "gpt-5.4-mini" in models else 0, key="step4_model")
            col1, col2 = st.columns(2)
            with col1:
                step4_temp = st.slider("Temperatura", 0.0, 2.0, 1.0 if step4_model == "gpt-5.4-mini" else 0.7, 0.1, key="step4_temp")
            with col2:
                step4_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step4_tokens")
            params_4 = {"model": step4_model, "temperature": 1.0 if step4_model == "gpt-5.4-mini" else step4_temp, "max_tokens": step4_tokens}
        else:
            st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=1.0, reasoning_effort=low.")
            params_4 = {"model": "gpt-5.4-mini", "temperature": 1.0, "reasoning_effort": "low"}
        
        step4_sys_def = """Jesteś ekspertem SEO i rygorystycznym analitykiem Content Gap dla produktów zdrowotnych, kosmetycznych, dermokosmetycznych, OTC oraz leków bez recepty.

Twoim zadaniem jest ocena, czy temat strony konkurencji pasuje do produktu klienta na podstawie:
* URL-a konkurencji,
* Title konkurencji,
* kontekstu produktu klienta.

Masz dostęp wyłącznie do URL-a i Title strony konkurencji. Nie znasz pełnej treści strony. Nie wolno Ci zakładać, że strona zawiera informacje, których nie da się wywnioskować z URL-a lub Title.

Najważniejsza zasada:
Używaj dostarczonego Kontekstu Produktu jako głównego źródła decyzji. To on określa, do jakich tematów produkt pasuje, do jakich pasuje warunkowo, a do jakich nie należy go naciągać.

Oceniaj bardzo rygorystycznie i konserwatywnie.

Decyzja ma odpowiedzieć na jedno pytanie:
Czy temat wynikający z URL-a i Title można bezpiecznie oraz naturalnie powiązać z jednym z produktów klienta?

ZASADA SZCZEGÓŁOWYCH LOKALIZACJI, ODMIAN I POSTACI:
Jeżeli URL konkurencji dotyczy bardzo specyficznej odmiany problemu lub specyficznej lokalizacji anatomicznej (np. ból głowy napięciowy, łuszczyca paznokci, infekcja gardła), a produkt klienta ma przeznaczenie bardzo ogólne (np. ogólna tabletka przeciwbólowa, uniwersalny krem na skórę), ODRZUĆ temat jako NIE_PASUJE, chyba że z dostarczonego Kontekstu Produktu jasno wynika, że produkt adresuje to specyficzne wskazanie.
Wyjątek: Jeżeli specyficzna lokalizacja jest naturalnym podzbiorem przeznaczenia ogólnego (np. 'ból ręki' dla ogólnej tabletki przeciwbólowej, 'łuszczyca dłoni' dla ogólnej maści na skórę) i z logiki medycznej oraz postaci produktu (tabletka, maść, syrop) wynika, że zadziała on w tym miejscu (np. działa ogólnoustrojowo lub można go tam bezpiecznie posmarować) - zwróć PASUJE.

Zasady akceptacji:
1. Zwróć "PASUJE" tylko wtedy, gdy URL lub Title wyraźnie wskazuje temat, który jest mocno zgodny z PRZYNAJMNIEJ JEDNYM produktem według dostarczonego Kontekstu Produktów.
2. Możesz zwrócić "PASUJE" dla tematu warunkowego tylko wtedy, gdy URL lub Title jasno zawęża temat do problemu, skutku, objawu albo potrzeby, którą konkretny produkt rzeczywiście adresuje.
3. Jeżeli produkt wspiera objaw lub skutek problemu, ale nie problem pierwotny, zaakceptuj tylko wtedy, gdy URL lub Title dotyczy tego objawu lub skutku.
4. Jeżeli produkt łagodzi objawy choroby, można zaakceptować temat o objawach tej choroby, ale nie temat sugerujący leczenie choroby, jeśli nie wynika to z dostarczonego Kontekstu Produktów.
5. Jeżeli temat jest poradnikowy, edukacyjny lub problemowy i mieści się w granicach któregoś produktu, możesz zaakceptować.
6. UWAGA: Masz do dyspozycji listę KILKU produktów. Musisz ocenić potencjał dopasowania strony do KAŻDEGO z nich. Zwróć jako `produkt` ten, który jest NAJLEPIEJ dopasowany. Jeśli pasuje więcej niż jeden produkt, wskaż ten o najsilniejszym kontekście.

Zasady odrzucenia:
1. Zwróć "NIE_PASUJE", jeśli temat jest tylko luźno powiązany z produktem.
2. Zwróć "NIE_PASUJE", jeśli temat wymagałby naciągania właściwości produktu.
3. Zwróć "NIE_PASUJE", jeśli temat dotyczy problemu pierwotnego, którego produkt nie rozwiązuje ani nie wspiera według dostarczonego Kontekstu Produktu.

---
KONTEKST PRODUKTU:
{products_context}
4. Zwróć "NIE_PASUJE", jeśli URL lub Title sugeruje kategorię sklepu, kartę produktu, listing, ranking, porównywarkę, stronę ofertową, aptekę, forum, tag, paginację albo stronę główną.
5. Zwróć "NIE_PASUJE", jeśli typ strony lub temat jest niejasny.
6. Zwróć "NIE_PASUJE", jeśli na podstawie samego URL-a i Title nie da się pewnie stwierdzić dopasowania.
7. Zwróć "NIE_PASUJE", jeśli temat wymagałby ryzykownego claimu medycznego, którego nie potwierdza `{products_context}`.

Domyślna decyzja:
Jeśli masz wątpliwość, wybierz "NIE_PASUJE".

Nie oceniaj:
* potencjału ruchu,
* siły konkurencji,
* jakości strony konkurencji,
* opłacalności tworzenia treści,
* pełnej treści strony, bo jej nie znasz.

Odpowiadaj wyłącznie poprawnym JSON-em. Nie dodawaj markdowna, komentarzy ani tekstu poza JSON-em."""
        step4_sys = st.text_area("System Prompt", value=step4_sys_def, height=300, key="step4_sys")
        
        def_user_4 = """Zadanie: decyzja, czy temat strony konkurencji pasuje do produktu klienta.

Dane strony konkurencji:

URL:
{target_url}

Title:
{target_title}

Kontekst produktów klienta:
{products_context}

Cel:
Oceń, czy temat wynikający z URL-a i Title pasuje do któregoś produktu klienta.

Masz odpowiedzieć krótko i decyzyjnie:
* jeśli pasuje, wskaż produkt i w jednym zdaniu wyjaśnij dlaczego,
* jeśli nie pasuje, zostaw produkt pusty i w jednym zdaniu wyjaśnij dlaczego.

Pamiętaj:
* masz tylko URL i Title,
* nie znasz pełnej treści strony,
* nie zgaduj,
* używaj `{products_context}` jako głównego źródła decyzji,
* akceptuj tylko jasne dopasowania,
* odrzucaj tematy luźne, niejasne, zakupowe, listingowe, produktowe albo ryzykowne komunikacyjnie.

Zwróć wyłącznie poprawny JSON:
{
"ocena": "PASUJE | NIE_PASUJE",
"produkt": "adres URL lub nazwa najlepiej dopasowanego produktu z kontekstu klienta albo pusty string",
"segment": "krótki segment/problematyka, np. sucha skóra, odparzenia, łagodzenie objawów łuszczycy, wyprysk, wyprzenia albo pusty string",
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
                    
                    products_context = "Lista naszych produktów wraz ze skonsolidowanym kontekstem Content Gap:\n"
                    for item in st.session_state.product_analysis:
                        ctx = item.get("products_context", item.get("analysis", ""))
                        products_context += f"- Produkt: {item['url']}\n\nKontekst:\n{ctx}\n\n---\n"
                        
                    progress_text = "Analiza stron konkurencji..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    results = []
                    client = openai.OpenAI(api_key=openai_api_key)
                    
                    for idx, row in df_gap.iterrows():
                        target_url = row.get("URL", "")
                        target_title = row.get("Title", "")
                        
                        prompt = step4_user.replace("{target_url}", target_url).replace("{target_title}", target_title).replace("{products_context}", products_context)
                        sys_prompt = step4_sys.replace("{products_context}", products_context)
                        
                        try:
                            call_4_kwargs = {
                                "model": params_4["model"],
                                "response_format": { "type": "json_object" },
                                "messages": [
                                    {"role": "system", "content": sys_prompt},
                                    {"role": "user", "content": prompt}
                                ]
                            }
                            if "temperature" in params_4: call_4_kwargs["temperature"] = params_4["temperature"]
                            if "max_tokens" in params_4:
                                if any(m in params_4["model"] for m in ["gpt-5", "o1", "o3"]): call_4_kwargs["max_completion_tokens"] = params_4["max_tokens"]
                                else: call_4_kwargs["max_tokens"] = params_4["max_tokens"]
                            if "reasoning_effort" in params_4: call_4_kwargs["reasoning_effort"] = params_4["reasoning_effort"]
                                
                            ai_response = client.chat.completions.create(**call_4_kwargs)
                            if ai_response.usage:
                                from utils.helpers import track_usage
                                track_usage(params_4["model"], ai_response.usage.prompt_tokens, ai_response.usage.completion_tokens)
                            ans = ai_response.choices[0].message.content.strip()
                            
                            import json
                            from utils.helpers import clean_json
                            try:
                                data = json.loads(clean_json(ans))
                                ocena = str(data.get("ocena", "NIE_PASUJE")).upper().strip()
                                produkt = data.get("produkt", "")
                                segment = data.get("segment", "")
                                uzasadnienie = data.get("uzasadnienie", "")
                                
                                row_result = row.to_dict()
                                row_result.update({
                                    "AI Verdict": ocena,
                                    "Recommended Product": produkt,
                                    "Segment": segment,
                                    "Reasoning": uzasadnienie
                                })
                                results.append(row_result)
                            except:
                                row_result = row.to_dict()
                                row_result.update({
                                    "AI Verdict": "BŁĄD/NIE_PASUJE",
                                    "Recommended Product": "Błąd JSON",
                                    "Segment": "",
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
                        
                        df_accepted = df_results[df_results['AI Verdict'] == "PASUJE"]
                        df_rejected = df_results[df_results['AI Verdict'] != "PASUJE"]
                        
                        tab1, tab2 = st.tabs(["✅ Pasuje", "❌ Nie pasuje"])
                        with tab1:
                            st.write(f"Pasuje: {len(df_accepted)}")
                            st.dataframe(df_accepted)
                        with tab2:
                            st.write(f"Nie pasuje: {len(df_rejected)}")
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
