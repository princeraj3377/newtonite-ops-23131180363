FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODER=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY seed.py .

EXPOSE 8000

CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
