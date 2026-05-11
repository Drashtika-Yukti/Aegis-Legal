# Stage 1: Build
FROM python:3.11-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final
FROM python:3.11-slim
WORKDIR /app

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy application modules
COPY main.py .
COPY core/ ./core/
COPY agents/ ./agents/
COPY utils/ ./utils/
COPY requirements.txt .

# Install NLP Medium model for Privacy Shield
RUN python -m spacy download en_core_web_md

# Hugging Face default port
EXPOSE 7860

# Run the production server
CMD ["python", "main.py"]
