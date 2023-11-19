FROM python:3.12.0 as builder

RUN pip install "poetry==1.6.1"

WORKDIR /ttm

COPY poetry.lock pyproject.toml .

RUN poetry config virtualenvs.create false \
    && poetry install --only main

ENV TZ=Asia/Seoul

FROM python:3.12.0-slim

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/alembic

WORKDIR /ttm

COPY . .

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
