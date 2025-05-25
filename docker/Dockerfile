FROM python:3.12.0 as builder

WORKDIR /app

RUN pip install "poetry==2.1.2"

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false

RUN poetry install --no-root

COPY . /app

CMD ["poetry","run","uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
