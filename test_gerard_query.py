"""
Script de prueba para verificar el nuevo formato de GERARD
"""
import os
from dotenv import load_dotenv
from consultar_terminal import build_retrieval_chain

load_dotenv()

print("🔄 Inicializando GERARD...")
retrieval_chain = build_retrieval_chain()

print("\n✅ GERARD listo. Ejecutando consulta de prueba...\n")
print("="*80)

# Consulta de prueba
pregunta = "¿Quiénes son los Guardianes del Universo? Dame nombres específicos"

print(f"CONSULTA: {pregunta}")
print("="*80)
print("\nBuscando...\n")

answer = retrieval_chain.invoke({"input": pregunta})

print("RESPUESTA DE GERARD:")
print("="*80)
print(answer)
print("="*80)
