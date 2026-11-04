FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY . .
RUN pip install --no-cache-dir -e .
CMD ["python", "main.py", "gateway"]
