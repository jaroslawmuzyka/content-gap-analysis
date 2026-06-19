import streamlit as st
import pandas as pd
import openai
import os
from utils.helpers import to_excel

def render(openai_api_key):
    st.header("Krok 7: Weryfikacja Istniejących Treści")
    
    if "df_gap_results" not in st.session_state or "my_pages_df" not in st.session_state:
        st.warning("Musisz najpierw ukończyć Krok 4 (aby wygenerować pomysły Gap) oraz Krok 5 (aby wgrać własne URLe i Title).")
    else:
        df_gap = st.session_state.df_gap_results
        df_accepted = df_gap[df_gap['AI Verdict'] == "PASUJE"]
        df_my = st.session_state.my_pages_df
        
        st.info(f"Do weryfikacji mamy {len(df_accepted)} zaakceptowanych pomysłów na wpisy oraz {len(df_my)} własnych podstron.")
        
        # 1. Sprawdzanie czy istnieje plik awaryjny
        if os.path.exists("temp_verification_results_backup.xlsx"):
            st.warning("⚠️ Wykryto niezakończoną weryfikację z poprzedniej sesji!")
            try:
                with open("temp_verification_results_backup.xlsx", "rb") as f:
                    xlsx_backup = f.read()
                df_backup = pd.read_excel("temp_verification_results_backup.xlsx")
                st.download_button(
                    label=f"📥 Pobierz uratowane wyniki weryfikacji ({len(df_backup)} rekordów)",
                    data=xlsx_backup,
                    file_name="uratowane_wyniki_krok7.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Nie udało się wczytać pliku backupu: {e}")
                
        st.markdown("---")
        
        # 2. Wybór trybu pracy
        mode = st.radio(
            "Wybierz tryb pracy w Kroku 7:",
            ["Weryfikacja AI nowej listy", "Wznów analizę z częściowego/gotowego pliku XLSX"]
        )
        
        df_ready = None
        if mode == "Wznów analizę z częściowego/gotowego pliku XLSX":
            st.info("Wgraj plik (Excel lub CSV), który udało Ci się pobrać po przerwanej sesji. Narzędzie wczyta zrobione już pomysły i zweryfikuje tylko pozostałe, a na końcu połączy wyniki.")
            ready_file = st.file_uploader("Wgraj częściowy plik Weryfikacji", type=['csv', 'xlsx', 'xls'], key="ready_file_verification")
            if ready_file:
                try:
                    if ready_file.name.endswith('.csv'):
                        df_ready = pd.read_csv(ready_file)
                    else:
                        df_ready = pd.read_excel(ready_file)
                        
                    processed_urls = df_ready["Competitor URL"].dropna().unique() if "Competitor URL" in df_ready.columns else []
                    
                    df_accepted_urls = df_accepted["Competitor URL"].dropna().unique() if "Competitor URL" in df_accepted.columns else []
                    remaining = len(set(df_accepted_urls) - set(processed_urls))
                    
                    st.success(f"Pomyślnie wczytano plik! Wykryto {len(processed_urls)} przetworzonych pomysłów. Pozostało do weryfikacji: {remaining}")
                    st.dataframe(df_ready.head())
                    
                    if remaining <= 0:
                        if st.button("Zapisz te wyniki i przejdź dalej", type="primary"):
                            st.session_state.df_verified_results = df_ready
                            st.success("Zapisano! Wszystkie pomysły są zweryfikowane. Możesz przejść do kroku z raportami.")
                        return # Koniec rysowania, jeśli wszystko zrobione
                except Exception as e:
                    st.error(f"Błąd podczas wczytywania gotowego pliku: {e}")
        
        with st.expander("⚙️ Opcje AI (Model, Prompty, Parametry)"):
            models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-5.5", "gpt-5.4-mini", "o1-mini", "o3-mini"]
            
            template_7 = st.radio("Szablon Ustawień (Weryfikacja):", ["Domyślny (Ręczne parametry)", "Rekomendowany (gpt-5.4-mini, reasoning: low, temp: 1.0)"], key="template_7")
            if template_7 == "Domyślny (Ręczne parametry)":
                step7_model = st.selectbox("Wybierz model OpenAI:", models, index=models.index("gpt-5.4-mini") if "gpt-5.4-mini" in models else 0, key="step7_model")
                col1, col2 = st.columns(2)
                with col1:
                    step7_temp = st.slider("Temperatura", 0.0, 2.0, 1.0 if step7_model == "gpt-5.4-mini" else 0.7, 0.1, key="step7_temp")
                with col2:
                    step7_tokens = st.number_input("Max Tokens", 100, 16000, 4000, key="step7_tokens")
                params_7 = {"model": step7_model, "temperature": 1.0 if step7_model == "gpt-5.4-mini" else step7_temp, "max_tokens": step7_tokens}
            else:
                st.info("Zastosowano parametry rekomendowane: model=gpt-5.4-mini, temp=1.0, reasoning_effort=low.")
                params_7 = {"model": "gpt-5.4-mini", "temperature": 1.0, "reasoning_effort": "low"}
            
            sys_7_def = """Jesteś redaktorem naczelnym, strategiem SEO i specjalistą od architektury treści.

Twoim zadaniem jest ocena, czy nowy pomysł na wpis blogowy lub poradnikowy jest już obsłużony przez istniejące adresy URL na stronie klienta.

Nie oceniasz wyłącznie podobieństwa słów w tytule lub URL-u. Oceniasz przede wszystkim:
* intencję użytkownika,
* główny problem,
* segment tematyczny,
* zakres merytoryczny,
* potencjalną kanibalizację SEO,
* to, czy istniejącą treść lepiej rozbudować zamiast tworzyć nowy wpis.

Zasady oceny:
1. Zwróć wyłącznie poprawny obiekt JSON, zawierający klucz "results" będący tablicą wyników dla każdego przekazanego pomysłu.
2. Nie dodawaj komentarzy, markdowna ani tekstu poza JSON-em.
3. Nie zakładaj, że istniejąca strona opisuje temat, jeśli nie wynika to z jej URL-a, title, H1 lub opisu w dostarczonym kontekście.
4. Jeżeli masz tylko listę URL-i bez title/H1/opisów, oceniaj konserwatywnie.
5. Nie uznawaj tematu za opisany tylko dlatego, że istniejąca strona dotyczy podobnej kategorii.
6. Temat jest "OPISANE" tylko wtedy, gdy istniejąca strona prawdopodobnie odpowiada na tę samą intencję użytkownika i ten sam główny problem.
7. Temat jest "CZESCIOWO_OPISANE", jeśli istniejąca strona dotyczy podobnego problemu, ale brakuje konkretnego kąta, zastosowania, grupy odbiorców, sezonowości, przyczyny, skutku albo kontekstu wskazanego w pomyśle.
8. Temat jest "NIEOPISANE", jeśli nie ma istniejącej strony, która odpowiada na tę samą intencję i problem.
9. Jeżeli temat można bezpiecznie obsłużyć rozbudową istniejącej strony, rekomenduj rozbudowę zamiast nowego wpisu.
10. Jeżeli nowy wpis byłby bardzo podobny do istniejącego i mógłby powodować kanibalizację, ustaw wysokie ryzyko kanibalizacji.
11. Jeżeli istniejący URL to strona produktu, a pomysł jest poradnikowy, nie uznawaj automatycznie tematu za opisany. Oceń, czy lepsza będzie rozbudowa strony produktu, FAQ czy osobny artykuł.
12. Jeżeli istniejący artykuł dotyczy tego samego problemu, ale innej grupy odbiorców lub innego kontekstu, oznacz jako "CZESCIOWO_OPISANE".
13. Jeżeli pomysł dotyczy wąskiego zastosowania, sezonowości lub szczególnej przyczyny problemu, a istniejąca strona opisuje tylko ogólny problem, oznacz jako "CZESCIOWO_OPISANE".
14. Domyślnie unikaj tworzenia nowych treści, jeśli istniejący URL można rozbudować bez utraty intencji.
15. Rekomenduj nowy wpis tylko wtedy, gdy temat ma odrębną intencję, odrębny problem lub wyraźnie inny zakres niż istniejące strony."""
            step7_sys = st.text_area("System Prompt", value=sys_7_def, height=250, key="step7_sys")
            
            user_7_def = """Zadanie: mapowanie paczki nowych pomysłów contentowych do istniejących treści na stronie klienta.

Paczka pomysłów na nowe wpisy (lista obiektów):
{batch_data}

Lista istniejących adresów URL na stronie klienta:
{my_pages_context}

Cel:
Dla KAŻDEGO pomysłu z paczki sprawdź, czy wątek w nim opisany jest już realizowany przez któryś z istniejących adresów URL.

Nie chodzi o zwykłe podobieństwo słów. Oceń, czy istniejąca strona odpowiada na tę samą intencję użytkownika i ten sam problem.

Zwróć uwagę na:
* czy temat jest już w pełni opisany,
* czy jest opisany tylko częściowo,
* czy lepiej rozbudować istniejący URL,
* czy warto stworzyć nowy wpis,
* czy nowy wpis mógłby kanibalizować istniejącą stronę,
* który istniejący URL jest najlepszym dopasowaniem,
* czego brakuje na istniejącej stronie względem nowego pomysłu.

Definicje statusów:
"OPISANE": Istniejący URL prawdopodobnie odpowiada na tę samą intencję, ten sam problem i podobny zakres tematu. Nie należy tworzyć nowego wpisu.
"CZESCIOWO_OPISANE": Istniejący URL dotyczy podobnego problemu lub segmentu, ale nie pokrywa w pełni kąta zaproponowanego w nowym wpisie. Zwykle należy rozbudować istniejącą stronę, dodać sekcję, FAQ albo akapit.
"NIEOPISANE": Brak istniejącego URL-a, który odpowiada na tę samą intencję i problem. Można rozważyć stworzenie nowego wpisu.

Zwróć wyłącznie poprawny JSON o następującej strukturze:
{
  "results": [
    {
      "id": "identyfikator podany w batch_data",
      "status": "OPISANE | CZESCIOWO_OPISANE | NIEOPISANE",
      "decyzja": "NIE_TWORZ_NOWEGO_WPISU | ROZBUDUJ_ISTNIEJACY_URL | STWORZ_NOWY_WPIS | WYMAGA_RECZNEJ_WERYFIKACJI",
      "istniejacy_url": "najlepiej dopasowany istniejący URL albo pusty string",
      "dopasowanie": "pelne | czesciowe | luzne | brak | niejasne",
      "intencja_pomyslu": "informacyjna | poradnikowa | problemowa | produktowa | porownawcza | sezonowa | niejasna",
      "segment": "przepisany z batch_data segment pomysłu",
      "temat_pomyslu": "krótki opis głównego tematu pomysłu",
      "czy_grozi_kanibalizacja": true,
      "ryzyko_kanibalizacji": "wysokie | srednie | niskie | brak",
      "brakujacy_kat_lub_zakres": "co trzeba dodać, jeśli temat jest opisany tylko częściowo; pusty string, jeśli nie dotyczy",
      "rekomendowana_akcja": "krótka rekomendacja",
      "uzasadnienie": "jedno krótkie zdanie wyjaśniające ocenę"
    }
  ]
}"""
            step7_user = st.text_area("User Prompt", value=user_7_def, height=350, key="step7_user")
                
        if st.button("Rozpocznij Weryfikację AI", type="primary"):
            if len(df_accepted) == 0:
                st.warning("Nie masz żadnych Zaakceptowanych pomysłów z Kroku 4.")
            elif not openai_api_key:
                st.error("Brak klucza OpenAI.")
            else:
                df_accepted_to_process = df_accepted
                if df_ready is not None and "Competitor URL" in df_ready.columns:
                    processed_urls = df_ready["Competitor URL"].dropna().unique()
                    df_accepted_to_process = df_accepted[~df_accepted["Competitor URL"].isin(processed_urls)]
                    
                if len(df_accepted_to_process) == 0:
                    st.success("Wszystkie adresy zostały już przeanalizowane w załączonym pliku. Nie ma nic więcej do zrobienia!")
                    if df_ready is not None:
                        st.session_state.df_verified_results = df_ready
                    st.stop()
                my_pages_context = ""
                url_col = "URL" if "URL" in df_my.columns else ("Address" if "Address" in df_my.columns else df_my.columns[0])
                title_col = "Title 1" if "Title 1" in df_my.columns else ("Title" if "Title" in df_my.columns else ("Tytuł" if "Tytuł" in df_my.columns else None))
                
                for idx, row in df_my.iterrows():
                    u = str(row.get(url_col, ""))
                    t = str(row.get(title_col, "")) if title_col else ""
                    if u:
                        my_pages_context += f"- {u} (Title: {t})\n"
                        
                if len(my_pages_context) > 400000:
                    st.warning("Ostrzeżenie: Twoja lista własnych stron jest bardzo długa. Obcinam do pierwszych 400k znaków (ok. 4000 URLi), aby nie przekroczyć maksymalnego limitu 128 tys. tokenów dla modelu.")
                    my_pages_context = my_pages_context[:400000]
                
                progress_text = "Weryfikacja istnienia treści (Batching)..."
                my_bar = st.progress(0, text=progress_text)
                st.markdown("### Podgląd wyników weryfikacji na żywo:")
                table_placeholder = st.empty()
                
                results_verified = []
                client = openai.OpenAI(api_key=openai_api_key)
                
                import time
                import json
                batch_size = 10
                
                # Konwertujemy df_accepted_to_process do iteracji
                for i in range(0, len(df_accepted_to_process), batch_size):
                    batch = df_accepted_to_process.iloc[i:i+batch_size]
                    
                    batch_data_list = []
                    for idx, row in batch.iterrows():
                        batch_data_list.append({
                            "id": idx,
                            "target_url": str(row.get("Competitor URL", "")),
                            "target_title": str(row.get("Competitor Title", "")),
                            "segment": str(row.get("Segment", ""))
                        })
                        
                    batch_data_str = json.dumps(batch_data_list, ensure_ascii=False)
                    prompt = step7_user.replace("{batch_data}", batch_data_str).replace("{my_pages_context}", my_pages_context)
                    
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            call_kwargs = {
                                "model": params_7["model"],
                                "response_format": { "type": "json_object" },
                                "messages": [
                                    {"role": "system", "content": step7_sys},
                                    {"role": "user", "content": prompt}
                                ]
                            }
                            if "temperature" in params_7: call_kwargs["temperature"] = params_7["temperature"]
                            if "max_tokens" in params_7:
                                if any(m in params_7["model"] for m in ["gpt-5", "o1", "o3"]): call_kwargs["max_completion_tokens"] = params_7["max_tokens"]
                                else: call_kwargs["max_tokens"] = params_7["max_tokens"]
                            if "reasoning_effort" in params_7: call_kwargs["reasoning_effort"] = params_7["reasoning_effort"]
                                
                            ai_response = client.chat.completions.create(**call_kwargs)
                            if ai_response.usage:
                                from utils.helpers import track_usage
                                track_usage(params_7["model"], ai_response.usage.prompt_tokens, ai_response.usage.completion_tokens)
                                
                            ans = ai_response.choices[0].message.content.strip()
                            
                            from utils.helpers import clean_json
                            data = json.loads(clean_json(ans))
                            results_array = data.get("results", [])
                            res_dict = {str(item.get("id")): item for item in results_array if "id" in item}
                            
                            for idx, row in batch.iterrows():
                                row_dict = row.to_dict()
                                item = res_dict.get(str(idx), {})
                                if item:
                                    row_dict["Status na własnej stronie"] = item.get("status", "Błąd")
                                    row_dict["Istniejący URL"] = item.get("istniejacy_url", "")
                                    row_dict["Decyzja Contentowa"] = item.get("decyzja", "")
                                    row_dict["Dopasowanie"] = item.get("dopasowanie", "")
                                    row_dict["Intencja Pomysłu"] = item.get("intencja_pomyslu", "")
                                    row_dict["Temat Pomysłu"] = item.get("temat_pomyslu", "")
                                    row_dict["Ryzyko Kanibalizacji"] = item.get("ryzyko_kanibalizacji", "")
                                    row_dict["Brakujący Kąt/Zakres"] = item.get("brakujacy_kat_lub_zakres", "")
                                    row_dict["Rekomendowana Akcja"] = item.get("rekomendowana_akcja", "")
                                    row_dict["Weryfikacja Uzasadnienie"] = item.get("uzasadnienie", "")
                                else:
                                    row_dict["Status na własnej stronie"] = "BŁĄD MODELU"
                                    row_dict["Weryfikacja Uzasadnienie"] = "Brak ID w odpowiedzi"
                                results_verified.append(row_dict)
                            break 
                            
                        except Exception as e:
                            if "rate" in str(e).lower() or "429" in str(e) or "limit" in str(e).lower():
                                if attempt < max_retries - 1:
                                    my_bar.progress(min(1.0, i / len(df_accepted_to_process)), text=f"Weryfikacja: {i}/{len(df_accepted_to_process)}. (Rate Limit - 10s...)")
                                    time.sleep(10)
                                else:
                                    st.warning(f"Rate Limit przy paczce {i}-{i+batch_size}: {e}")
                            else:
                                st.warning(f"Błąd przy paczce {i}-{i+batch_size}: {e}")
                                break
                            
                    progress_value = min(1.0, (i + len(batch)) / len(df_accepted_to_process))
                    my_bar.progress(progress_value, text=f"Weryfikacja: {i+len(batch)}/{len(df_accepted_to_process)}")
                    
                    if results_verified:
                        df_current = pd.DataFrame(results_verified)
                        if df_ready is not None:
                            df_current = pd.concat([df_ready, df_current], ignore_index=True)
                        table_placeholder.dataframe(df_current)
                        to_excel(df_current, "temp_verification_results_backup.xlsx")
                
                if not results_verified and len(df_accepted_to_process) > 0:
                    st.error("Nie udało się zweryfikować żadnego z pozostałych pomysłów.")
                else:
                    df_newly_verified = pd.DataFrame(results_verified) if results_verified else pd.DataFrame()
                    
                    if df_ready is not None:
                        df_final_verified = pd.concat([df_ready, df_newly_verified], ignore_index=True)
                    else:
                        df_final_verified = df_newly_verified
                        
                    st.session_state.df_verified_results = df_final_verified
                    if os.path.exists("temp_verification_results_backup.xlsx"):
                        os.remove("temp_verification_results_backup.xlsx")
                    st.success("Weryfikacja zakończona pomyślnie!")
                
                st.download_button(
                    label="📥 Pobierz zweryfikowane pomysły (XLSX)",
                    data=to_excel(st.session_state.df_verified_results),
                    file_name='zweryfikowane_pomysly.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
