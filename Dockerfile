# Base image
FROM python:3.12-slim

# Prevents Python from writing pyc files & unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Start the bot
CMD ["python", "fernuni_bot.py"]
