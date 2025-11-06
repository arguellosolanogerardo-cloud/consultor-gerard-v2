#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico específico para consultas problemáticas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from consultar_web import load_resources, hybrid_retrieval
import time

def diagnosticar_consulta(query, k_vector=500, k_keyword=200):
    """Diagnóstico detallado de una consulta específica"""
    print(f"\n{'='*80}")
    print(f"DIAGNÓSTICO PARA: '{query}'")
    print(f"Parámetros: k_vector={k_vector}, k_keyword={k_keyword}")
    print(f"{'='*80}")

    # Cargar recursos
    print("Cargando recursos...")
    llm, vs = load_resources()
    print("✓ Recursos cargados")

    # Ejecutar búsqueda híbrida
    print(f"\nEjecutando búsqueda híbrida...")
    start_time = time.time()
    docs = hybrid_retrieval(vs, query, k_vector=k_vector, k_keyword=k_keyword)
    end_time = time.time()

    print(f"✓ Búsqueda completada en {end_time - start_time:.2f}s")
    print(f"✓ Documentos recuperados: {len(docs)}")

    # Analizar contenido
    print(f"\n{'='*40} ANÁLISIS DE CONTENIDO {'='*40}")

    # Buscar términos clave en los documentos
    terminos_clave = ['guardián', 'guardianes', 'universo', 'evento', 'gran evento', 'fecha', 'septiembre', '2012']
    encontrados = {}

    for termino in terminos_clave:
        encontrados[termino] = []
        for i, doc in enumerate(docs):
            if termino.lower() in doc.page_content.lower():
                encontrados[termino].append(i)

    print("Términos clave encontrados:")
    for termino, indices in encontrados.items():
        if indices:
            print(f"  ✓ '{termino}': encontrado en docs {indices}")
        else:
            print(f"  ✗ '{termino}': NO encontrado")

    # Mostrar preview de los primeros documentos
    print(f"\n{'='*40} PREVIEW DE PRIMEROS 3 DOCUMENTOS {'='*40}")
    for i, doc in enumerate(docs[:3]):
        content_preview = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
        print(f"\n--- Documento {i+1} ---")
        print(f"Metadata: {doc.metadata}")
        print(f"Contenido: {content_preview}")

    return docs

if __name__ == "__main__":
    # Consultas problemáticas reportadas por el usuario
    consultas_problema = [
        "QUIENES SON LOS GUARDIANES DEL UNIVERSO, COMO SON FISICAMENTE",
        "CUAL SERA LA FECHA DEL GRAN EVENTO"
    ]

    for consulta in consultas_problema:
        docs = diagnosticar_consulta(consulta)

    print(f"\n{'='*80}")
    print("DIAGNÓSTICO COMPLETADO")
    print(f"{'='*80}")