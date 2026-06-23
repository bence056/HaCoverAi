FROM python:3.14-slim

# --- system deps ---
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# --- working directory ---
WORKDIR /app

# --- install python deps first (better caching) ---
COPY requirements.txt .

# IMPORTANT: PyTorch CPU wheels for ARM64
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio \
      --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# --- copy project ---
COPY . .

# --- default environment ---
ENV PYTHONUNBUFFERED=1

# --- run inference by default ---
CMD ["python", "ai.py", "--prod"]