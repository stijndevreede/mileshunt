FROM python:3.12-slim

WORKDIR /app

RUN mkdir -p /app/data

COPY pyproject.toml .
COPY mileshunt/ mileshunt/
COPY static/ static/

RUN pip install --no-cache-dir .

ENV MILESHUNT_DB=/app/data/mileshunt.db

EXPOSE 8000

CMD ["uvicorn", "mileshunt.app:app", "--host", "0.0.0.0", "--port", "8000"]
