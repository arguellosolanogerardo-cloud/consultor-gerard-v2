#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico detallado de consultas problemáticas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from consultar_web import load_resources, hybrid_retrieval, format_docs_with_metadata, prompt
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from datetime import datetime
import uuid

def analizar_consulta_detallada(query, max_docs=50):
    """Análisis detallado de una consulta específica"""
    print(f"\n{'='*100}")
    print(f"ANÁLISIS DETALLADO: '{query}'")
    print(f"{'='*100}")

    # Cargar recursos
    llm, vs = load_resources()
    print("✓ Recursos cargados")

    # Recuperar documentos
    docs = hybrid_retrieval(vs, query, k_vector=500, k_keyword=200)
    print(f"✓ Recuperados {len(docs)} documentos")

    # Limitar para análisis
    docs_analisis = docs[:max_docs]

    # Buscar términos clave específicos en la consulta
    query_lower = query.lower()
    terminos_busqueda = []

    # Extraer términos relevantes de la consulta
    if 'guardián' in query_lower or 'guardianes' in query_lower:
        terminos_busqueda.extend(['guardián', 'guardianes', 'universo', 'maestro', 'maestros'])
    if 'evento' in query_lower or 'gran evento' in query_lower:
        terminos_busqueda.extend(['evento', 'gran evento', 'fecha', 'septiembre', '2012'])
    if 'alaniso' in query_lower or 'maestro' in query_lower:
        terminos_busqueda.extend(['alaniso', 'maestro', 'alan'])

    print(f"🔍 Buscando términos clave: {terminos_busqueda}")

    # Analizar cada documento
    docs_con_terminos = []
    for i, doc in enumerate(docs_analisis):
        content_lower = doc.page_content.lower()
        encontrados = [term for term in terminos_busqueda if term in content_lower]

        if encontrados:
            docs_con_terminos.append((i, doc, encontrados))
            print(f"📄 Doc {i}: Términos encontrados: {encontrados}")
            # Mostrar extracto del documento
            for term in encontrados:
                if term in content_lower:
                    start = max(0, content_lower.find(term) - 100)
                    end = min(len(content_lower), content_lower.find(term) + 200)
                    extracto = doc.page_content[start:end]
                    print(f"   💡 '{term}': ...{extracto}...")
                    break
            print()

    print(f"📊 RESUMEN: {len(docs_con_terminos)} documentos contienen términos relevantes de {len(docs_analisis)} analizados")

    # Formatear contexto como lo haría la aplicación
    context = format_docs_with_metadata(docs_analisis)
    print(f"📝 Contexto formateado: {len(context)} caracteres")

    # Crear payload como la aplicación
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    session_hash = str(uuid.uuid4())
    payload = {
        'context': context,
        'input': query,
        'date': ts,
        'session_hash': session_hash
    }

    # Ejecutar LLM
    print(f"\n🤖 CONSULTANDO LLM...")
    try:
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke(payload)
        print("✓ Respuesta del LLM:")
        print(f"'{result}'")

        # Analizar si la respuesta indica falta de información
        if 'no tengo' in result.lower() or 'enseñanzas' in result.lower():
            print("❌ LLM indica que NO tiene información")
            return False
        else:
            print("✅ LLM proporcionó información")
            return True

    except Exception as e:
        print(f"❌ Error en LLM: {e}")
        return False

if __name__ == "__main__":
    # Consultas problemáticas reportadas
    consultas_problema = [
        "NO ENCUENTRA NADA DE NADA CUAL ES EL NOMBRE DE LOS GUARDIANES DEL UNIVERSO Y COMO SON FISICAMENTE LOS 9 MAESTROS?",
        "CUANDO SERA EL GRAN EVENTO",
        "QUIEN ES EL MAESTRO ALANISO"
    ]

    resultados = []
    for consulta in consultas_problema:
        exito = analizar_consulta_detallada(consulta)
        resultados.append((consulta, exito))

    print(f"\n{'='*100}")
    print("RESUMEN FINAL")
    print(f"{'='*100}")
    for consulta, exito in resultados:
        status = "✅ ÉXITO" if exito else "❌ FALLÓ"
        print(f"{status}: {consulta[:50]}...")