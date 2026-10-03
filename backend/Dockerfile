# One image runs the API and the ingestion worker (and optionally Redis) under supervisord.
# Built for Hugging Face Spaces (port 7860, uid 1000) but runs anywhere Docker does.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/user \
    MODELS_CACHE_DIR=/home/user/models \
    PORT=7860

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng supervisor redis-server \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 user
USER user
WORKDIR /home/user/app
ENV PATH="/home/user/.local/bin:$PATH"

# Dependencies first so code changes don't reinstall them.
COPY --chown=user pyproject.toml ./
RUN mkdir app && touch app/__init__.py && pip install --user . && rm -rf app build *.egg-info

# Bake the models into the image: no download on cold start, and no runtime HF Hub dependency.
RUN python -c "from fastembed import TextEmbedding; \
from fastembed.rerank.cross_encoder import TextCrossEncoder; \
TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/home/user/models'); \
TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2', cache_dir='/home/user/models')"

COPY --chown=user . .
RUN pip install --user --no-deps . && chmod +x start.sh

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c \
  "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"7860\")}/api/health')"

CMD ["./start.sh"]
