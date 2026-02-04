import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from src.agents.critic import ApfdRevisorAgent
from src.utils.logger import logger

def test_agent():
    print("Testing ApfdRevisorAgent initialization...")
    try:
        agent = ApfdRevisorAgent()
        print("Success: Agent initialized.")
    except Exception as e:
        print(f"FAIL: Initialization error: {e}")
        return

    print("\nTesting validar_completude...")
    try:
        # Test with empty dict
        probs_empty = agent.validar_completude({})
        print(f"Empty dict problems: {len(probs_empty)} (Expected > 0)")
        
        # Test with valid dict (mock)
        valid_mock = {
            'dados_processuais': {'promotoria': 'X', 'comarca': 'Y', 'numero_processo': '1'},
            'flagranteados': {'nome': 'A', 'qualificacao': 'B'},
            'crimes_penas': {'crimes': ['C'], 'pena_minima_total': 1, 'pena_maxima_total': 2},
            'antecedentes': {'possui_antecedentes': False, 'reincidente': False},
            'avaliacao_juridica': {'tipo_manifestacao': 'Preventiva', 'fundamentacao': 'Sim'}
        }
        probs_valid = agent.validar_completude(valid_mock)
        print(f"Valid dict problems: {len(probs_valid)} (Expected 0)")
        if probs_valid:
            print(f"Unexpected problems: {probs_valid}")
            
    except Exception as e:
        print(f"FAIL: validar_completude error: {e}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    test_agent()
