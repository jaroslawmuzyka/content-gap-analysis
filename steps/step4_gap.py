import streamlit as st
import pandas as pd
import openai
from utils.helpers import to_excel

def render(openai_api_key):
    st.header("Krok 4: Mapowanie Content Gap (Non-Brand)")
    
    st.markdown("Wgraj plik wyeksportowany z Ahrefs: **Traffic share -> By page** (czyli adresy url i tytuły innych domen na bazie zbadanych wcześniej fraz).")
    
    gap_file = st.file_uploader("Wgraj plik z Ahrefs (CSV UTF-16LE, standardowe CSV lub XLSX)", type=['csv', 'xlsx', 'xls'])
    
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        step4_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step4_model")
        
        step4_sys = st.text_area("System Prompt", value="Jesteś ekspertem SEO.", key="step4_sys")
        
        def_user_4 = """Zadanie: Analiza Content Gap.
Oto URL obcej strony: {target_url}
Oto jej Tytuł (Title): {target_title}

Oto produkty, które klient sprzedaje:
{products_context}

Oceń BARDZO RYGORYSTYCZNIE, czy ta strona konkurencji jest artykułem poradnikowym (blogowym), który idealnie nadaje się na wpis na naszej stronie i wprost doprowadzi do sprzedaży jednego z naszych produktów.
Jeśli to jest kategoria sklepu, podstrona ofertowa innej firmy, lub temat zbyt luźno powiązany - ODRZUĆ. Zwróć tylko poprawny obiekt JSON.
Struktura JSON:
{
  "ocena": "ZAAKCEPTOWANO" lub "ODRZUCAM",
  "produkt": "Adres URL naszego produktu z podanej listy (lub puste jeśli brak)",
  "segment": "Kategoria/problem, którego dotyczy wpis (np. łuszczyca, sucha skóra)",
  "uzasadnienie": "Krótkie uzasadnienie decyzji dlaczego powiązano z produktem lub dlaczego odrzucono (1 zdanie)"
}"""
        step4_user = st.text_area("User Prompt (użyj {target_url}, {target_title}, {products_context})", value=def_user_4, height=350, key="step4_user")
        
        col1, col2 = st.columns(2)
        with col1:
            step4_temp = st.slider("Temperatura", 0.0, 2.0, 0.7, 0.1, key="step4_temp")
        with col2:
            step4_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step4_tokens")
            
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
                            ai_response = client.chat.completions.create(
                                model=step4_model,
                                temperature=step4_temp,
                                max_tokens=step4_tokens,
                                response_format={ "type": "json_object" },
                                messages=[
                                    {"role": "system", "content": step4_sys},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                            ans = ai_response.choices[0].message.content.strip()
                            
                            import json
                            try:
                                data = json.loads(ans)
                                ocena = data.get("ocena", "ODRZUCAM").upper()
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
                                    "AI Verdict": "BŁĄD/ODRZUCAM",
                                    "Recommended Product": "Błąd JSON",
                                    "Segment": "",
                                    "Reasoning": ans
                                })
                                results.append(row_result)
                        except Exception as e:
                            st.warning(f"Błąd OpenAI przy wierszu {idx}: {e}")
                            
                        my_bar.progress((idx + 1) / len(df_gap), text=f"Przeanalizowano {idx+1}/{len(df_gap)} wierszy.")
                    
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
