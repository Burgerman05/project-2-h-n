FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .  

RUN touch buyers.db && chmod 666 buyers.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]