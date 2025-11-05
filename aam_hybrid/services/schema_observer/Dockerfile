FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY services/schema_observer/ services/schema_observer/

CMD ["python", "-m", "services.schema_observer.main"]
