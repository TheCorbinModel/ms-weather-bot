FROM python:3.11-slim

WORKDIR /app

# Install system font for Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir requests Pillow

COPY . .

CMD ["python", "main.py"]
