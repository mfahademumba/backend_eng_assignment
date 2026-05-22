from fastapi import FastAPI

app = FastAPI(title="backend-eng-assignment")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "backend-eng-assignment is running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
