# Arquivo: generate_graph.py
# Propósito: Gera e salva um gráfico de fluxo de execução com possíveis loops.

import os
import networkx as nx
import matplotlib.pyplot as plt

def generate_execution_flow_graph():
    """Gera o gráfico de fluxo do ciclo do Agente e salva como imagem."""
    G = nx.DiGraph()
    nodes = ["Scanner", "Planner", "Reader", "Writer", "Critic"]
    G.add_nodes_from(nodes)

    # Arestas do fluxo principal
    edges = [
        ("Scanner", "Planner"),
        ("Planner", "Reader"),
        ("Reader", "Writer"),
        ("Writer", "Critic")
    ]
    G.add_edges_from(edges)

    # Arestas de possíveis loops
    G.add_edge("Critic", "Writer", label="Refinement Loop")
    G.add_edge("Critic", "Planner", label="Full Rethink Loop")

    plt.figure(figsize=(12, 6))
    
    # Layout posicionado manualmente para ficar alinhado da esquerda para a direita
    pos = {
        "Scanner": (0, 0),
        "Planner": (1, 0),
        "Reader": (2, 0),
        "Writer": (3, 0),
        "Critic": (4, 0)
    }

    # Desenhando os nós e arestas regulares
    nx.draw_networkx_nodes(G, pos, node_size=4000, node_color="skyblue", edgecolors="black")
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold")
    
    # Desenhar as arestas do fluxo principal retas
    main_edges = [(u, v) for u, v in G.edges() if not "Loop" in G.edges[u, v].get('label', '')]
    nx.draw_networkx_edges(G, pos, edgelist=main_edges, arrows=True, arrowsize=20, edge_color="black")
    
    # Desenhar as arestas de loop curvadas
    loop_edges = [(u, v) for u, v in G.edges() if "Loop" in G.edges[u, v].get('label', '')]
    nx.draw_networkx_edges(G, pos, edgelist=loop_edges, arrows=True, arrowsize=20, edge_color="red", connectionstyle="arc3,rad=-0.5")

    # Adicionar labels aos loops
    edge_labels = nx.get_edge_attributes(G, 'label')
    # Ajuste simples para exibir os labels
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', label_pos=0.3)

    plt.title("Fluxo de Execução do Agente (com Loops)", fontsize=14)
    plt.axis("off")
    
    output_path = "execution_flow_graph.png"
    plt.savefig(output_path, bbox_inches="tight")
    print(f"Gráfico gerado e salvo com sucesso em: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_execution_flow_graph()
