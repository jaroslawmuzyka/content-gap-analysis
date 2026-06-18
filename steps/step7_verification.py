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
        df_accepted = df_gap[df_gap['AI Verdict'] == "PASUJE"]
        df_my = st.session_state.my_pages_df
        
        st.info(f"Do weryfikacji mamy {len(df_accepted)} zaakceptowanych pomysłów na wpisy oraz {len(df_my)} własnych podstron.")
        
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
1. Zwróć wyłącznie poprawny obiekt JSON.
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
            
            user_7_def = """Zadanie: mapowanie nowego pomysłu contentowego do istniejących treści na stronie.

Pomysł na nowy wpis:
URL konkurencji: {target_url}
Tytuł konkurencji: {target_title}
Segment / temat: {segment}

Lista istniejących adresów URL na stronie klienta:
{my_pages_context}

Cel:
Sprawdź, czy wątek opisany w pomyśle na nowy wpis jest już realizowany przez któryś z istniejących adresów URL na stronie klienta.

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

Zwróć wyłącznie poprawny JSON w strukturze:
{
"status": "OPISANE | CZESCIOWO_OPISANE | NIEOPISANE",
"decyzja": "NIE_TWORZ_NOWEGO_WPISU | ROZBUDUJ_ISTNIEJACY_URL | STWORZ_NOWY_WPIS | WYMAGA_RECZNEJ_WERYFIKACJI",
"istniejacy_url": "najlepiej dopasowany istniejący URL albo pusty string",
"dopasowanie": "pelne | czesciowe | luzne | brak | niejasne",
"intencja_pomyslu": "informacyjna | poradnikowa | problemowa | produktowa | porownawcza | sezonowa | niejasna",
"segment": "{segment}",
"temat_pomyslu": "krótki opis głównego tematu pomysłu",
"czy_grozi_kanibalizacja": true,
"ryzyko_kanibalizacji": "wysokie | srednie | niskie | brak",
"brakujacy_kat_lub_zakres": "co trzeba dodać, jeśli temat jest opisany tylko częściowo; pusty string, jeśli nie dotyczy",
"rekomendowana_akcja": "krótka rekomendacja, np. dodać sekcję FAQ, rozbudować artykuł, stworzyć osobny wpis, nie tworzyć nowej treści",
"uzasadnienie": "jedno krótkie zdanie wyjaśniające ocenę"
}"""
            step7_user = st.text_area("User Prompt", value=user_7_def, height=350, key="step7_user")
                
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
                        ans = ai_response.choices[0].message.content.strip()
                        import json
                        try:
                            data = json.loads(ans)
                            row_dict = row.to_dict()
                            row_dict["Status na własnej stronie"] = data.get("status", "Błąd")
                            row_dict["Istniejący URL"] = data.get("istniejacy_url", "")
                            row_dict["Decyzja Contentowa"] = data.get("decyzja", "")
                            row_dict["Dopasowanie"] = data.get("dopasowanie", "")
                            row_dict["Intencja Pomysłu"] = data.get("intencja_pomyslu", "")
                            row_dict["Temat Pomysłu"] = data.get("temat_pomyslu", "")
                            row_dict["Ryzyko Kanibalizacji"] = data.get("ryzyko_kanibalizacji", "")
                            row_dict["Brakujący Kąt/Zakres"] = data.get("brakujacy_kat_lub_zakres", "")
                            row_dict["Rekomendowana Akcja"] = data.get("rekomendowana_akcja", "")
                            row_dict["Weryfikacja Uzasadnienie"] = data.get("uzasadnienie", "")
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
                        
                    progress_value = min(1.0, (idx + 1) / len(df_accepted))
                    my_bar.progress(progress_value, text=f"Weryfikacja {idx+1}/{len(df_accepted)}...")
                
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
