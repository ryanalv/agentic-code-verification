# Ferramentas para busca na web e extração de conteúdo (scraping) de páginas HTML.
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

def web_search(query: str, max_results: int = 3) -> str:
    """Performs a web search using DuckDuckGo."""
    print(f"  [Tool] Searching for: {query}")
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")
        return "\n---\n".join(results)
    except Exception as e:
        return f"Error searching: {str(e)}"

def scrape_page(url: str) -> str:
    """Scrapes the content of a web page."""
    print(f"  [Tool] Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove elementos script e style
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Quebra em linhas e remove espaços iniciais e finais em cada uma
        lines = (line.strip() for line in text.splitlines())
        # Quebra multi-cabeçalhos em uma linha cada
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Descarta linhas em branco
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limita o comprimento para evitar problemas de janela de contexto (truncamento simples)
        return text[:5000] + "... (truncated)" if len(text) > 5000 else text
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"
