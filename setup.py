# Infraestrutura que serve para distribuir, empacotar e instalar o projeto. 
from setuptools import setup, find_packages

setup(
    name="ai_quality_critic_agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv",
        "openai",
        "pandas",
        "matplotlib",
    ],
)
