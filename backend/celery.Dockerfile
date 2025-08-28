FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e .[dev]
COPY app /app/app
CMD ["celery", "-A", "app.workers.tasks.celery_app", "worker", "--loglevel=INFO"]
