import streamlit as st
import openai

# Konfiguracja strony musi być pierwszym wywołaniem
st.set_page_config(page_title="Content Gap Analyzer", layout="wide")

# Ustawienie stanu początkowego
if "step" not in st.session_state:
    st.session_state.step = 1

# Pasek boczny na konfigurację i nawigację
with st.sidebar:
    st.title("⚙️ Ustawienia")
    openai_api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not openai_api_key:
        openai_api_key = st.text_input("Podaj klucz OpenAI API:", type="password")
    
    if openai_api_key:
        openai.api_key = openai_api_key
    else:
        st.warning("Brak klucza API OpenAI. Skrypt może nie działać prawidłowo w krokach AI.")
        
    jina_api_key = st.secrets.get("JINA_API_KEY", "")
    if not jina_api_key:
        jina_api_key = st.text_input("Podaj klucz JINA API (opcjonalnie dla płatnego pakietu):", type="password")
        
    st.session_state.jina_api_key = jina_api_key
        
    st.markdown("---")
    st.title("🧭 Nawigacja")
    
    step1 = st.button("Krok 1: Wgranie Danych Domeny", use_container_width=True)
    step2 = st.button("Krok 2: Analiza Produktów (Jina + AI)", use_container_width=True)
    step3 = st.button("Krok 3: Generowanie Fraz", use_container_width=True)
    step4 = st.button("Krok 4: Mapowanie Content Gap", use_container_width=True)
    step5 = st.button("Krok 5: Analiza Brandu", use_container_width=True)
    step6 = st.button("Krok 6: Struktura Własnej Strony", use_container_width=True)
    step7 = st.button("Krok 7: Weryfikacja Istniejących Treści", use_container_width=True)
    step8 = st.button("Krok 8: Audyt Contentu (AI Readiness)", use_container_width=True)
    st.markdown("---")
    step9 = st.button("Krok 9: Globalny Raport (Eksport)", use_container_width=True)
    
    if step1: st.session_state.step = 1
    if step2: st.session_state.step = 2
    if step3: st.session_state.step = 3
    if step4: st.session_state.step = 4
    if step5: st.session_state.step = 5
    if step6: st.session_state.step = 6
    if step7: st.session_state.step = 7
    if step8: st.session_state.step = 8
    if step9: st.session_state.step = 9

st.title("📈 Content Gap Analyzer")

if st.session_state.step == 1:
    from steps import step1_setup
    step1_setup.render()
elif st.session_state.step == 2:
    from steps import step2_products
    step2_products.render(openai_api_key)
elif st.session_state.step == 3:
    from steps import step3_phrases
    step3_phrases.render()
elif st.session_state.step == 4:
    from steps import step4_gap
    step4_gap.render(openai_api_key)
elif st.session_state.step == 5:
    from steps import step5_brand
    step5_brand.render(openai_api_key)
elif st.session_state.step == 6:
    from steps import step6_structure
    step6_structure.render()
elif st.session_state.step == 7:
    from steps import step7_verification
    step7_verification.render(openai_api_key)
elif st.session_state.step == 8:
    from steps import step8_audit
    step8_audit.render(openai_api_key)
elif st.session_state.step == 9:
    from steps import step9_export
    step9_export.render()
