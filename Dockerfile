FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./

RUN python -m pip install --root-user-action=ignore --upgrade pip \
    && python -m pip install --root-user-action=ignore \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.12.1 \
    && python -m pip install --root-user-action=ignore \
        fastapi==0.116.1 \
        jinja2==3.1.6 \
        pydantic-settings==2.10.1 \
        qdrant-client==1.15.1 \
        'sentence-transformers>=3.0,<4' \
        sqlalchemy==2.0.43 \
        'uvicorn[standard]==0.35.0'

COPY src ./src

RUN python -m pip install --root-user-action=ignore --no-deps .

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/data \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "mc_pilot.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
