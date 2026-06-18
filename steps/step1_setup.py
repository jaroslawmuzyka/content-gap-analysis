import streamlit as st
import pandas as pd
from utils.helpers import normalize_url, to_excel

def render():
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
                    
                    def ahrefs_agg(x):
                        return pd.Series({
                            "Ahrefs_Keywords (ALL)": ", ".join(x["Keyword"].dropna().astype(str)),
                            "Ahrefs_Keywords (TOP10)": ", ".join(x[x["Position"] <= 10]["Keyword"].dropna().astype(str)),
                            "Ahrefs_Keywords (TOP3)": ", ".join(x[x["Position"] <= 3]["Keyword"].dropna().astype(str)),
                            "Ahrefs_Volume": x["Volume"].sum(),
                            "Ahrefs_Traffic": x["Traffic"].sum()
                        })
                    
                    df_a_agg = df_a_clean.groupby("URL_Norm").apply(ahrefs_agg).reset_index()
                    
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
                            
                    def senuto_agg(x):
                        return pd.Series({
                            "Senuto_Keywords (ALL)": ", ".join(x["Keyword"].dropna().astype(str)),
                            "Senuto_Keywords (TOP10)": ", ".join(x[x["Position"] <= 10]["Keyword"].dropna().astype(str)),
                            "Senuto_Keywords (TOP3)": ", ".join(x[x["Position"] <= 3]["Keyword"].dropna().astype(str)),
                            "Senuto_Volume": x["Volume"].sum(),
                            "Senuto_Traffic": x["Traffic"].sum()
                        })
                        
                    df_s_agg = df_s_clean.groupby("URL_Norm").apply(senuto_agg).reset_index()
                    
                    # Konsolidacja obu tabel (Outer Join po URL)
                    df_combined = pd.merge(df_s_agg, df_a_agg, on="URL_Norm", how="outer")
                    df_combined = df_combined.rename(columns={"URL_Norm": "URL"})
                    
                    # Zabezpieczenie kolejności kolumn (URL na początku)
                    cols = ["URL"] + [c for c in df_combined.columns if c != "URL"]
                    df_combined = df_combined[cols]
                    
                    # Usuwanie pustych adresów URL (oraz NaN)
                    df_combined = df_combined.dropna(subset=["URL"])
                    df_combined = df_combined[df_combined["URL"].astype(str).str.strip() != ""]
                    
                    if "Senuto_Traffic" in df_combined.columns:
                        df_combined["Senuto_Traffic"] = df_combined["Senuto_Traffic"].round().astype("Int64")
                        df_combined = df_combined.sort_values(by="Senuto_Traffic", ascending=False)
                    
                    st.session_state.df_domain = df_combined
                    
                    # Generowanie rozszerzonej (niepogrupowanej) wersji tabeli
                    df_a_raw = df_a_clean.copy()
                    df_a_raw["Source"] = "Ahrefs"
                    df_s_raw = df_s_clean.copy()
                    df_s_raw["Source"] = "Senuto"
                    
                    df_unpivoted = pd.concat([df_a_raw, df_s_raw], ignore_index=True)
                    
                    if "URL" in df_unpivoted.columns:
                        df_unpivoted = df_unpivoted.drop(columns=["URL"])
                        
                    df_unpivoted = df_unpivoted.rename(columns={"URL_Norm": "URL"})
                    
                    df_unpivoted = df_unpivoted.dropna(subset=["URL", "Keyword"])
                    df_unpivoted = df_unpivoted[df_unpivoted["URL"].astype(str).str.strip() != ""]
                    
                    df_unpivoted["kw_lower"] = df_unpivoted["Keyword"].astype(str).str.lower()
                    df_unpivoted = df_unpivoted.drop_duplicates(subset=["kw_lower", "URL"])
                    df_unpivoted = df_unpivoted.drop(columns=["kw_lower"])
                    
                    u_cols = ["URL", "Keyword", "Volume", "Traffic", "Position", "Source"]
                    u_cols = [c for c in u_cols if c in df_unpivoted.columns]
                    df_unpivoted = df_unpivoted[u_cols]
                    
                    if "Traffic" in df_unpivoted.columns:
                        mask_senuto = df_unpivoted["Source"] == "Senuto"
                        df_unpivoted.loc[mask_senuto, "Traffic"] = df_unpivoted.loc[mask_senuto, "Traffic"].round().astype("Int64")
                    
                    st.session_state.df_unpivoted = df_unpivoted
                    
                    st.success("Pliki zostały skonsolidowane! Wyniki zebrane po adresie URL.")
                    
                    tab1, tab2 = st.tabs(["Widok Pogrupowany (URL)", "Widok Rozszerzony (Frazy)"])
                    
                    with tab1:
                        st.dataframe(df_combined.head(100))
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
