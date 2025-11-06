#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para probar Ollama
"""

import sys
import os

# Configurar UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from langchain_ollama import OllamaLLM
    print("✅ LangChain Ollama importado correctamente")

    # Probar con llama2:7b
    try:
        llm = OllamaLLM(model="llama2:7b", temperature=0.4, num_ctx=2048)
        print("✅ Modelo llama2:7b inicializado correctamente")

        # Probar una consulta simple
        response = llm.invoke("Hola, ¿cómo estás?")
        print(f"✅ Respuesta: {str(response)[:100]}...")

    except Exception as e:
        print(f"❌ Error con llama2:7b: {e}")

        # Probar con un modelo aún más pequeño
        try:
            llm = OllamaLLM(model="llama2:3.2", temperature=0.4, num_ctx=2048)
            print("✅ Modelo llama2:3.2 inicializado correctamente")

            response = llm.invoke("Hola")
            print(f"✅ Respuesta: {str(response)[:50]}...")

        except Exception as e2:
            print(f"❌ Error con llama2:3.2: {e2}")

except ImportError as e:
    print(f"❌ Error importando langchain_ollama: {e}")