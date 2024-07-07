from fastapi import FastAPI

app = FastAPI()


@app.get("/test")
async def test_endpoint() -> dict[str, str]:
    return {"message": "Hello, this is a test endpoint!"}


@app.get("/test-cicd")
async def test_cicd() -> dict[str, str]:
    return {"message": "Hello, this is a test cicd!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
