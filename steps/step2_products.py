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
        step2_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step2_model")
        
        step2_sys = st.text_area("System Prompt", value="Jesteś ekspertem SEO i farmacji/kosmetyki.", key="step2_sys")
        
        def_user_2_a = """Przeanalizuj treść opisu produktu ze strony internetowej.
Strona: {url}
Treść strony:
{content}

Zadanie:
Musisz zwrócić odpowiedź jako poprawny obiekt JSON.
Struktura JSON ma wyglądać następująco:
{
  "problem": "Opisz krótko jaki problem medyczny/kosmetyczny ten produkt rozwiązuje",
  "ograniczenia": "Opisz ograniczenia (np. wiek, przeciwwskazania)",
  "przyczyny": "Co powoduje schorzenie i dla kogo produkt jest przeznaczony?"
}"""
        step2_user_a = st.text_area("User Prompt 1: Analiza Produktu", value=def_user_2_a, height=200, key="step2_user_a")
        
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
        step2_user_b = st.text_area("User Prompt 2: Frazy SEO", value=def_user_2_b, height=180, key="step2_user_b")
        
        col1, col2 = st.columns(2)
        with col1:
            step2_temp = st.slider("Temperatura", 0.0, 2.0, 0.7, 0.1, key="step2_temp")
        with col2:
            step2_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step2_tokens")
        
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
                            model=step2_model,
                            temperature=step2_temp,
                            max_tokens=step2_tokens,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step2_sys},
                                {"role": "user", "content": prompt_a}
                            ]
                        )
                        result_a = ai_response_a.choices[0].message.content
                        
                        # Call 2
                        prompt_b = step2_user_b.replace("{url}", url).replace("{content}", content[:4000])
                        ai_response_b = client.chat.completions.create(
                            model=step2_model,
                            temperature=step2_temp,
                            max_tokens=step2_tokens,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step2_sys},
                                {"role": "user", "content": prompt_b}
                            ]
                        )
                        result_b = ai_response_b.choices[0].message.content
                        
                        import json
                        try:
                            data_a = json.loads(result_a)
                            analysis_text = f"**Problem:** {data_a.get('problem', '')}\n\n**Ograniczenia:** {data_a.get('ograniczenia', '')}\n\n**Przyczyny:** {data_a.get('przyczyny', '')}"
                        except Exception as e:
                            analysis_text = f"Błąd parsowania JSON (Prompt 1): {result_a}"
                            st.warning(analysis_text)
                            
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
