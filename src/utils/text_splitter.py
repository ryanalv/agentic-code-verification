import re
from typing import Dict, List

def split_markdown_by_headers(text: str) -> Dict[str, str]:
    """
    Divide um texto markdown em seções baseadas nos cabeçalhos H1 (#) e H2 (##).
    
    Argumentos:
        text (str): O texto markdown completo.
        
    Retorna:
        Dict[str, str]: Um dicionário onde as chaves são os títulos das seções e os valores são o conteúdo.
    """
    sections = {}
    lines = text.split('\n')
    current_title = "Visão Geral" # Título padrão para o preâmbulo
    current_content = []
    
    # Regex para encontrar cabeçalhos H1 ou H2
    # Corresponde a: # Título ou ## Título
    header_pattern = re.compile(r'^(#{1,2})\s+(.+)$')
    
    for line in lines:
        match = header_pattern.match(line)
        if match:
            # Se acumulamos conteúdo para a seção anterior, salvamos
            if current_content:
                # Evita seções vazias se possível, ou apenas mantém
                sections[current_title] = '\n'.join(current_content).strip()
            
            # Inicia nova seção
            # match.group(2) é o texto do título
            current_title = match.group(2).strip()
            current_content = [line] # Mantém a linha do cabeçalho no conteúdo para contexto
        else:
            current_content.append(line)
            
    # Salva a última seção
    if current_content:
        sections[current_title] = '\n'.join(current_content).strip()
        
    return sections
