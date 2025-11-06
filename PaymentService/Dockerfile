FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN touch payments.db && chmod 666 payments.db

CMD ["python", "app/main.py"]