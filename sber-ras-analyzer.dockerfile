FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py .
COPY README.md .

RUN mkdir -p /app/data /app/output

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]