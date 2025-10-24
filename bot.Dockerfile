FROM python:3.13-slim

WORKDIR /app

# Create a non-root user and group
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Change ownership of the working directory
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "fernuni_bot.py"]