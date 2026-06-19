import streamlit as st
import pandas as pd
from utils.helpers import to_excel_multi

def render():
    st.header("Krok 9: Globalny Raport (Eksport)")
    st.markdown("Tutaj możesz wyeksportować wszystkie dotychczas zebrane i wygenerowane dane w postaci jednego, eleganckiego pliku Excel z wieloma zakładkami (Sheetami). Plik zostanie automatycznie sformatowany.")
    
    sheets = {}
    
    # 1. Domeny (Krok 1)
    if "df_domain" in st.session_state:
        sheets["1. Frazy Domeny"] = st.session_state.df_domain
    if "df_unpivoted" in st.session_state:
        sheets["1a. Frazy Rozszerzone"] = st.session_state.df_unpivoted
        
    # 2. Analiza Produktów (Krok 2)
    if "product_analysis" in st.session_state:
        from utils.helpers import get_step2_excel_sheets
        step2_sheets = get_step2_excel_sheets(st.session_state.product_analysis)
        sheets.update(step2_sheets)
        
    # 4. Content Gap (Krok 4)
    if "df_gap_results" in st.session_state:
        sheets["4. Content Gap"] = st.session_state.df_gap_results
        
    # 5. Analiza Brandu (Krok 5)
    if "brand_clusters" in st.session_state:
        cluster_data = []
        for k in st.session_state.brand_clusters.get("klastry", []):
            frazy = k.get("frazy_w_klastrze", [])
            frazy_str = ", ".join([str(f.get("keyword", "")) for f in frazy])
            vol_sum = sum([int(f.get("volume", 0)) for f in frazy if str(f.get("volume")).isdigit()])
            url_title = k.get("proponowany_title", k.get("proponowany_h1", k.get("nazwa_klastra", "")))
            cluster_data.append({
                "Proponowany Title / H1": url_title,
                "Nazwa Klastra": k.get("nazwa_klastra", ""),
                "Frazy w klastrze": frazy_str,
                "Łączny Volume": vol_sum,
                "Rekomendowana Akcja": k.get("rekomendacja", ""),
                "Priorytet": k.get("priorytet", ""),
                "Typ Klastra": k.get("typ_klastra", ""),
                "Uzasadnienie": k.get("uzasadnienie_rekomendacji", "")
            })
        if cluster_data:
            sheets["5. Brand Klastry"] = pd.DataFrame(cluster_data)
            
    if "brand_analysis_results" in st.session_state:
        frazy_data = []
        for item in st.session_state.brand_analysis_results:
            frazy_data.append({
                "Fraza (Keyword)": item.get("keyword", ""),
                "Volume": item.get("volume", 0),
                "Pozycja": item.get("position", 0),
                "Dopasowany Produkt": item.get("produkt", ""),
                "Intencja": item.get("intencja", ""),
                "Etap Ścieżki": item.get("etap_sciezki_uzytkownika", ""),
                "Problem Użytkownika": item.get("problem_uzytkownika", ""),
                "Dopasowanie": item.get("dopasowanie_do_produktu", ""),
                "Proponowany Temat/Sekcja": item.get("proponowany_temat_lub_sekcja", ""),
                "Rekomendowany Typ Treści": item.get("rekomendowany_typ_tresci", ""),
                "Ryzyko Claimów": item.get("ryzyko_claimow", ""),
                "Bezpieczny Kierunek": item.get("bezpieczny_kierunek_odpowiedzi", ""),
                "Czego NIE sugerować": item.get("czego_nie_sugerowac", ""),
                "Uzasadnienie": item.get("uzasadnienie", "")
            })
        if frazy_data:
            sheets["5a. Brand Frazy"] = pd.DataFrame(frazy_data)
        
    # 7. Weryfikacja (Krok 7)
    if "df_verified_results" in st.session_state:
        sheets["7. Weryfikacja Gap"] = st.session_state.df_verified_results
        
    # 8. Audyt (Krok 8)
    if "df_audited" in st.session_state:
        sheets["8. Audyt Contentu"] = st.session_state.df_audited
        
    if not sheets:
        st.warning("Nie masz jeszcze żadnych danych do eksportu. Wykonaj poprzednie kroki w nawigacji, aby zebrać dane.")
        return
        
    st.success(f"Znaleziono {len(sheets)} zakładek do wygenerowania. Możesz je teraz pobrać.")
    
    st.write("Dostępne zakładki do eksportu:")
    for name in sheets.keys():
        st.markdown(f"- **{name}**")
        
    with st.spinner("Generowanie i formatowanie pliku Excel..."):
        try:
            excel_data = to_excel_multi(sheets)
            
            st.download_button(
                label="📥 Pobierz Globalny Raport (XLSX)",
                data=excel_data,
                file_name='content_gap_globalny_raport.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Wystąpił błąd podczas generowania pliku Excel: {e}")
