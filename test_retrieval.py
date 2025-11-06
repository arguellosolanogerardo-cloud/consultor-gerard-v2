#!/usr/bin/env python3
"""
Script para probar el retrieval chain fuera de Streamlit
"""
import os
import sys
import json
from datetime import datetime
import uuid

# Simular el contexto que necesita la aplicación
class MockST:
    class secrets:
        @staticmethod
        def keys():
            return []

        def __getitem__(self, key):
            raise KeyError(f'No secret: {key}')

sys.modules['streamlit'] = MockST()

# Ahora importar las funciones
from consultar_web import load_resources, hybrid_retrieval, format_docs_with_metadata
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

print('Cargando recursos...')
try:
    llm_loaded, vs = load_resources()
    print(f'LLM: {type(llm_loaded)}, VS: {type(vs)}')
except Exception as e:
    print(f'Error cargando recursos: {e}')
    import traceback
    traceback.print_exc()
    exit(1)

# Crear retriever híbrido
def hybrid_retriever_func(query: str):
    return hybrid_retrieval(vs, query, k_vector=100, k_keyword=30)

# Crear prompt
prompt = ChatPromptTemplate.from_template('''[INST] <<SYS>>
Eres Gerard, un analista forense especializado en textos antiguos y documentos históricos. Tu tarea es analizar documentos y responder preguntas basándote únicamente en la información proporcionada en el contexto.

INSTRUCCIONES ESPECÍFICAS:
- Responde ÚNICAMENTE en español
- Si la pregunta no puede responderse con el contexto proporcionado, di explícitamente que no tienes suficiente información
- Mantén un tono profesional y objetivo
- Si encuentras contradicciones en el contexto, mencionalas
- Cita las fuentes cuando sea relevante

Contexto proporcionado:
{context}

Pregunta del usuario: {input}
Fecha actual: {date}
Sesión: {session_hash}
<</SYS>> [/INST]''')

# Crear retrieval chain
retrieval_chain = (
    {
        'context': (lambda x: x['input']) | RunnableLambda(hybrid_retriever_func) | format_docs_with_metadata,
        'input': lambda x: x['input'],
        'date': lambda x: x.get('date', ''),
        'session_hash': lambda x: x.get('session_hash', '')
    }
    | prompt
    | llm_loaded
    | StrOutputParser()
)

# Probar consulta
ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
session_hash = str(uuid.uuid4())
payload = {'input': 'que es el amor', 'date': ts, 'session_hash': session_hash}

print('Ejecutando consulta...')
try:
    answer_raw = retrieval_chain.invoke(payload)
    print(f'Respuesta obtenida: {type(answer_raw)}')
    print(f'Contenido: {str(answer_raw)[:500]}...')

    # Verificar si es JSON válido
    import re
    match = re.search(r'\[.*\]', answer_raw, re.DOTALL)
    if match:
        print('JSON encontrado en respuesta')
        data = json.loads(match.group(0))
        print(f'JSON parseado correctamente: {len(data)} items')
    else:
        print('No se encontró JSON en la respuesta')
        print('Respuesta completa:')
        print(answer_raw)

except Exception as e:
    print(f'Error en consulta: {e}')
    import traceback
    traceback.print_exc()