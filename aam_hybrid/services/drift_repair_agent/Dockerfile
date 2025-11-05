FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY services/drift_repair_agent/ services/drift_repair_agent/

CMD ["python", "-m", "services.drift_repair_agent.main"]
