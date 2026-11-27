# Nobel Explorer API, including Nobel Intelligence (AI research assistant).
#
# The AI packages, the pinned embedding model and the packaged knowledge index
# are baked into the image, so production never downloads a model or rebuilds
# the index. The assistant stays OFF unless AI_AGENT_ENABLED=true is set on
# the service; with it off, the model is never loaded.

# 1. Start with Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface

# 2. Create a working directory inside the container
WORKDIR /app

# 3. Copy dependency lists first
COPY requirements.txt requirements-ai.txt ./

# 4. Install Python dependencies. CPU-only PyTorch comes first from the PyTorch
#    CPU index (the default Linux wheel pulls several GB of CUDA libraries); the
#    exact torch pin in requirements-ai.txt is then satisfied by the +cpu build.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0 \
 && pip install -r requirements-ai.txt \
 && pip check

# 5. Download the pinned embedding model (PyTorch safetensors weights only).
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG EMBEDDING_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('${EMBEDDING_MODEL}', revision='${EMBEDDING_REVISION}', \
allow_patterns=['*.json', 'vocab.txt', 'model.safetensors', '1_Pooling/*'])" \
 && chmod -R a+rX "$HF_HOME"

# 6. Offline inference against the baked model and the packaged index
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    ANONYMIZED_TELEMETRY=False \
    AI_EMBEDDING_MODEL=${EMBEDDING_MODEL} \
    AI_EMBEDDING_REVISION=${EMBEDDING_REVISION} \
    AI_CHROMA_DIR=/app/deploy/ai-index/chroma

# 7. Copy backend application code and the packaged knowledge index
COPY backend ./backend
COPY deploy/ai-index ./deploy/ai-index

# 8. Run as an unprivileged user (Chroma needs write access to its own directory
#    for SQLite locks; everything else is read-only for this user)
RUN useradd --system --uid 10001 --no-create-home app \
 && chown -R app /app/deploy/ai-index
USER app

# 9. Document the FastAPI port
EXPOSE 8000

# 10. Start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
