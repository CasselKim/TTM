FROM python:3.12.0 as builder

WORKDIR /app

RUN pip install "poetry==1.6.1"

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false

RUN poetry install --no-dev

COPY . /app

CMD ["poetry","run","uvicorn", "app.presentation.api.main:app", "--host", "0.0.0.0", "--port", "80"]
