"""
Parser optimizado para archivos .srt con preservación de timestamps.
Extrae bloques de subtítulos con sus tiempos exactos.
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from langchain_core.documents import Document


@dataclass
class SubtitleBlock:
    """Bloque individual de subtítulo con metadata completa"""
    index: int
    start_time: str  # "00:00:01,319"
    end_time: str    # "00:00:02,800"
    text: str
    start_seconds: float  # Para búsquedas
    end_seconds: float


class SRTParser:
    """Parser especializado para archivos .srt"""
    
    @staticmethod
    def timestamp_to_seconds(timestamp: str) -> float:
        """Convierte HH:MM:SS,mmm a segundos totales"""
        time_part, ms_part = timestamp.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        return h * 3600 + m * 60 + s + ms / 1000
    
    @staticmethod
    def strip_milliseconds(timestamp: str) -> str:
        """Elimina los milisegundos de un timestamp HH:MM:SS,mmm -> HH:MM:SS"""
        return timestamp.split(',')[0]
    
    @staticmethod
    def parse_srt_file(filepath: str) -> List[SubtitleBlock]:
        """
        Parsea un archivo .srt y retorna lista de bloques con timestamps.
        
        Args:
            filepath: Ruta al archivo .srt
            
        Returns:
            Lista de SubtitleBlock con toda la metadata
        """
        blocks = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback a latin-1 si UTF-8 falla
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Regex para parsear bloques de subtítulos
        pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n)*?)(?=\n\d+\n|\Z)'
        
        matches = re.finditer(pattern, content)
        
        for match in matches:
            index = int(match.group(1))
            start_time = match.group(2)
            end_time = match.group(3)
            text = match.group(4).strip()
            
            block = SubtitleBlock(
                index=index,
                start_time=start_time,
                end_time=end_time,
                text=text,
                start_seconds=SRTParser.timestamp_to_seconds(start_time),
                end_seconds=SRTParser.timestamp_to_seconds(end_time)
            )
            blocks.append(block)
        
        return blocks
    
    @staticmethod
    def create_chunks_with_timestamps(
        blocks: List[SubtitleBlock],
        source_filename: str,
        chunk_size: int = 800,
        chunk_overlap: int = 150
    ) -> List[Document]:
        """
        Crea chunks de texto preservando timestamps y metadata.
        
        Args:
            blocks: Lista de SubtitleBlock parseados
            source_filename: Nombre del archivo fuente
            chunk_size: Tamaño objetivo del chunk en caracteres
            chunk_overlap: Overlap entre chunks
            
        Returns:
            Lista de Document de LangChain con metadata enriquecida
        """
        documents = []
        current_text = ""
        current_blocks = []
        
        for block in blocks:
            # Si agregar este bloque excede el tamaño
            if len(current_text) + len(block.text) > chunk_size and current_blocks:
                # Crear documento con el chunk actual
                doc = SRTParser._create_document(
                    current_blocks, 
                    source_filename
                )
                documents.append(doc)
                
                # Calcular overlap: mantener últimos bloques que sumen ~overlap chars
                overlap_text = ""
                overlap_blocks = []
                for b in reversed(current_blocks):
                    if len(overlap_text) + len(b.text) <= chunk_overlap:
                        overlap_blocks.insert(0, b)
                        overlap_text = b.text + " " + overlap_text
                    else:
                        break
                
                current_blocks = overlap_blocks
                current_text = overlap_text
            
            # Agregar bloque actual
            current_blocks.append(block)
            current_text += " " + block.text
        
        # No olvidar el último chunk
        if current_blocks:
            doc = SRTParser._create_document(current_blocks, source_filename)
            documents.append(doc)
        
        return documents
    
    @staticmethod
    def _create_document(blocks: List[SubtitleBlock], source_filename: str) -> Document:
        """Crea un Document de LangChain con metadata completa y timestamps embebidos en el texto"""
        # Concatenar texto CON timestamps de cada bloque individual (sin milisegundos)
        text_parts = []
        for block in blocks:
            # Formato: [HH:MM:SS --> HH:MM:SS] texto (sin milisegundos)
            start_clean = SRTParser.strip_milliseconds(block.start_time)
            end_clean = SRTParser.strip_milliseconds(block.end_time)
            timestamp_prefix = f"[{start_clean} --> {end_clean}]"
            text_parts.append(f"{timestamp_prefix} {block.text}")
        
        # Unir todos los bloques con saltos de línea para mantener claridad
        text = "\n".join(text_parts)
        
        # Metadata enriquecida
        metadata = {
            'source': source_filename,
            'start_time': blocks[0].start_time,
            'end_time': blocks[-1].end_time,
            'start_seconds': blocks[0].start_seconds,
            'end_seconds': blocks[-1].end_seconds,
            'duration_seconds': blocks[-1].end_seconds - blocks[0].start_seconds,
            'start_index': blocks[0].index,
            'end_index': blocks[-1].index,
            'num_blocks': len(blocks),
            # Para respuestas precisas del agente
            'timestamp_range': f"{blocks[0].start_time} → {blocks[-1].end_time}"
        }
        
        return Document(page_content=text, metadata=metadata)


def load_srt_documents_optimized(
    data_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> Tuple[List[Document], Dict]:
    """
    Carga todos los .srt de un directorio con chunking optimizado.
    
    Args:
        data_path: Ruta al directorio con archivos .srt
        chunk_size: Tamaño de chunks en caracteres
        chunk_overlap: Overlap entre chunks
        
    Returns:
        Tupla de (documentos, estadísticas)
    """
    print(f"\n📂 Cargando archivos .srt desde: {data_path}")
    print(f"⚙️  Configuración: chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    all_documents = []
    stats = {
        'total_files': 0,
        'total_chunks': 0,
        'total_blocks': 0,
        'failed_files': []
    }
    
    data_dir = Path(data_path)
    srt_files = list(data_dir.glob("*.srt"))
    
    print(f"✅ Encontrados {len(srt_files)} archivos .srt\n")
    
    for i, filepath in enumerate(srt_files, 1):
        try:
            # Parsear archivo
            blocks = SRTParser.parse_srt_file(str(filepath))
            
            if not blocks:
                print(f"   ⚠️  {filepath.name}: Sin bloques válidos")
                continue
            
            # Crear chunks con timestamps
            chunks = SRTParser.create_chunks_with_timestamps(
                blocks=blocks,
                source_filename=filepath.name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            all_documents.extend(chunks)
            
            stats['total_files'] += 1
            stats['total_chunks'] += len(chunks)
            stats['total_blocks'] += len(blocks)
            
            # Progreso cada 100 archivos
            if i % 100 == 0:
                print(f"   📊 Progreso: {i}/{len(srt_files)} archivos procesados")
            
        except Exception as e:
            print(f"   ❌ Error en {filepath.name}: {e}")
            stats['failed_files'].append(filepath.name)
    
    print(f"\n✅ Carga completada:")
    print(f"   • Archivos procesados: {stats['total_files']}")
    print(f"   • Chunks generados: {stats['total_chunks']}")
    print(f"   • Bloques de subtítulos: {stats['total_blocks']}")
    
    if stats['failed_files']:
        print(f"   ⚠️  Archivos fallidos: {len(stats['failed_files'])}")
    
    return all_documents, stats


# Ejemplo de uso
if __name__ == "__main__":
    # Parsear un archivo individual
    blocks = SRTParser.parse_srt_file("documentos_srt/ejemplo.srt")
    print(f"Bloques extraídos: {len(blocks)}")
    
    if blocks:
        print(f"\nPrimer bloque:")
        print(f"  Índice: {blocks[0].index}")
        print(f"  Tiempo: {blocks[0].start_time} → {blocks[0].end_time}")
        print(f"  Texto: {blocks[0].text[:100]}...")
        print(f"  Segundos: {blocks[0].start_seconds:.2f}s")
    
    # Cargar directorio completo
    documents, stats = load_srt_documents_optimized(
        data_path="documentos_srt/",
        chunk_size=800,
        chunk_overlap=150
    )
    
    print(f"\nTotal documentos: {len(documents)}")
    if documents:
        print(f"Ejemplo de metadata:")
        print(documents[0].metadata)
