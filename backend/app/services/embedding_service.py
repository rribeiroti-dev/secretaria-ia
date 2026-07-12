import os
import requests
from fastapi import HTTPException

# O nome do modelo continua igual
MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# --- A CORREÇÃO: Nova URL do Router da Hugging Face ---
API_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{MODEL_ID}"

def embed_text(texto: str) -> list[float]:
    # Pega o token que vamos configurar no Render
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("Erro: HF_TOKEN não encontrado nas variáveis de ambiente.")
        # Para testes locais, você pode forçar o token aqui temporariamente (não suba isso pro GitHub!)
        # hf_token = "seu_token_aqui" 
        
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    # Faz a requisição para a API externa gratuita
    response = requests.post(API_URL, headers=headers, json={"inputs": texto})
    
    if response.status_code != 200:
        print(f"Erro da API HF: {response.text}")
        raise HTTPException(status_code=500, detail="Erro ao gerar embedding")
    
    # A API retorna o vetor matemático. 
    # Dependendo da API, pode vir aninhado, mas geralmente é uma lista direta.
    vetor = response.json()
    
    return vetor