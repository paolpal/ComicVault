FROM python:3.12 AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000

# Development stage
FROM base AS development
# Non copiamo il codice perché verrà montato come volume

# Production stage
FROM base AS production
RUN pip install gunicorn
COPY . .
