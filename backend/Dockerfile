# Imagem alternativa para deploy no Render como "Docker service".
# Mais confiável que o buildCommand com apt-get do render.yaml para garantir o ffmpeg
# (necessário para extrair frame/áudio de vídeos enviados pelo usuário).

FROM python:3.11-slim

# ffmpeg é necessário para processar vídeo (extração de frame e trilha de áudio)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Usuário não-root: princípio do menor privilégio dentro do container
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
