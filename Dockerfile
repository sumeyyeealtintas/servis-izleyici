FROM python:3.12-slim

# Root olmayan kullanıcı ile çalıştır (konteyner güvenliği için iyi pratik)
RUN useradd --create-home --uid 10001 izleyici
WORKDIR /uygulama

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY izleyici ./izleyici
COPY izleme.yaml .
USER izleyici

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/saglik', timeout=2)"

CMD ["uvicorn", "izleyici.uygulama:uygulama_olustur", "--factory", "--host", "0.0.0.0", "--port", "8000"]
