FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY eup_agents eup_agents
COPY setup setup
COPY config config
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "eup_agents.server:app", "--host", "0.0.0.0", "--port", "8000"]
