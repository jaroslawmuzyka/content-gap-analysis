import streamlit as st
import pandas as pd

def render():
    st.header("Krok 5: Struktura Własnej Strony")
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
                st.success("Struktura strony zapisana pomyślnie. Możesz przejść do Kroku 6 (Analiza Brandu) oraz Kroku 7 (Weryfikacja Gap).")
        except Exception as e:
            st.error(f"Błąd podczas wczytywania pliku: {e}")
