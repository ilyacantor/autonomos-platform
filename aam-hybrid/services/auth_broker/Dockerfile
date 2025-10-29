FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY services/auth_broker/ services/auth_broker/

CMD ["python", "-m", "services.auth_broker.main"]
