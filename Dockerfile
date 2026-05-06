FROM python:3.12-slim

WORKDIR /app

COPY Backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend/ ./Backend/
COPY Frontend/ ./Frontend/

WORKDIR /app/Backend

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
