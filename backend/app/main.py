from fastapi import FastAPI

app = FastAPI(title="AI Panel Studio")


@app.get("/health")
async def health_check():
    return {"status": "ok"}