import streamlit as st

def render():
    st.header("Krok 3: Ostateczna Lista Fraz do Ahrefs")
    
    if "product_analysis" not in st.session_state or "df_domain" not in st.session_state:
        st.info("Wykonaj najpierw Krok 1 (wgranie danych domeny) i Krok 2 (analiza produktów).")
    else:
        ai_phrases = []
        for item in st.session_state.product_analysis:
            ai_phrases.extend(item.get("seed_keywords", []))
            
        ai_phrases_set = set(ai_phrases)
        
        domain_phrases = []
        if "df_unpivoted" in st.session_state:
            domain_phrases = st.session_state.df_unpivoted["Keyword"].dropna().tolist()
        else:
            if "Senuto_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Senuto_Keywords"].dropna():
                    domain_phrases.extend([k.strip() for k in str(kws).split(",") if k.strip()])
            if "Ahrefs_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Ahrefs_Keywords"].dropna():
                    domain_phrases.extend([k.strip() for k in str(kws).split(",") if k.strip()])
                    
        domain_phrases_set = set(str(p).replace('*', '').lower().strip() for p in domain_phrases)
        
        all_phrases_set = ai_phrases_set.union(domain_phrases_set)
        
        st.write(f"Ilość fraz wygenerowanych przez AI: {len(ai_phrases_set)}")
        st.write(f"Ilość fraz domenowych z plików: {len(domain_phrases_set)}")
        st.write(f"Łącznie po deduplikacji: {len(all_phrases_set)}")
        
        text_to_copy = "\n".join(sorted(list(all_phrases_set)))
        
        st.text_area("Skopiuj te frazy do Ahrefs (Matching Terms):", text_to_copy, height=300)
