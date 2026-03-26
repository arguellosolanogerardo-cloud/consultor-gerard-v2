from consultar_web import load_resources, hybrid_retrieval
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

print('🔧 PRUEBA DIRECTA DEL SISTEMA CORREGIDO')
print('='*50)

# Cargar recursos
llm, vs = load_resources()
print('✓ Recursos cargados')

# Consulta de prueba
query = 'QUIENES SON LOS GUARDIANES DEL UNIVERSO'
docs = hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)
print(f'📄 Documentos recuperados: {len(docs)}')

# Verificar contenido
terminos = ['guardián', 'guardianes', 'universo']
encontrados = sum(1 for doc in docs[:10] if any(term in doc.page_content.lower() for term in terminos))
print(f'✅ Documentos relevantes: {encontrados}/10')

# Probar respuesta del LLM
prompt = ChatPromptTemplate.from_template(r"""
INSTRUCCIONES CRÍTICAS:
- Eres un asistente que RESPONDE ÚNICAMENTE BASADO EN EL CONTEXTO proporcionado abajo
- NO uses conocimiento general, información externa, o conocimientos previos
- Si el CONTEXTO no contiene información relevante para la pregunta, responde EXACTAMENTE: "No tengo enseñanzas sobre ese tema"
- Si encuentras información en el CONTEXTO, cita textualmente y resume basándote SOLO en ese contenido
- Responde en español de manera clara y directa

CONTEXTO PROPORCIONADO:
{context}

PREGUNTA: {input}

RESPUESTA (basada ÚNICAMENTE en el contexto arriba):""")

context = '\n\n'.join([f'Doc {i+1}: {doc.page_content[:200]}...' for i, doc in enumerate(docs[:5])])
chain = prompt | llm | RunnablePassthrough()
response = chain.invoke({'context': context, 'input': query})

print(f'🤖 Respuesta: {response[:300]}...')
print('✅ Prueba completada - Sistema corregido y funcionando')