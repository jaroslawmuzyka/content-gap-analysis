import streamlit as st
import pandas as pd

def render():
    st.header("Krok 0: Wczytanie Sesji (Masowy Import)")
    st.markdown("Wgraj plik 'Raport_Krok9_Globalny.xlsx' (lub inny wyeksportowany raport), aby odtworzyć dane w aplikacji bez konieczności ponownego płacenia za API i czekania na generację AI.")
    
    uploaded_file = st.file_uploader("Wgraj wyeksportowany plik Excel", type=['xlsx'])
    
    if uploaded_file is not None:
        if st.button("Odtwórz Sesję", type="primary"):
            with st.spinner("Wczytywanie i parsowanie danych z Excela..."):
                try:
                    # Read all sheets
                    excel_file = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_file.sheet_names
                    
                    if "1. Frazy Domeny" in sheet_names:
                        st.session_state.df_domain = pd.read_excel(uploaded_file, sheet_name="1. Frazy Domeny")
                    if "1a. Frazy Rozszerzone" in sheet_names:
                        st.session_state.df_unpivoted = pd.read_excel(uploaded_file, sheet_name="1a. Frazy Rozszerzone")
                    
                    if "4. Content Gap" in sheet_names:
                        st.session_state.df_gap_results = pd.read_excel(uploaded_file, sheet_name="4. Content Gap")
                        
                    if "6. Brand Klastry" in sheet_names:
                        st.session_state.df_brand_clusters = pd.read_excel(uploaded_file, sheet_name="6. Brand Klastry")
                        
                    if "7. Weryfikacja Gap" in sheet_names:
                        st.session_state.df_verified_results = pd.read_excel(uploaded_file, sheet_name="7. Weryfikacja Gap")
                        
                    if "8. Audyt Contentu" in sheet_names:
                        st.session_state.df_audited = pd.read_excel(uploaded_file, sheet_name="8. Audyt Contentu")
                        
                    # Reconstruct global stats somewhat
                    if "global_stats" not in st.session_state:
                        st.session_state.global_stats = {
                            "przeanalizowane_frazy": 0,
                            "strony_konkurencji": 0,
                            "strony_wlasne": 0,
                            "wygenerowane_pomysly": 0,
                            "content_gaps": 0
                        }
                    
                    if "1a. Frazy Rozszerzone" in sheet_names:
                        st.session_state.global_stats["przeanalizowane_frazy"] = len(st.session_state.df_unpivoted)
                    if "4. Content Gap" in sheet_names:
                        st.session_state.global_stats["strony_konkurencji"] = len(st.session_state.df_gap_results)
                    if "6. Brand Klastry" in sheet_names:
                        st.session_state.global_stats["wygenerowane_pomysly"] = len(st.session_state.df_brand_clusters)
                    if "7. Weryfikacja Gap" in sheet_names:
                        st.session_state.global_stats["content_gaps"] = len(st.session_state.df_verified_results)
                    
                    st.success("Sesja została odtworzona pomyślnie! Możesz teraz przejść do innych kroków lub wygenerować raporty HTML/DOCX w Kroku 9.")
                    
                except Exception as e:
                    st.error(f"Błąd podczas wczytywania sesji: {e}")
