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
    # (Wybór modelu usunięty stąd - przeniesiony do konkretnych kroków)
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

# Funkcja pomocnicza: eksport do Excela (XLSX)
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

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
                    # Ahrefs kolumny do pozostawienia i zmiany nazwy
                    ahrefs_cols_to_keep = ["Keyword", "Volume", "Organic traffic", "Current position", "Current URL"]
                    avail_ahrefs = [c for c in ahrefs_cols_to_keep if c in df_ahrefs.columns]
                    df_a_clean = df_ahrefs[avail_ahrefs].copy()
                    
                    df_a_clean = df_a_clean.rename(columns={
                        "Keyword": "Keyword",
                        "Volume": "Volume",
                        "Organic traffic": "Traffic",
                        "Current position": "Position",
                        "Current URL": "URL"
                    })
                    if "URL" in df_a_clean.columns:
                        df_a_clean["URL_Norm"] = df_a_clean["URL"].apply(normalize_url)
                    else:
                        df_a_clean["URL_Norm"] = ""
                    
                    for col in ["Volume", "Traffic", "Position"]:
                        if col in df_a_clean.columns:
                            df_a_clean[col] = pd.to_numeric(df_a_clean[col], errors='coerce')
                    
                    df_a_agg = df_a_clean.groupby("URL_Norm").agg(
                        Ahrefs_Keywords=("Keyword", lambda x: ", ".join(x.dropna().astype(str))),
                        Ahrefs_Volume=("Volume", "sum"),
                        Ahrefs_Traffic=("Traffic", "sum"),
                        Ahrefs_Top_Position=("Position", "min")
                    ).reset_index()
                    
                    # Senuto kolumny do pozostawienia i zmiany nazwy
                    senuto_cols_map = {
                        "Słowo kluczowe": "Keyword",
                        "Śr. mies. liczba wyszukiwań": "Volume",
                        "Śr. mies. liczba wyszukiwani": "Volume", # na wypadek różnej pisowni
                        "Szacowany ruch": "Traffic",
                        "Pozycja": "Position",
                        "Adres URL": "URL"
                    }
                    avail_senuto = [c for c in df_senuto.columns if c in senuto_cols_map]
                    df_s_clean = df_senuto[avail_senuto].copy()
                    df_s_clean = df_s_clean.rename(columns=senuto_cols_map)
                    
                    if "URL" in df_s_clean.columns:
                        df_s_clean["URL_Norm"] = df_s_clean["URL"].apply(normalize_url)
                    else:
                        df_s_clean["URL_Norm"] = ""
                        
                    for col in ["Volume", "Traffic", "Position"]:
                        if col in df_s_clean.columns:
                            df_s_clean[col] = pd.to_numeric(df_s_clean[col], errors='coerce')
                            
                    df_s_agg = df_s_clean.groupby("URL_Norm").agg(
                        Senuto_Keywords=("Keyword", lambda x: ", ".join(x.dropna().astype(str))),
                        Senuto_Volume=("Volume", "sum"),
                        Senuto_Traffic=("Traffic", "sum"),
                        Senuto_Top_Position=("Position", "min")
                    ).reset_index()
                    
                    # Konsolidacja obu tabel (Outer Join po URL)
                    df_combined = pd.merge(df_s_agg, df_a_agg, on="URL_Norm", how="outer")
                    df_combined = df_combined.rename(columns={"URL_Norm": "URL"})
                    
                    # Zabezpieczenie kolejności kolumn (URL na początku)
                    cols = ["URL"] + [c for c in df_combined.columns if c != "URL"]
                    df_combined = df_combined[cols]
                    
                    # Usuwanie pustych adresów URL (oraz NaN)
                    df_combined = df_combined.dropna(subset=["URL"])
                    df_combined = df_combined[df_combined["URL"].astype(str).str.strip() != ""]
                    
                    st.session_state.df_domain = df_combined
                    
                    # Generowanie rozszerzonej (niepogrupowanej) wersji tabeli
                    df_a_raw = df_a_clean.copy()
                    df_a_raw["Source"] = "Ahrefs"
                    df_s_raw = df_s_clean.copy()
                    df_s_raw["Source"] = "Senuto"
                    
                    df_unpivoted = pd.concat([df_a_raw, df_s_raw], ignore_index=True)
                    
                    # Usuwamy oryginalną kolumnę URL aby uniknąć duplikatów przy zmianie nazwy
                    if "URL" in df_unpivoted.columns:
                        df_unpivoted = df_unpivoted.drop(columns=["URL"])
                        
                    df_unpivoted = df_unpivoted.rename(columns={"URL_Norm": "URL"})
                    
                    df_unpivoted = df_unpivoted.dropna(subset=["URL", "Keyword"])
                    df_unpivoted = df_unpivoted[df_unpivoted["URL"].astype(str).str.strip() != ""]
                    
                    # Deduplikacja po URL i Keyword
                    df_unpivoted["kw_lower"] = df_unpivoted["Keyword"].astype(str).str.lower()
                    df_unpivoted = df_unpivoted.drop_duplicates(subset=["kw_lower", "URL"])
                    df_unpivoted = df_unpivoted.drop(columns=["kw_lower"])
                    
                    # Zabezpieczenie kolejności
                    u_cols = ["URL", "Keyword", "Volume", "Traffic", "Position", "Source"]
                    u_cols = [c for c in u_cols if c in df_unpivoted.columns]
                    df_unpivoted = df_unpivoted[u_cols]
                    
                    st.session_state.df_unpivoted = df_unpivoted
                    
                    st.success("Pliki zostały skonsolidowane! Wyniki zebrane po adresie URL.")
                    
                    tab1, tab2 = st.tabs(["Widok Pogrupowany (URL)", "Widok Rozszerzony (Frazy)"])
                    
                    with tab1:
                        st.dataframe(df_combined.head(100)) # Podgląd pierwszych 100 wyników
                        st.download_button(
                            label="📥 Pobierz Widok Pogrupowany (XLSX)",
                            data=to_excel(df_combined),
                            file_name='skonsolidowane_frazy_grupy.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                        
                    with tab2:
                        st.dataframe(df_unpivoted.head(100))
                        st.download_button(
                            label="📥 Pobierz Widok Rozszerzony (XLSX)",
                            data=to_excel(df_unpivoted),
                            file_name='skonsolidowane_frazy_rozszerzone.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
        else:
            st.warning("Proszę wgrać oba pliki (Ahrefs i Senuto).")

# ================================
# KROK 2: Analiza Produktów
# ================================
elif st.session_state.step == 2:
    st.header("Krok 2: Analiza Produktów (Jina Reader + AI)")
    
    product_urls_text = st.text_area("Wklej adresy URL produktów klienta (po jednym w linii):", height=150)
    
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
        
        def_user_2 = """Przeanalizuj treść opisu produktu ze strony internetowej.
Strona: {url}
Treść strony:
{content}

Zadanie:
Musisz zwrócić odpowiedź jako poprawny obiekt JSON.
Struktura JSON ma wyglądać następująco:
{
  "problem": "Opisz krótko jaki problem medyczny/kosmetyczny ten produkt rozwiązuje",
  "ograniczenia": "Opisz ograniczenia (np. wiek, przeciwwskazania)",
  "przyczyny": "Co powoduje schorzenie i dla kogo produkt jest przeznaczony?",
  "seed_keywords": ["fraza 1", "fraza 2"] // max 10 najważniejszych fraz (od 1 do 3 słów)
}"""
        step2_user = st.text_area("User Prompt (użyj {url} i {content})", value=def_user_2, height=300, key="step2_user")
        
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
                        
                        # Jina Reader request (dodajemy r.jina.ai/)
                        jina_url = f"https://r.jina.ai/{url}"
                        response = requests.get(jina_url, headers=headers)
                        if response.status_code == 200:
                            content = response.json().get('data', {}).get('content', response.text)
                        else:
                            st.error(f"Błąd pobierania strony {url}: {response.status_code}")
                            continue
                        
                    if content:
                        # Tutaj wywołanie OpenAI API do analizy produktu
                        prompt = step2_user.replace("{url}", url).replace("{content}", content[:4000])
                        
                        client = openai.OpenAI(api_key=openai_api_key)
                        ai_response = client.chat.completions.create(
                            model=step2_model,
                            temperature=step2_temp,
                            max_tokens=step2_tokens,
                            response_format={ "type": "json_object" },
                            messages=[
                                {"role": "system", "content": step2_sys},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        result = ai_response.choices[0].message.content
                        
                        import json
                        try:
                            data = json.loads(result)
                            analysis_text = f"**Problem:** {data.get('problem', '')}\n\n**Ograniczenia:** {data.get('ograniczenia', '')}\n\n**Przyczyny:** {data.get('przyczyny', '')}"
                            raw_phrases = data.get('seed_keywords', [])
                            phrases = [str(p).replace('*', '').strip().lower() for p in raw_phrases if str(p).strip()]
                        except Exception as e:
                            analysis_text = result
                            phrases = []
                            st.warning(f"Nie udało się sparsować JSON dla {url}: {e}")
                            
                        product_analysis.append({
                            "url": url,
                            "analysis": analysis_text,
                            "seed_keywords": phrases
                        })
                        })
                    else:
                        st.warning(f"Brak zawartości do analizy dla {url}")
                except Exception as e:
                    st.error(f"Błąd analizy {url}: {e}")
                    
                my_bar.progress((idx + 1) / len(items_to_analyze), text=f"Przeanalizowano {idx+1} z {len(items_to_analyze)} produktów.")
                
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
        domain_phrases = []
        if "df_unpivoted" in st.session_state:
            domain_phrases = st.session_state.df_unpivoted["Keyword"].dropna().tolist()
        else:
            # Fallback jeśli df_unpivoted nie istnieje z jakiegoś powodu
            if "Senuto_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Senuto_Keywords"].dropna():
                    domain_phrases.extend([k.strip() for k in str(kws).split(",") if k.strip()])
            if "Ahrefs_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Ahrefs_Keywords"].dropna():
                    domain_phrases.extend([k.strip() for k in str(kws).split(",") if k.strip()])
                    
        domain_phrases_set = set(str(p).replace('*', '').lower().strip() for p in domain_phrases)
        
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
                            # Próba formatu Ahrefs
                            df_gap = pd.read_csv(gap_file, encoding="utf-16le", sep="\t")
                            if len(df_gap.columns) <= 1:
                                raise ValueError("To nie jest plik rozdzielany tabulatorem")
                        except:
                            # Fallback do zwykłego CSV przecinkowego
                            gap_file.seek(0)
                            df_gap = pd.read_csv(gap_file)
                except Exception as e:
                    st.error(f"Nie udało się odczytać pliku: {e}")
                    df_gap = pd.DataFrame()
                
                # Upewniamy się, że są odpowiednie kolumny np. "URL" oraz "Title"
                if "URL" not in df_gap.columns:
                    st.error("Plik nie zawiera kolumny 'URL'.")
                else:
                    # Deduplikacja po Top keyword przed analizą
                    if "Top keyword" in df_gap.columns:
                        if "Traffic" in df_gap.columns:
                            df_gap["Traffic"] = pd.to_numeric(df_gap["Traffic"], errors='coerce')
                            df_gap = df_gap.sort_values(by="Traffic", ascending=False)
                        df_gap = df_gap.drop_duplicates(subset=["Top keyword"], keep="first")
                        
                    st.success(f"Wczytano {len(df_gap)} unikalnych stron (po deduplikacji) do analizy. Uruchamiam AI w trybie paczkowym...")
                    
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
                                uzasadnienie = data.get("uzasadnienie", "")
                                
                                if "ZAAKCEPTOWANO" in ocena:
                                    results.append({
                                        "Competitor URL": target_url,
                                        "Competitor Title": target_title,
                                        "Recommended Product": produkt,
                                        "Reasoning": uzasadnienie,
                                        "AI Verdict": ocena
                                    })
                            except:
                                if "ZAAKCEPTOWANO" in ans.upper():
                                    results.append({
                                        "Competitor URL": target_url,
                                        "Competitor Title": target_title,
                                        "Recommended Product": "Błąd JSON",
                                        "Reasoning": ans,
                                        "AI Verdict": "ZAAKCEPTOWANO"
                                    })
                        except Exception as e:
                            st.warning(f"Błąd OpenAI przy wierszu {idx}: {e}")
                            
                        my_bar.progress((idx + 1) / len(df_gap), text=f"Przeanalizowano {idx+1}/{len(df_gap)} wierszy.")
                    
                    if results:
                        df_results = pd.DataFrame(results)
                        st.session_state.df_gap_results = df_results
                        st.success("Analiza zakończona! Poniżej przefiltrowane wyniki:")
                        st.dataframe(df_results)
                        
                        st.download_button(
                            label="📥 Pobierz wyniki Gap (XLSX)",
                            data=to_excel(df_results),
                            file_name='content_gap_wyniki.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
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
            
            # OpenAI Analysis - batching zapytań, bo może być dużo. Pakujemy np. po 100 fraz.
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
