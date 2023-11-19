# TTM
Auto trade and manage stocks/coins platform
<p align="center">
</p>
  <p align="center">
    <a href="https://github.com/anuraghazra/github-readme-stats/actions">
      <img alt="Tests Passing" src="https://github.com/anuraghazra/github-readme-stats/workflows/Test/badge.svg" />
    </a>
    <a href="https://codecov.io/gh/anuraghazra/github-readme-stats">
      <img alt="Tests Coverage" src="https://codecov.io/gh/anuraghazra/github-readme-stats/branch/master/graph/badge.svg" />
    </a>
    <br />
    <a href="https://github.com/anuraghazra/github-readme-stats/issues">
      <img alt="Issues" src="https://img.shields.io/github/issues/anuraghazra/github-readme-stats?color=0088ff" />
    </a>
    <a href="https://github.com/anuraghazra/github-readme-stats/pulls">
      <img alt="GitHub pull requests" src="https://img.shields.io/github/issues-pr/anuraghazra/github-readme-stats?color=0088ff" />
    </a>
    <br />
    <br />

  </p>


## Requirements
- python 12.0
- poetry 1.6.1
- fastapi 0.104.1


## Installation
### 1. Download repo
```
git clone https://github.com/CasselKim/TTM.git`
```

### 2. Download poetry
https://python-poetry.org/docs/#installing-with-the-official-installer

### 3. Create venv
```
poetry install
```
### 4. Execute docker
```
docker build -f docker/Dockerfile . -t ttm-image
docker compose -f docker/docker-compose-local.yml -p ttm up -d
```
### 5. Check the access
http://0.0.0.0/docs
![image](docs/local_test.png)

## Deployment - Github Action
1. PR open
2. Test by github action
3. Auto-merge when test pass
4. Build as image and push to Docker hub
5. Run the image on the AWS EC2 through github action

## License
This project is licensed under the terms of the MIT license.
