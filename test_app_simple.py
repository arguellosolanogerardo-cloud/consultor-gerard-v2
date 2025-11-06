import streamlit as st
import sys
import os

# Configurar página
st.set_page_config(
    page_title="Consultor Gerard - Test",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔮 Consultor Gerard - Test Version")
st.markdown("---")

# Verificar recursos
st.header("🔍 Verificación de Recursos")

try:
    from consultar_web import load_resources
    st.info("Cargando recursos...")
    llm, vs = load_resources()
    st.success("✅ Recursos cargados correctamente")
    st.write(f"LLM: {type(llm).__name__}")
    st.write(f"VectorStore: {type(vs).__name__}")
except Exception as e:
    st.error(f"❌ Error cargando recursos: {e}")

# Formulario de prueba
st.header("💬 Prueba de Consulta")

with st.form("consulta_form"):
    pregunta = st.text_input("Escribe tu pregunta sobre Gerard:", "Qué dice Gerard sobre el amor?")
    submitted = st.form_submit_button("Consultar")

    if submitted:
        st.info("Procesando consulta...")
        try:
            from consultar_web import hybrid_retrieval
            docs = hybrid_retrieval(vs, pregunta, k_vector=100, k_keyword=30)
            st.success(f"✅ Recuperados {len(docs)} documentos relevantes")

            # Mostrar respuesta del LLM
            response = llm.invoke(f"Responde basado en esta información sobre Gerard: {docs[0].page_content[:500]}...\\n\\nPregunta: {pregunta}")
            st.markdown("### Respuesta:")
            st.write(response)

        except Exception as e:
            st.error(f"❌ Error procesando consulta: {e}")

st.markdown("---")
st.caption("Test version - Consultor Gerard con DeepSeek R1 8B")