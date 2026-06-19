import streamlit as st

def render():
    st.header("Krok 3: Ostateczna Lista Fraz do Ahrefs")
    
    if "product_analysis" not in st.session_state or "df_domain" not in st.session_state:
        st.info("Wykonaj najpierw Krok 1 (wgranie danych domeny) i Krok 2 (analiza produktów).")
    else:
        # Frazy AI
        ai_phrases = []
        for item in st.session_state.product_analysis:
            ai_phrases.extend(item.get("seed_keywords", []))
        ai_phrases_set = set(str(p).replace('*', '').lower().strip() for p in ai_phrases if str(p).strip())
        
        # Frazy Senuto i Ahrefs
        senuto_phrases_set = set()
        ahrefs_phrases_set = set()
        
        if "df_unpivoted" in st.session_state:
            df_u = st.session_state.df_unpivoted
            sen_kws = df_u[df_u["Source"] == "Senuto"]["Keyword"].dropna()
            ahr_kws = df_u[df_u["Source"] == "Ahrefs"]["Keyword"].dropna()
            
            senuto_phrases_set = set(str(p).replace('*', '').lower().strip() for p in sen_kws if str(p).strip())
            ahrefs_phrases_set = set(str(p).replace('*', '').lower().strip() for p in ahr_kws if str(p).strip())
        else:
            if "Senuto_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Senuto_Keywords"].dropna():
                    for k in str(kws).split(","):
                        if k.strip(): senuto_phrases_set.add(k.replace('*', '').lower().strip())
            if "Ahrefs_Keywords" in st.session_state.df_domain.columns:
                for kws in st.session_state.df_domain["Ahrefs_Keywords"].dropna():
                    for k in str(kws).split(","):
                        if k.strip(): ahrefs_phrases_set.add(k.replace('*', '').lower().strip())
        
        ai_list = sorted(list(ai_phrases_set))
        other_list = sorted(list(senuto_phrases_set.union(ahrefs_phrases_set) - ai_phrases_set))
        all_ordered = ai_list + other_list
        
        st.write(f"Ilość wszystkich fraz łącznie (po deduplikacji): **{len(all_ordered)}**")
        
        st.markdown("""
        ### Instrukcja do Ahrefs
        1. Skopiuj wszystkie frazy i wklej do **Ahrefs (Keyword explorer)**: [https://app.ahrefs.com/keywords-explorer](https://app.ahrefs.com/keywords-explorer)
        2. Przejdź do zakładki **"Matching terms"** i przefiltruj dane:
           - Oznacz np. `Volume` na poziomie od **10**.
           - Ustaw `Intents` na **Non-branded** *(nie chcemy analizować słów brandowych, zarówno własnych jak i konkurencji)*.
        3. Skopiuj wszystkie widoczne frazy kluczowe (max 10 000) i **wklej je ponownie w Keyword Explorer**.
        4. Z lewego menu wybierz pole **Traffic Share** -> **"By page"**.
        5. Wyeksportuj dane, a następnie ręcznie w Excelu **usuń wiersze np. z trafficem poniżej 10** *(nie chcemy pisać na tematy, które nie będą zbierały ruchu)*.
        6. Zapisz plik. Wykorzystasz go w kolejnym **Kroku 4**!
        """)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Wszystkie frazy", "Frazy AI", "Frazy Senuto", "Frazy Ahrefs"])
        
        with tab1:
            st.write(f"Ilość: {len(all_ordered)}")
            st.text_area("Skopiuj te frazy do Ahrefs (Matching Terms):", "\n".join(all_ordered), height=300, key="all_kws")
            
        with tab2:
            st.write(f"Ilość: {len(ai_phrases_set)}")
            st.text_area("Frazy wygenerowane przez AI:", "\n".join(sorted(list(ai_phrases_set))), height=300, key="ai_kws")
            
        with tab3:
            st.write(f"Ilość: {len(senuto_phrases_set)}")
            st.text_area("Frazy wyciągnięte z Senuto:", "\n".join(sorted(list(senuto_phrases_set))), height=300, key="senuto_kws")
            
        with tab4:
            st.write(f"Ilość: {len(ahrefs_phrases_set)}")
            st.text_area("Frazy wyciągnięte z Ahrefs:", "\n".join(sorted(list(ahrefs_phrases_set))), height=300, key="ahrefs_kws")
