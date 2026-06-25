import streamlit as st
import pandas as pd
from utils.helpers import render_wow_metrics

def render():
    st.header("Krok 5: Struktura Własnej Strony")
    render_wow_metrics()
    
    st.markdown("Wgraj plik (np. XLSX lub CSV) z listą adresów URL i tytułów, które już istnieją na Twojej stronie. Posłużą one do sprawdzenia, czy wygenerowane pomysły na wpisy nie są już opisane.")
    
    my_file = st.file_uploader("Wgraj plik z własnymi URLami (kolumny URL, Title)", type=['csv', 'xlsx', 'xls'])
    if my_file:
        try:
            if my_file.name.endswith('.csv'):
                df_my_pages = pd.read_csv(my_file)
            else:
                df_my_pages = pd.read_excel(my_file)
                
            st.write(f"Wczytano {len(df_my_pages)} wierszy.")
            st.dataframe(df_my_pages.head())
            
            if st.button("Zapisz do weryfikacji", type="primary"):
                st.session_state.my_pages_df = df_my_pages
                if "global_stats" in st.session_state:
                    st.session_state.global_stats["strony_wlasne"] = len(df_my_pages)
                st.success("Plik zapisany w pamięci do użycia w kolejnych krokach.")
        except Exception as e:
            st.error(f"Błąd podczas wczytywania pliku: {e}")
