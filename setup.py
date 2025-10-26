from setuptools import setup, find_packages

setup(
    name="ai-assistant",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        'ai_assistant': [
            'config/*.json',
            'data/*.txt',
        ],
    },
    install_requires=[
        "langchain_ollama",
        "sentence-transformers",
        "numpy",
        "prometheus-client",
        "python-dotenv"
    ]
)