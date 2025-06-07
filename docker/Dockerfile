FROM python:3.12.0 as builder

WORKDIR /app

# 시스템 패키지 업데이트 및 한글 폰트 설치
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    fonts-nanum \
    fontconfig \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry==2.1.2"

COPY pyproject.toml poetry.lock* /app/

RUN poetry config virtualenvs.create false

RUN poetry install --no-root

COPY . /app

CMD ["poetry","run","uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
