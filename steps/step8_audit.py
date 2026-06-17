import streamlit as st
import pandas as pd
import requests
import openai
from utils.helpers import to_excel
import json

def render(openai_api_key):
    st.header("Krok 8: Audyt Contentu (AI Readiness)")
    st.markdown("Wgraj plik (np. XLSX lub CSV) z listą adresów URL do zaudytowania. Skrypt wejdzie na każdą podstronę, pobierze jej zawartość i oceni ją pod kątem 12 rygorystycznych kryteriów.")
    
    audit_file = st.file_uploader("Wgraj plik z URLami do audytu (kolumny: URL, opcjonalnie Keyword, Title, H1)", type=['csv', 'xlsx', 'xls'])
    
    with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-5.5", "gpt-5.4-mini", "o1-mini", "o3-mini"]
        
        template_8 = st.radio("Szablon Ustawień (Audyt):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: medium, temp: 0.1)"], key="template_8")
        if template_8 == "Domyślny (Ręczne parametry)":
            step8_model = st.selectbox("Wybierz model OpenAI:", models, index=0, key="step8_model")
            col1, col2 = st.columns(2)
            with col1:
                step8_temp = st.slider("Temperatura", 0.0, 2.0, 0.7, 0.1, key="step8_temp")
            with col2:
                step8_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step8_tokens")
            params_8 = {"model": step8_model, "temperature": step8_temp, "max_tokens": step8_tokens}
        else:
            st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=0.1, reasoning_effort=medium.")
            params_8 = {"model": "gpt-5.4-mini", "temperature": 0.1, "reasoning_effort": "medium"}
        
        step8_sys_def = """Jesteś ekspertem SEO, redaktorem naczelnym, content strategistą i rygorystycznym audytorem treści dla serwisów medycznych, kosmetycznych, dermokosmetycznych, OTC i e-commerce.

Twoim zadaniem jest szczegółowa ocena jakości treści pod kątem SEO, intencji użytkownika, rzetelności, wiarygodności, struktury, użyteczności i potencjału sprzedażowego.

Oceniasz wyłącznie na podstawie dostarczonej treści i kontekstu. Nie zakładaj, że na stronie znajdują się elementy, których nie ma w zeskrapowanej treści. Jeśli zeskrapowana treść nie zawiera informacji o linkach, pogrubieniach, listach lub FAQ, traktuj to jako brak dowodu i oceń konserwatywnie.

Zwracasz wyłącznie poprawny obiekt JSON. Nie dodawaj markdowna, komentarzy ani tekstu poza JSON-em.

Skala statusów:
"Dobry": Kryterium jest spełnione dobrze. Treść realnie pomaga użytkownikowi, jest konkretna, logiczna i nie wymaga istotnych zmian.
"Średni": Kryterium jest częściowo spełnione. Treść ma poprawny kierunek, ale wymaga rozbudowy, doprecyzowania, lepszej struktury albo mocniejszych przykładów.
"Do poprawy": Kryterium jest słabo spełnione. Treść zawiera istotne braki, ogólniki, niepełne odpowiedzi albo nie wykorzystuje potencjału SEO.
"Brak": Nie ma widocznych elementów spełniających dane kryterium albo dostarczona treść nie pozwala potwierdzić ich obecności.

Zasady audytu:
1. Oceniaj rygorystycznie, ale praktycznie.
2. Nie dawaj statusu "Dobry", jeśli treść jest tylko poprawna, ale powierzchowna.
3. Dla każdego kryterium podaj konkretną rekomendację: co dodać, usunąć, rozbudować albo zmienić.
4. Rekomendacja ma być operacyjna, możliwa do wdrożenia przez copywritera, SEO-wca lub redaktora.
5. Nie pisz ogólników typu "warto poprawić treść". Wskaż, co dokładnie poprawić.
6. Jeżeli tekst dotyczy zdrowia, skóry, leczenia, objawów, dzieci, ciąży, leków, ran, infekcji lub przeciwwskazań, szczególnie oceniaj wiarygodność, źródła i bezpieczeństwo komunikacji.
7. Nie sugeruj dodawania claimów medycznych, których nie da się bezpiecznie uzasadnić.
8. Jeśli brakuje źródeł medycznych, eksperta, daty aktualizacji lub informacji o autorze, uwzględnij to w kryteriach wiarygodności i odświeżania.
9. Jeśli artykuł ma potencjał do sprzedaży produktu, oceniaj też, czy naturalnie linkuje do produktu lub odpowiada na problem użytkownika.
10. Jeżeli treść jest krótka, ogólna albo nie wyczerpuje tematu, obniż ocenę w kryteriach: dokładność, rozbudowa, fragmentacja i styl.
11. Jeżeli z treści nie da się ustalić domyślnego zapytania użytkownika, wywnioskuj je ostrożnie z URL-a, title, H1 i głównego tematu.
12. Jeżeli dane wejściowe nie zawierają title, H1, keywordu lub kontekstu produktów, nie wymyślaj ich. Wpisz null albo oprzyj ocenę na dostępnej treści."""
        step8_sys = st.text_area("System Prompt", value=step8_sys_def, height=300, key="step8_sys")
        
        user_8_def = """Audyt Contentu.

Dane strony:
URL analizowanej strony: {target_url}
Opcjonalny główny keyword lub zapytanie użytkownika: {target_keyword}
Opcjonalny title strony: {page_title}
Opcjonalny H1 strony: {page_h1}

Opcjonalny kontekst produktów klienta:
{products_context}

Zeskrapowana treść strony:
{content}

Zadanie:
Przeprowadź rygorystyczny audyt powyższej treści według 12 kryteriów.
Dla każdego kryterium:
* przypisz status: "Dobry", "Średni", "Do poprawy" albo "Brak",
* podaj krótką, konkretną rekomendację wdrożeniową,
* wskaż główny problem lub brak,
* określ priorytet poprawy: "wysoki", "średni" albo "niski".

Kryteria oceny:
1. trafnosc: Czy treść odpowiada na domyślne zapytanie użytkownika? Czy rozwiązuje główny problem?
2. dokladnosc: Czy treść jest konkretna, rzetelna i merytoryczna?
3. wiarygodnosc: Czy budzi zaufanie? Autor, ekspert, bibliografia, data, linki.
4. autorytet: Czy wzmacnia topical authority serwisu? Powiązania z objawami, przyczynami itp.
5. linkowanie: Czy występuje sensowne linkowanie wewnętrzne do produktów, powiązanych poradników?
6. odswiezanie: Czy treść wygląda na aktualną?
7. rozbudowa: Czy artykuł wyczerpuje temat?
8. styl: Czy styl jest dopasowany do intencji?
9. fragmentacja: Czy akapity funkcjonują jako samodzielne fragmenty, definicje łatwe do cytowania?
10. faq: Czy istnieje sekcja FAQ?
11. pogrubienia: Czy pomagają skanować treść?
12. listy: Czy tekst zawiera listy organizujące wiedzę?

Zwróć wyłącznie poprawny JSON w strukturze:
{
"meta": {
"url": "{target_url}",
"domyslna_intencja": "informacyjna | poradnikowa | produktowa | transakcyjna | porownawcza | niejasna",
"domyslny_problem_uzytkownika": "",
"typ_tresci": "artykul_poradnikowy | strona_produktu | kategoria | landing | faq | inny | niejasne",
"ocena_ogolna": "Dobry | Średni | Do poprawy | Brak",
"najwiekszy_problem": "",
"najwieksza_szansa": ""
},
"audyt": {
"trafnosc": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"dokladnosc": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"wiarygodnosc": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"autorytet": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"linkowanie": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"odswiezanie": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"rozbudowa": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"styl": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"fragmentacja": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"faq": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"pogrubienia": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" },
"listy": { "status": "Dobry | Średni | Do poprawy | Brak", "problem_lub_brak": "", "rekomendacja": "", "priorytet": "wysoki | średni | niski" }
},
"priorytetowe_dzialania": [ {"kolejnosc": 1, "dzialanie": "", "obszar": "trafnosc...", "uzasadnienie": ""} ],
"szybkie_poprawki": [ {"poprawka": "", "efekt": ""} ],
"ryzyka": [ {"ryzyko": "", "jak_ograniczyc": ""} ]
}"""
        step8_user = st.text_area("User Prompt", value=user_8_def, height=400, key="step8_user")

    if st.button("Rozpocznij Audyt AI", type="primary"):
        if audit_file:
            try:
                if audit_file.name.endswith('.csv'):
                    df_audit = pd.read_csv(audit_file)
                else:
                    df_audit = pd.read_excel(audit_file)
                    
                url_col = next((c for c in df_audit.columns if 'url' in str(c).lower()), df_audit.columns[0])
                k_col = next((c for c in df_audit.columns if 'keyword' in str(c).lower() or 'fraza' in str(c).lower()), None)
                t_col = next((c for c in df_audit.columns if 'title' in str(c).lower() or 'tytuł' in str(c).lower()), None)
                h1_col = next((c for c in df_audit.columns if 'h1' in str(c).lower()), None)
                
                products_context = "Lista naszych produktów:\n"
                if "product_analysis" in st.session_state:
                    for item in st.session_state.product_analysis:
                        products_context += f"- Produkt: {item['url']}\n  Analiza: {item['analysis']}\n\n"
                        
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
                        
                    t_kw = str(row.get(k_col, "")) if k_col else ""
                    t_ti = str(row.get(t_col, "")) if t_col else ""
                    t_h1 = str(row.get(h1_col, "")) if h1_col else ""
                        
                    jina_url = f"https://r.jina.ai/{target_url}"
                    response = requests.get(jina_url, headers=headers)
                    if response.status_code == 200:
                        content = response.json().get('data', {}).get('content', response.text)
                    else:
                        st.error(f"Błąd pobierania {target_url}")
                        continue
                        
                    content_clipped = content[:40000]
                    
                    prompt = step8_user.replace("{target_url}", target_url).replace("{target_keyword}", t_kw).replace("{page_title}", t_ti).replace("{page_h1}", t_h1).replace("{products_context}", products_context).replace("{content}", content_clipped)
                    
                    try:
                        call_kwargs = {
                            "model": params_8["model"],
                            "response_format": { "type": "json_object" },
                            "messages": [
                                {"role": "system", "content": step8_sys},
                                {"role": "user", "content": prompt}
                            ]
                        }
                        if "temperature" in params_8: call_kwargs["temperature"] = params_8["temperature"]
                        if "max_tokens" in params_8: call_kwargs["max_tokens"] = params_8["max_tokens"]
                        if "reasoning_effort" in params_8: call_kwargs["reasoning_effort"] = params_8["reasoning_effort"]
                            
                        ai_response = client.chat.completions.create(**call_kwargs)
                        ans = ai_response.choices[0].message.content.strip()
                        
                        try:
                            data = json.loads(ans)
                            row_dict = row.to_dict()
                            
                            meta = data.get("meta", {})
                            row_dict["Ocena Ogólna"] = meta.get("ocena_ogolna", "")
                            row_dict["Domyślna Intencja"] = meta.get("domyslna_intencja", "")
                            row_dict["Domyślny Problem"] = meta.get("domyslny_problem_uzytkownika", "")
                            row_dict["Największy Problem"] = meta.get("najwiekszy_problem", "")
                            row_dict["Największa Szansa"] = meta.get("najwieksza_szansa", "")
                            
                            audyt = data.get("audyt", {})
                            keys_to_extract = ["trafnosc", "dokladnosc", "wiarygodnosc", "autorytet", "linkowanie", "odswiezanie", "rozbudowa", "styl", "fragmentacja", "faq", "pogrubienia", "listy"]
                            
                            for k in keys_to_extract:
                                k_data = audyt.get(k, {})
                                row_dict[f"{k.capitalize()} - Status"] = k_data.get("status", "")
                                row_dict[f"{k.capitalize()} - Priorytet"] = k_data.get("priorytet", "")
                                row_dict[f"{k.capitalize()} - Problem"] = k_data.get("problem_lub_brak", "")
                                row_dict[f"{k.capitalize()} - Rekomendacja"] = k_data.get("rekomendacja", "")
                                
                            row_dict["Priorytetowe Działania"] = json.dumps(data.get("priorytetowe_dzialania", []), ensure_ascii=False)
                            row_dict["Szybkie Poprawki"] = json.dumps(data.get("szybkie_poprawki", []), ensure_ascii=False)
                            row_dict["Ryzyka"] = json.dumps(data.get("ryzyka", []), ensure_ascii=False)
                                
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
                        
                    progress_value = min(1.0, (idx + 1) / len(df_audit))
                    my_bar.progress(progress_value, text=f"Zaudytowano {idx+1}/{len(df_audit)}")
                
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
