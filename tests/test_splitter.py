import sys
import os

# Adiciona a raiz ao sys.path para importação correta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.text_splitter import split_markdown_by_headers

def test_split_markdown():
    sample_text = """# Introdução
    
Esta é a introdução.

## Arquitetura

Esta é a seção de arquitetura.
Ela fala sobre arquivos como `src/main.py`.

# Banco de Dados

Aqui está o esquema do banco de dados.
    """
    
    sections = split_markdown_by_headers(sample_text)
    
    # Print de depuração
    print(f"Seções encontradas: {sections.keys()}")
    
    # Verificações (Asserts)
    # Nota: Ajustei as chaves esperadas para bater com o texto de exemplo em PT se necessário, 
    # mas aqui o splitter usa o texto do header.
    assert "Introdução" in sections
    assert "Arquitetura" in sections
    assert "Banco de Dados" in sections
    assert "Esta é a introdução." in sections["Introdução"]
    
    print("Teste do Divisor Passou!")

if __name__ == "__main__":
    test_split_markdown()
