#!/usr/bin/env python3
"""
Script de prueba para el sistema optimizado de ingesta SRT
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestar_optimizado import SRTParser, IngestConfig, IngestorSRT

def test_srt_parser():
    """Prueba el parser SRT"""
    print("🧪 Probando parser SRT...")

    # Crear archivo SRT de prueba
    test_srt_content = """1
00:00:01,000 --> 00:00:05,000
Hola, este es un subtítulo de prueba.

2
00:00:06,000 --> 00:00:10,000
Segundo subtítulo para verificar el parser.
"""

    test_file = "test_subtitle.srt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_srt_content)

    try:
        # Probar parser
        entries = SRTParser.parse_srt_file(test_file)

        print(f"✅ Parser SRT: {len(entries)} entradas encontradas")

        for entry in entries:
            print(f"   • Secuencia {entry.sequence_number}: {entry.timestamp_start} → {entry.timestamp_end}")
            print(f"     Texto: {entry.text[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Error en parser SRT: {e}")
        return False
    finally:
        # Limpiar archivo de prueba
        if os.path.exists(test_file):
            os.remove(test_file)

def test_config():
    """Prueba la configuración"""
    print("\n🧪 Probando configuración...")

    config = IngestConfig()
    print(f"✅ Configuración creada:")
    print(f"   • Chunk size: {config.chunk_size}")
    print(f"   • Chunk overlap: {config.chunk_overlap}")
    print(f"   • Batch size: {config.batch_size}")
    print(f"   • Separators: {config.separators}")

    return True

def test_ingestor_init():
    """Prueba la inicialización del ingestor"""
    print("\n🧪 Probando inicialización del ingestor...")

    try:
        config = IngestConfig()
        ingestor = IngestorSRT(config)
        print("✅ Ingestor inicializado correctamente")
        print(f"   • Embeddings: {type(ingestor.embeddings).__name__}")
        return True
    except Exception as e:
        print(f"❌ Error inicializando ingestor: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA OPTIMIZADO SRT")
    print("=" * 60)

    tests = [
        ("Parser SRT", test_srt_parser),
        ("Configuración", test_config),
        ("Inicialización Ingestor", test_ingestor_init),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error ejecutando {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nResultado final: {passed}/{total} pruebas pasaron")

    if passed == total:
        print("🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        print("\nPara ejecutar la ingesta completa:")
        print("  python ingestar_optimizado.py --force")
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")

if __name__ == "__main__":
    main()