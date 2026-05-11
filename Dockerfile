# Stage 1: Build
FROM python:3.11-slim AS builder
WORKDIR /install
COPY engine/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final
FROM python:3.11-slim
WORKDIR /app

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy application from the engine/ directory
COPY engine/main.py .
COPY engine/core/ ./core/
COPY engine/agents/ ./agents/
COPY engine/utils/ ./utils/
COPY engine/requirements.txt .

# Install NLP Medium model for Privacy Shield
RUN python -m spacy download en_core_web_md

# Hugging Face default port
EXPOSE 7860

# Ensure logs are visible in the HF dashboard
ENV PYTHONUNBUFFERED=1

# Run the production server
CMD ["python", "main.py"]
