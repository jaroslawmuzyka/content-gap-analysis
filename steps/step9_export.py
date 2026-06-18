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
