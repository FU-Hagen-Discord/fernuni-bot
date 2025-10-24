FROM python:3.13-slim

ENV MPLCONFIGDIR=/app/matplotlib_cache

WORKDIR /app

# Create a non-root user and group
RUN addgroup --system appuser && adduser --system --ingroup appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/matplotlib_cache
RUN mkdir -p /app/data

# Change ownership of the working directory
RUN chown -R appuser:appuser /app

USER appuser

CMD ["python", "grade_statistics_plotter.py"]