import streamlit as st
import pandas as pd
import openai

def render(openai_api_key):
    st.header("Krok 5: Analiza Brandu")
    
    st.markdown("Wgraj pliki zawierające zapytania brandowe, czyli to, co użytkownicy wyszukują wokół nazwy Twojej marki/produktu (np. z Ahrefs i Senuto).")
    
    col1, col2 = st.columns(2)
    with col1:
        brand_ahrefs = st.file_uploader("Brand Keywords Ahrefs (CSV)", type=['csv'])
    with col2:
        brand_senuto = st.file_uploader("Brand Keywords Senuto (XLSX)", type=['xlsx', 'xls'])
        
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        step5_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step5_model")
        
        step5_sys = st.text_area("System Prompt", value="Jesteś ekspertem od analizy intencji słów kluczowych.", key="step5_sys")
        
        def_user_5 = """Oto lista zapytań użytkowników zawierających nazwę brandu/produktu klienta:
{chunk}

Zadanie:
Pogrupuj te zapytania na klastry intencji (np. Pytania o stosowanie, Skutki uboczne, Wiek dziecka, Opinie).
Zaproponuj 3 gotowe tematy poradnikowe na bloga, które zbiorą ruch z tych zapytań i najlepiej na nie odpowiedzą.
Zwróć wynik w ładnym formacie markdown (Tytuł klastra, frazy, sugerowane artykuły)."""
        step5_user = st.text_area("User Prompt (użyj {chunk} jako zmiennej na paczkę fraz)", value=def_user_5, height=200, key="step5_user")
        
        col1, col2 = st.columns(2)
        with col1:
            step5_temp = st.slider("Temperatura", 0.0, 2.0, 0.7, 0.1, key="step5_temp")
        with col2:
            step5_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step5_tokens")
            
    if st.button("Rozpocznij Analizę Brandu AI", type="primary"):
        brand_kws = []
        if brand_ahrefs:
            try:
                df_b_ahrefs = pd.read_csv(brand_ahrefs, encoding="utf-16le", sep="\t")
                col_k = "Keyword" if "Keyword" in df_b_ahrefs.columns else df_b_ahrefs.columns[0]
                brand_kws.extend(df_b_ahrefs[col_k].dropna().tolist())
            except:
                st.error("Błąd parsowania Ahrefs Brand CSV.")
        if brand_senuto:
            try:
                df_b_senuto = pd.read_excel(brand_senuto)
                col_k = "Słowo kluczowe" if "Słowo kluczowe" in df_b_senuto.columns else df_b_senuto.columns[0]
                brand_kws.extend(df_b_senuto[col_k].dropna().tolist())
            except:
                st.error("Błąd parsowania Senuto Brand XLSX.")
                
        if brand_kws:
            unique_kws = list(set(brand_kws))
            st.info(f"Znaleziono {len(unique_kws)} unikalnych zapytań brandowych. Rozpoczynam AI Kategoryzację...")
            
            all_brand_ideas = ""
            client = openai.OpenAI(api_key=openai_api_key)
            
            chunk_size = 100
            chunks = [unique_kws[i:i + chunk_size] for i in range(0, len(unique_kws), chunk_size)]
            
            my_bar = st.progress(0, text="Analiza zapytań brandowych...")
            for i, chunk in enumerate(chunks):
                prompt = step5_user.replace("{chunk}", str(chunk))
                try:
                    ai_response = client.chat.completions.create(
                        model=step5_model,
                        temperature=step5_temp,
                        max_tokens=step5_tokens,
                        messages=[
                            {"role": "system", "content": step5_sys},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    all_brand_ideas += ai_response.choices[0].message.content + "\n\n---\n\n"
                except Exception as e:
                    st.warning(f"Błąd OpenAI przy paczce {i+1}: {e}")
                
                my_bar.progress((i + 1) / len(chunks), text=f"Przeanalizowano paczkę {i+1}/{len(chunks)}.")
            
            st.success("Kategoryzacja zakończona!")
            st.markdown(all_brand_ideas)
        else:
            st.warning("Nie załadowano żadnych poprawnych plików z frazami brandowymi.")
