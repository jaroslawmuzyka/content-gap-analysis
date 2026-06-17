import streamlit as st
import pandas as pd
import openai
from utils.helpers import to_excel

def render(openai_api_key):
    st.header("Krok 7: Weryfikacja Istniejących Treści")
    
    if "df_gap_results" not in st.session_state or "my_pages_df" not in st.session_state:
        st.warning("Musisz najpierw ukończyć Krok 4 (aby wygenerować pomysły Gap) oraz Krok 6 (aby wgrać własne URLe i Title).")
    else:
        df_gap = st.session_state.df_gap_results
        df_accepted = df_gap[df_gap['AI Verdict'].str.contains("ZAAKCEPTOWANO", na=False)]
        df_my = st.session_state.my_pages_df
        
        st.info(f"Do weryfikacji mamy {len(df_accepted)} zaakceptowanych pomysłów na wpisy oraz {len(df_my)} własnych podstron.")
        
        with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
            models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            step7_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step7_model")
            
            step7_sys = st.text_area("System Prompt", value="Jesteś redaktorem naczelnym. Pilnujesz, aby nie tworzyć zduplikowanych treści na stronie.", key="step7_sys")
            
            def_user_7 = """Pomysł na nowy wpis:
URL konkurencji: {target_url}
Tytuł konkurencji: {target_title}
Segment/Temat: {segment}

Oto lista adresów już istniejących na mojej stronie:
{my_pages_context}

Zadanie:
Czy wątek opisany w pomysle na wpis jest już realizowany przez któryś z moich adresów URL? Zwróć tylko poprawny obiekt JSON!
Struktura JSON:
{
  "status": "Opisane" lub "Nieopisane",
  "istniejacy_url": "Adres URL u mnie (jeśli Opisane, inaczej pozostaw puste)",
  "uzasadnienie": "Krótkie uzasadnienie 1 zdanie"
}"""
            step7_user = st.text_area("User Prompt (użyj {target_url}, {target_title}, {segment}, {my_pages_context})", value=def_user_7, height=350, key="step7_user")
            
            col1, col2 = st.columns(2)
            with col1:
                step7_temp = st.slider("Temperatura", 0.0, 2.0, 0.2, 0.1, key="step7_temp")
            with col2:
                step7_tokens = st.number_input("Max Tokens", 100, 16000, 1000, key="step7_tokens")
                
        if st.button("Rozpocznij Weryfikację AI", type="primary"):
            if len(df_accepted) == 0:
                st.warning("Nie masz żadnych Zaakceptowanych pomysłów z Kroku 4.")
            elif not openai_api_key:
                st.error("Brak klucza OpenAI.")
            else:
                my_pages_context = ""
                url_col = "URL" if "URL" in df_my.columns else df_my.columns[0]
                title_col = "Title" if "Title" in df_my.columns else ("Tytuł" if "Tytuł" in df_my.columns else None)
                
                for idx, row in df_my.iterrows():
                    u = str(row.get(url_col, ""))
                    t = str(row.get(title_col, "")) if title_col else ""
                    if u:
                        my_pages_context += f"- {u} (Title: {t})\n"
                        
                if len(my_pages_context) > 80000:
                    st.warning("Ostrzeżenie: Twoja lista własnych stron jest długa. Obcinam do pierwszych 80k znaków, by nie przekroczyć limitu modelu.")
                    my_pages_context = my_pages_context[:80000]
                
                progress_text = "Weryfikacja istnienia treści..."
                my_bar = st.progress(0, text=progress_text)
                
                results_verified = []
                client = openai.OpenAI(api_key=openai_api_key)
                
                for idx, row in df_accepted.iterrows():
                    target_url = str(row.get("Competitor URL", ""))
                    target_title = str(row.get("Competitor Title", ""))
                    segment = str(row.get("Segment", ""))
                    
                    prompt = step7_user.replace("{target_url}", target_url).replace("{target_title}", target_title).replace("{segment}", segment).replace("{my_pages_context}", my_pages_context)
                    
                    try:
                        ai_response = client.chat.completions.create(
                            model=step7_model,
                            temperature=step7_temp,
                            max_tokens=step7_tokens,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step7_sys},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        ans = ai_response.choices[0].message.content.strip()
                        import json
                        try:
                            data = json.loads(ans)
                            status = data.get("status", "Błąd")
                            istniejacy_url = data.get("istniejacy_url", "")
                            uzasadnienie = data.get("uzasadnienie", "")
                            
                            row_dict = row.to_dict()
                            row_dict["Status na własnej stronie"] = status
                            row_dict["Istniejący URL"] = istniejacy_url
                            row_dict["Weryfikacja Uzasadnienie"] = uzasadnienie
                            results_verified.append(row_dict)
                        except:
                            row_dict = row.to_dict()
                            row_dict["Status na własnej stronie"] = "Błąd JSON"
                            row_dict["Istniejący URL"] = ""
                            row_dict["Weryfikacja Uzasadnienie"] = ans
                            results_verified.append(row_dict)
                    except Exception as e:
                        row_dict = row.to_dict()
                        row_dict["Status na własnej stronie"] = f"Błąd API: {e}"
                        row_dict["Istniejący URL"] = ""
                        row_dict["Weryfikacja Uzasadnienie"] = ""
                        results_verified.append(row_dict)
                        
                    my_bar.progress((idx + 1) / len(df_accepted), text=f"Weryfikacja {idx+1}/{len(df_accepted)}...")
                
                df_verified = pd.DataFrame(results_verified)
                st.session_state.df_verified_results = df_verified
                st.success("Weryfikacja zakończona!")
                
                st.dataframe(df_verified)
                
                st.download_button(
                    label="📥 Pobierz zweryfikowane pomysły (XLSX)",
                    data=to_excel(df_verified),
                    file_name='zweryfikowane_pomysly.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
