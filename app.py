import streamlit as st
import pandas as pd
import openai
import requests
import re
from io import BytesIO
from urllib.parse import urlparse

# Konfiguracja strony
st.set_page_config(page_title="Content Gap Analyzer", layout="wide")

# Ustawienie stanu początkowego
if "step" not in st.session_state:
    st.session_state.step = 1

# Pasek boczny na konfigurację i nawigację
with st.sidebar:
    st.title("⚙️ Ustawienia")
    
    # Modele OpenAI
    models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Wybierz model OpenAI:", models, index=0)
    st.session_state.selected_model = selected_model
    
    # Klucz API do OpenAI (jeśli chcemy pozwolić użytkownikowi na własny w UI, ale z założenia bierzemy z secrets)
    openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not openai_api_key:
        openai_api_key = st.text_input("Podaj klucz OpenAI API:", type="password")
    
    if openai_api_key:
        openai.api_key = openai_api_key
    else:
        st.warning("Brak klucza API OpenAI. Skrypt może nie działać prawidłowo w krokach AI.")
        
    # Klucz API do Jina Reader
    jina_api_key = st.secrets.get("JINA_API_KEY", "")
    if not jina_api_key:
        jina_api_key = st.text_input("Podaj klucz JINA API (opcjonalnie dla płatnego pakietu):", type="password")
        
    st.session_state.jina_api_key = jina_api_key
        
    st.markdown("---")
    st.title("🧭 Nawigacja")
    
    step1 = st.button("Krok 1: Wgranie Danych Domeny", use_container_width=True)
    step2 = st.button("Krok 2: Analiza Produktów (Jina + AI)", use_container_width=True)
    step3 = st.button("Krok 3: Generowanie Fraz", use_container_width=True)
    step4 = st.button("Krok 4: Mapowanie Content Gap", use_container_width=True)
    step5 = st.button("Krok 5: Analiza Brandu", use_container_width=True)
    
    if step1: st.session_state.step = 1
    if step2: st.session_state.step = 2
    if step3: st.session_state.step = 3
    if step4: st.session_state.step = 4
    if step5: st.session_state.step = 5

st.title("📈 Content Gap Analyzer")

# Funkcja pomocnicza: normalizacja URL
def normalize_url(url):
    if not isinstance(url, str):
        return ""
    # Usuwamy www, https://, http://, na końcu ukośnik
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    if url.endswith("/"):
        url = url[:-1]
    return url.strip()

# ================================
# KROK 1: Wgranie Danych Domeny
# ================================
if st.session_state.step == 1:
    st.header("Krok 1: Setup i Wgranie Danych Domeny")
    domain = st.text_input("Analizowana domena (np. linomag.pl):", value="linomag.pl")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Plik Ahrefs")
        ahrefs_file = st.file_uploader("Wgraj plik CSV z Ahrefs (All keywords)", type=['csv'], key="ahrefs")
    with col2:
        st.subheader("Plik Senuto")
        senuto_file = st.file_uploader("Wgraj plik XLSX z Senuto (All keywords)", type=['xlsx', 'xls'], key="senuto")
        
    if st.button("Konsoliduj Dane", type="primary"):
        if ahrefs_file and senuto_file:
            with st.spinner("Parsowanie i łączenie plików..."):
                try:
                    # Ahrefs jest w UTF-16LE i rozdzielany tabulatorem
                    df_ahrefs = pd.read_csv(ahrefs_file, encoding="utf-16le", sep="\t")
                except Exception as e:
                    # Fallback w przypadku innego kodowania
                    try:
                        ahrefs_file.seek(0)
                        df_ahrefs = pd.read_csv(ahrefs_file, encoding="utf-8")
                    except Exception as e2:
                        st.error(f"Błąd odczytu pliku Ahrefs: {e2}")
                        df_ahrefs = None
                
                try:
                    df_senuto = pd.read_excel(senuto_file)
                except Exception as e:
                    st.error(f"Błąd odczytu pliku Senuto: {e}")
                    df_senuto = None
                
                if df_ahrefs is not None and df_senuto is not None:
                    # Normalizacja URL dla Ahrefs i wydobycie fraz
                    # Ahrefs kolumny: "Keyword", "URL", "Volume"
                    col_kw_ahrefs = "Keyword" if "Keyword" in df_ahrefs.columns else df_ahrefs.columns[0]
                    col_url_ahrefs = "URL" if "URL" in df_ahrefs.columns else df_ahrefs.columns[1]
                    
                    df_a_clean = df_ahrefs[[col_kw_ahrefs, col_url_ahrefs]].rename(columns={col_kw_ahrefs: "keyword", col_url_ahrefs: "url"}).dropna()
                    df_a_clean["url_norm"] = df_a_clean["url"].apply(normalize_url)
                    df_a_clean["source"] = "Ahrefs"
                    
                    # Senuto kolumny: "Słowo kluczowe", "Adres URL"
                    col_kw_senuto = "Słowo kluczowe" if "Słowo kluczowe" in df_senuto.columns else df_senuto.columns[0]
                    col_url_senuto = "Adres URL" if "Adres URL" in df_senuto.columns else df_senuto.columns[1]
                    
                    df_s_clean = df_senuto[[col_kw_senuto, col_url_senuto]].rename(columns={col_kw_senuto: "keyword", col_url_senuto: "url"}).dropna()
                    df_s_clean["url_norm"] = df_s_clean["url"].apply(normalize_url)
                    df_s_clean["source"] = "Senuto"
                    
                    # Konsolidacja
                    df_combined = pd.concat([df_a_clean, df_s_clean], ignore_index=True)
                    # Deduplikacja na poziomie URL + Keyword, żeby nie dublować tych samych wyników
                    df_combined = df_combined.drop_duplicates(subset=["keyword", "url_norm"])
                    
                    st.session_state.df_domain = df_combined
                    st.success("Pliki zostały skonsolidowane!")
                    st.dataframe(df_combined.head(100)) # Podgląd pierwszych 100
        else:
            st.warning("Proszę wgrać oba pliki (Ahrefs i Senuto).")

