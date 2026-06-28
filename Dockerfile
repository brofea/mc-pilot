FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --root-user-action=ignore --upgrade pip \
    && python -m pip install --root-user-action=ignore .

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/data \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "mc_pilot.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
