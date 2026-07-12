import os
import requests
from fastapi import HTTPException

# O modelo E5 (perfeito para o seu banco de dados)
MODEL_ID = "intfloat/multilingual-e5-small"

# A URL EXATA do novo router (agora com a ordem correta: primeiro /models/, depois /pipeline/)
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_ID}/pipeline/feature-extraction"

def embed_text(texto: str) -> list[float]:
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("Erro: HF_TOKEN não encontrado nas variáveis de ambiente.")
        raise HTTPException(status_code=500, detail="Token de IA ausente no servidor")
        
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    # O modelo E5 pede que o texto venha com o prefixo "query: " para buscas
    payload = {"inputs": f"query: {texto}"}
    
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Erro da API HF: {response.text}")
        raise HTTPException(status_code=500, detail="Erro ao gerar embedding na Hugging Face")
    
    vetores = response.json()
    
    # O Hugging Face costuma devolver o vetor aninhado: [[[0.1, 0.2...]]]
    # O Supabase exige uma lista plana: [0.1, 0.2...]
    while isinstance(vetores, list) and len(vetores) > 0 and isinstance(vetores[0], list):
        vetores = vetores[0]
        
    return vetores