# ================================
# KROK 2: Analiza Produktów
# ================================
elif st.session_state.step == 2:
    st.header("Krok 2: Analiza Produktów (Jina Reader + AI)")
    
    product_urls_text = st.text_area("Wklej adresy URL produktów klienta (po jednym w linii):", height=150)
    
    with st.expander("Opcje Jina Reader (Opcjonalne)"):
        css_include = st.text_input("Selektor CSS do uwzględnienia (np. .product-description):")
        css_exclude = st.text_input("Selektor CSS do wykluczenia (np. .footer, nav):")
        scrape_mode = st.selectbox("Tryb Jina Reader", ["Domyslnie", "Pomiń cache (X-No-Cache)"])
        
    if st.button("Pobierz i Analizuj", type="primary"):
        urls = [u.strip() for u in product_urls_text.split("\n") if u.strip()]
        if not urls:
            st.warning("Podaj przynajmniej jeden adres URL.")
        elif not openai_api_key:
            st.error("Wymagany klucz API OpenAI.")
        else:
            product_analysis = []
            progress_text = "Analiza produktów w toku..."
            my_bar = st.progress(0, text=progress_text)
            
            for idx, url in enumerate(urls):
                try:
                    headers = {"Accept": "application/json"}
                    
                    if st.session_state.get("jina_api_key"):
                        headers["Authorization"] = f"Bearer {st.session_state.jina_api_key}"
                        
                    if scrape_mode == "Pomiń cache (X-No-Cache)":
                        headers["X-No-Cache"] = "true"
                    if css_include:
                        headers["X-Target-Selector"] = css_include
                    
                    # Jina Reader request (dodajemy r.jina.ai/)
                    jina_url = f"https://r.jina.ai/{url}"
                    response = requests.get(jina_url, headers=headers)
                    if response.status_code == 200:
                        content = response.json().get('data', {}).get('content', response.text)
                        
                        # Tutaj wywołanie OpenAI API do analizy produktu
                        prompt = f"""
                        Jesteś ekspertem SEO i farmacji/kosmetyki. Przeanalizuj treść opisu produktu ze strony internetowej.
                        Strona: {url}
                        Treść strony:
                        {content[:4000]} # Limitujemy znaki dla oszczędności tokenów i kontekstu
                        
                        Zadanie:
                        1. Jaki problem medyczny/kosmetyczny ten produkt rozwiązuje?
                        2. Jakie ma ograniczenia (np. od jakiego wieku można go stosować)?
                        3. Co może powodować dane schorzenie i dla kogo ten produkt jest? (Zastanów się szerzej nad przyczynami dolegliwości)
                        4. Wygeneruj max 10 najważniejszych fraz kluczowych (seed keywords, od 1 do 3 słów), które wprost dotyczą problemu i rozwiązania. Odpowiedź wypisz tylko jako listę fraz po przecinku.
                        
                        Zwróć odpowiedź w formacie czytelnym dla człowieka z wyróżnieniem powyższych punktów.
                        W punkcie 4 napisz TYLKO: "FRAZY BAZOWE: fraza 1, fraza 2, fraza 3".
                        """
                        client = openai.OpenAI(api_key=openai_api_key)
                        ai_response = client.chat.completions.create(
                            model=st.session_state.selected_model,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        result = ai_response.choices[0].message.content
                        
                        # Prosta ekstrakcja fraz za pomocą Regex z odpowiedzi:
                        phrases = []
                        match = re.search(r"FRAZY BAZOWE:(.*)", result, re.IGNORECASE)
                        if match:
                            raw_phrases = match.group(1).split(",")
                            phrases = [p.strip().lower() for p in raw_phrases if p.strip()]
                            
                        product_analysis.append({
                            "url": url,
                            "analysis": result,
                            "seed_keywords": phrases
                        })
                    else:
                        st.error(f"Błąd pobierania strony {url}: {response.status_code}")
                except Exception as e:
                    st.error(f"Błąd analizy {url}: {e}")
                    
                my_bar.progress((idx + 1) / len(urls), text=f"Przeanalizowano {idx+1} z {len(urls)} produktów.")
                
            st.session_state.product_analysis = product_analysis
            st.success("Analiza zakończona!")
            
    # Wyświetlanie wyników z sesji
    if "product_analysis" in st.session_state:
        st.subheader("Wyniki Analizy AI")
        for item in st.session_state.product_analysis:
            with st.expander(item["url"]):
                st.markdown(item["analysis"])

# ================================
# KROK 3: Generowanie Fraz
# ================================
elif st.session_state.step == 3:
    st.header("Krok 3: Ostateczna Lista Fraz do Ahrefs")
    
    if "product_analysis" not in st.session_state or "df_domain" not in st.session_state:
        st.info("Wykonaj najpierw Krok 1 (wgranie danych domeny) i Krok 2 (analiza produktów).")
    else:
        # Zbieramy frazy z punktu 5 (od AI)
        ai_phrases = []
        for item in st.session_state.product_analysis:
            ai_phrases.extend(item.get("seed_keywords", []))
            
        ai_phrases_set = set(ai_phrases)
        
        # Pobieramy frazy z pliku domenowego
        domain_phrases = st.session_state.df_domain["keyword"].dropna().tolist()
        domain_phrases_set = set(str(p).lower().strip() for p in domain_phrases)
        
        # Łączymy
        all_phrases_set = ai_phrases_set.union(domain_phrases_set)
        
        st.write(f"Ilość fraz wygenerowanych przez AI: {len(ai_phrases_set)}")
        st.write(f"Ilość fraz domenowych z plików: {len(domain_phrases_set)}")
        st.write(f"Łącznie po deduplikacji: {len(all_phrases_set)}")
        
        text_to_copy = "\n".join(sorted(list(all_phrases_set)))
        
        st.text_area("Skopiuj te frazy do Ahrefs (Matching Terms):", text_to_copy, height=300)
        # Niestety kopiowanie do schowka z czystego streamlita po stronie usera (przycisk) działa słabo,
        # textarea jest najlepsze bo pozwala na Ctrl+A, Ctrl+C. Można ew. użyć streamlit-clipboard, 
        # ale na razie textarea to bezpieczny standard.

# ================================
# KROK 4: Mapowanie Content Gap
# ================================
elif st.session_state.step == 4:
    st.header("Krok 4: Mapowanie Content Gap (Non-Brand)")
    
    st.markdown("Wgraj plik wyeksportowany z Ahrefs: **Traffic share -> By page** (czyli adresy url i tytuły innych domen na bazie zbadanych wcześniej fraz).")
    
    gap_file = st.file_uploader("Wgraj plik z Ahrefs (CSV UTF-16LE z Top Pages/Traffic share)", type=['csv'])
    
    if st.button("Rozpocznij Dopasowywanie AI", type="primary"):
        if gap_file and "product_analysis" in st.session_state:
            with st.spinner("Parsowanie pliku..."):
                try:
                    df_gap = pd.read_csv(gap_file, encoding="utf-16le", sep="\t")
                except:
                    gap_file.seek(0)
                    df_gap = pd.read_csv(gap_file)
                
                # Upewniamy się, że są odpowiednie kolumny np. "URL" oraz "Title"
                if "URL" not in df_gap.columns:
                    st.error("Plik nie zawiera kolumny 'URL'.")
                else:
                    st.success(f"Wczytano {len(df_gap)} stron do analizy. Uruchamiam AI w trybie paczkowym (batching)...")
                    
                    # Przygotowanie kontekstu o produktach
                    products_context = "Lista naszych produktów wraz z analizą:\n"
                    for item in st.session_state.product_analysis:
                        products_context += f"- Produkt: {item['url']}\n  Analiza: {item['analysis']}\n\n"
                        
                    progress_text = "Analiza stron konkurencji..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    results = []
                    client = openai.OpenAI(api_key=openai_api_key)
                    
                    # Iterujemy po adresach, aby nie przekroczyć context window ani nie dostać timeouta.
                    # Z racji że proces może trwać długo, przy wielu tysiącach limitów może zbraknąć, ale user jest tego świadom.
                    for idx, row in df_gap.iterrows():
                        target_url = row.get("URL", "")
                        target_title = row.get("Title", "")
                        
                        prompt = f"""
                        Zadanie: Analiza Content Gap.
                        Oto URL obcej strony: {target_url}
                        Oto jej Tytuł (Title): {target_title}
                        
                        Oto produkty, które klient sprzedaje:
                        {products_context}
                        
                        Oceń, czy temat tej strony konkurencji nadaje się na wpis blogowy na naszej stronie, który mógłby wprost kierować do naszego produktu.
                        Jeśli NIE nadaje się (jest to np. e-sklep bez bloga, temat zupełnie z innej beczki, lub nie mamy do tego odpowiedniego produktu), odpowiedz jednym słowem: ODRZUCAM.
                        Jeśli nadaje się na poradnik, napisz: 
                        ZAAKCEPTOWANO
                        Zaproponowany Produkt: [Adres URL naszego produktu z podanej listy]
                        Dlaczego powiązano: [Krótki powód w jednym zdaniu]
                        """
                        try:
                            ai_response = client.chat.completions.create(
                                model=st.session_state.selected_model,
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=150
                            )
                            ans = ai_response.choices[0].message.content.strip()
                            if "ODRZUCAM" not in ans.upper():
                                results.append({
                                    "Competitor URL": target_url,
                                    "Competitor Title": target_title,
                                    "AI Verdict": ans
                                })
                        except Exception as e:
                            st.warning(f"Błąd OpenAI przy wierszu {idx}: {e}")
                            
                        my_bar.progress((idx + 1) / len(df_gap), text=f"Przeanalizowano {idx+1}/{len(df_gap)} wierszy.")
                    
                    if results:
                        df_results = pd.DataFrame(results)
                        st.session_state.df_gap_results = df_results
                        st.success("Analiza zakończona! Poniżej przefiltrowane wyniki:")
                        st.dataframe(df_results)
                    else:
                        st.warning("Żaden z adresów nie został dopasowany do naszych produktów.")
        else:
            st.warning("Upewnij się, że wgrałeś plik oraz że w Kroku 2 zostały przeanalizowane produkty.")

# ================================
# KROK 5: Analiza Brandu
# ================================
elif st.session_state.step == 5:
    st.header("Krok 5: Analiza Brandu")
    
    st.markdown("Wgraj pliki zawierające zapytania brandowe, czyli to, co użytkownicy wyszukują wokół nazwy Twojej marki/produktu (np. z Ahrefs i Senuto).")
    
    col1, col2 = st.columns(2)
    with col1:
        brand_ahrefs = st.file_uploader("Brand Keywords Ahrefs (CSV)", type=['csv'])
    with col2:
        brand_senuto = st.file_uploader("Brand Keywords Senuto (XLSX)", type=['xlsx', 'xls'])
        
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
            
            # OpenAI Analysis - batching zapytań, bo może być dużo. Pakujemy np. po 100 fraz.
            all_brand_ideas = ""
            client = openai.OpenAI(api_key=openai_api_key)
            
            chunk_size = 100
            chunks = [unique_kws[i:i + chunk_size] for i in range(0, len(unique_kws), chunk_size)]
            
            my_bar = st.progress(0, text="Analiza zapytań brandowych...")
            for i, chunk in enumerate(chunks):
                prompt = f"""
                Oto lista zapytań użytkowników zawierających nazwę brandu/produktu klienta:
                {chunk}
                
                Zadanie:
                Pogrupuj te zapytania na klastry intencji (np. Pytania o stosowanie, Skutki uboczne, Wiek dziecka, Opinie).
                Zaproponuj 3 gotowe tematy poradnikowe na bloga, które zbiorą ruch z tych zapytań i najlepiej na nie odpowiedzą.
                Zwróć wynik w ładnym formacie markdown (Tytuł klastra, frazy, sugerowane artykuły).
                """
                try:
                    ai_response = client.chat.completions.create(
                        model=st.session_state.selected_model,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    all_brand_ideas += ai_response.choices[0].message.content + "\n\n---\n\n"
                except Exception as e:
                    st.warning(f"Błąd OpenAI przy paczce {i+1}: {e}")
                
                my_bar.progress((i + 1) / len(chunks), text=f"Przeanalizowano paczkę {i+1}/{len(chunks)}.")
            
            st.success("Kategoryzacja zakończona!")
            st.markdown(all_brand_ideas)
        else:
            st.warning("Nie załadowano żadnych poprawnych plików z frazami brandowymi.")
