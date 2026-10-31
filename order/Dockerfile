FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY order/ ./

ENV PORT=5002
ENV ORDER_DB_PATH=/data/orders.db

EXPOSE 5002

CMD ["python", "app.py"]