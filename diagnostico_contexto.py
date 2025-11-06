from consultar_web import load_resources, hybrid_retrieval
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

print('🔍 DIAGNÓSTICO DETALLADO DEL CONTEXTO')
print('='*50)

# Cargar recursos
llm, vs = load_resources()
print('✓ Recursos cargados')

# Consulta de prueba
query = 'QUIENES SON LOS GUARDIANES DEL UNIVERSO'
docs = hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)
print(f'📄 Documentos recuperados: {len(docs)}')

# Verificar qué documentos contienen la información
print('\n🔎 REVISIÓN DE CONTENIDO EN DOCUMENTOS:')
terminos = ['guardián', 'guardianes', 'universo']
for i, doc in enumerate(docs[:5]):
    content = doc.page_content
    found_terms = [term for term in terminos if term in content.lower()]
    if found_terms:
        print(f'📄 Doc {i+1}: Términos encontrados: {found_terms}')
        # Mostrar extracto del contenido
        start = content.lower().find(found_terms[0])
        if start > 0:
            start = max(0, start - 50)
        extract = content[start:start+200]
        print(f'   💡 "{extract}..."')
    else:
        print(f'📄 Doc {i+1}: Sin términos clave')

# Crear el contexto que se enviaría al LLM
context = '\n\n'.join([f'Documento {i+1}:\n{doc.page_content}' for i, doc in enumerate(docs[:5])])
print(f'\n📝 Longitud del contexto: {len(context)} caracteres')
print(f'📝 Primeros 500 caracteres del contexto:')
print(repr(context[:500]))

# Probar con el prompt
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

chain = prompt | llm | RunnablePassthrough()
response = chain.invoke({'context': context, 'input': query})

print(f'\n🤖 Respuesta del LLM: {response}')