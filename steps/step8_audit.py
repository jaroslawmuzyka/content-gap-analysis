import streamlit as st
import pandas as pd
import requests
import openai
from utils.helpers import to_excel

def render(openai_api_key):
    st.header("Krok 8: Audyt Contentu (AI Readiness)")
    st.markdown("Wgraj plik (np. XLSX lub CSV) z listą adresów URL do zaudytowania. Skrypt wejdzie na każdą podstronę, pobierze jej zawartość i oceni ją pod kątem kryteriów contentowych (trafność, zaufanie, linkowanie, styl itp.).")
    
    audit_file = st.file_uploader("Wgraj plik z URLami do audytu (wymagana kolumna URL)", type=['csv', 'xlsx', 'xls'])
    
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        step8_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step8_model")
        
        step8_sys = st.text_area("System Prompt", value="Jesteś ekspertem SEO i rygorystycznym audytorem treści. Oceniasz treść wg szczegółowych kryteriów. Odpowiadasz wyłącznie obiektem JSON bez formatowania markdown.", key="step8_sys")
        
        def_user_8 = """Audyt Contentu.
Oto URL analizowanej strony: {target_url}
Oto zeskrapowana treść z tej strony:
{content}

Zadanie:
Twoim zadaniem jest szczegółowa ocena powyższej treści pod kątem każdego z poniższych 12 kryteriów. 
Dla każdego kryterium przypisz status z puli: "Dobry", "Średni", "Do poprawy", "Brak" oraz napisz w 1-2 zdaniach konkretną rekomendację (co zmienić, dodać, usunąć).
Kryteria do oceny:
1. trafnosc: Jak nasze treści są dopasowane do domyślnego zapytania użytkownika (czy rozwiązują główny problem).
2. dokladnosc: Rzetelność, budowa bazy wiedzy, czy to ogólniki czy fachowe dane.
3. wiarygodnosc: Poziom zaufania, opinia eksperta, adnotacje, linki do źródeł medycznych/naukowych.
4. autorytet: Tworzenie powiązanych klastrów, powiązanie tematu z grzybicą, odpornością itp. (topical authority).
5. linkowanie: Linkowanie wewnętrzne do innych poradników i produktów z oferty wewnątrz tekstu.
6. odswiezanie: Czy treść jest ponadczasowa, czy wymaga odświeżenia/aktualizacji pod kątem nowych danych.
7. rozbudowa: Czy artykuł wyczerpuje temat czy jest krótki tekst wymagający rozbudowy.
8. styl: Styl dopasowany do intencji (pytania jako nagłówki, spis treści, Q&A).
9. fragmentacja: Identyfikacja czy akapity funkcjonują jako samodzielne fragmenty (zwięzłe odpowiedzi, definicje łatwe do cytowania).
10. faq: Obecność sekcji FAQ.
11. pogrubienia: Jakość pogrubień (czy pomagają skanować).
12. listy: Obecność i jakość list numerowanych/nienumerowanych.

Zwróć wynik jako poprawny JSON! Bez owijania w ```json.
Format (dokładnie ten układ, każdy klucz MUSI zawierać "status" i "rekomendacja"):
{
  "trafnosc": {"status": "...", "rekomendacja": "..."},
  "dokladnosc": {"status": "...", "rekomendacja": "..."},
  "wiarygodnosc": {"status": "...", "rekomendacja": "..."},
  "autorytet": {"status": "...", "rekomendacja": "..."},
  "linkowanie": {"status": "...", "rekomendacja": "..."},
  "odswiezanie": {"status": "...", "rekomendacja": "..."},
  "rozbudowa": {"status": "...", "rekomendacja": "..."},
  "styl": {"status": "...", "rekomendacja": "..."},
  "fragmentacja": {"status": "...", "rekomendacja": "..."},
  "faq": {"status": "...", "rekomendacja": "..."},
  "pogrubienia": {"status": "...", "rekomendacja": "..."},
  "listy": {"status": "...", "rekomendacja": "..."}
}"""
        step8_user = st.text_area("User Prompt (użyj {target_url}, {content})", value=def_user_8, height=500, key="step8_user")
        
        col1, col2 = st.columns(2)
        with col1:
            step8_temp = st.slider("Temperatura", 0.0, 2.0, 0.2, 0.1, key="step8_temp")
        with col2:
            step8_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step8_tokens")

    if st.button("Rozpocznij Audyt AI", type="primary"):
        if audit_file:
            try:
                if audit_file.name.endswith('.csv'):
                    df_audit = pd.read_csv(audit_file)
                else:
                    df_audit = pd.read_excel(audit_file)
                    
                url_col = "URL" if "URL" in df_audit.columns else df_audit.columns[0]
                
                headers = {"Accept": "application/json"}
                if st.session_state.get("jina_api_key"):
                    headers["Authorization"] = f"Bearer {st.session_state.jina_api_key}"
                
                results_audit = []
                client = openai.OpenAI(api_key=openai_api_key)
                
                progress_text = "Pobieranie i audyt treści..."
                my_bar = st.progress(0, text=progress_text)
                
                for idx, row in df_audit.iterrows():
                    target_url = str(row.get(url_col, "")).strip()
                    if not target_url:
                        continue
                        
                    jina_url = f"https://r.jina.ai/{target_url}"
                    response = requests.get(jina_url, headers=headers)
                    if response.status_code == 200:
                        content = response.json().get('data', {}).get('content', response.text)
                    else:
                        st.error(f"Błąd pobierania {target_url}")
                        continue
                        
                    content_clipped = content[:40000]
                    
                    prompt = step8_user.replace("{target_url}", target_url).replace("{content}", content_clipped)
                    
                    try:
                        ai_response = client.chat.completions.create(
                            model=step8_model,
                            temperature=step8_temp,
                            max_tokens=step8_tokens,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step8_sys},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        ans = ai_response.choices[0].message.content.strip()
                        
                        import json
                        try:
                            data = json.loads(ans)
                            
                            row_dict = row.to_dict()
                            
                            keys_to_extract = ["trafnosc", "dokladnosc", "wiarygodnosc", "autorytet", "linkowanie", "odswiezanie", "rozbudowa", "styl", "fragmentacja", "faq", "pogrubienia", "listy"]
                            
                            for k in keys_to_extract:
                                k_data = data.get(k, {})
                                row_dict[f"{k.capitalize()} - Status"] = k_data.get("status", "")
                                row_dict[f"{k.capitalize()} - Rekomendacja"] = k_data.get("rekomendacja", "")
                                
                            results_audit.append(row_dict)
                        except:
                            row_dict = row.to_dict()
                            row_dict["BŁĄD AUDYTU"] = "Nie udało się sparsować JSON."
                            row_dict["AI RAW"] = ans
                            results_audit.append(row_dict)
                    except Exception as e:
                        row_dict = row.to_dict()
                        row_dict["BŁĄD AUDYTU"] = str(e)
                        results_audit.append(row_dict)
                        
                    my_bar.progress((idx + 1) / len(df_audit), text=f"Zaudytowano {idx+1}/{len(df_audit)}")
                
                df_audited = pd.DataFrame(results_audit)
                st.session_state.df_audited = df_audited
                st.success("Audyt zakończony!")
                st.dataframe(df_audited)
                
                st.download_button(
                    label="📥 Pobierz Audyt Contentu (XLSX)",
                    data=to_excel(df_audited),
                    file_name='audyt_contentu_ai.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f"Wystąpił błąd ogólny: {e}")
        else:
            st.warning("Wgraj najpierw plik z adresami URL.")
