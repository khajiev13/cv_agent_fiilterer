FROM docker.1panel.dev/library/python:3.9-slim

WORKDIR /app

COPY requirements.txt .

#Install packages for file processing
RUN apt-get update && apt-get install -y \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    antiword \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir -r requirements.txt 


COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/main.py"]