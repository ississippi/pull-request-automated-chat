# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y build-essential

COPY static/ ./static
# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Run server
EXPOSE 8080
CMD ["uvicorn", "chat_ws_api:app", "--host", "0.0.0.0", "--port", "8080"]

