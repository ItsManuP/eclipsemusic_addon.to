from fastapi import FastAPI

app = FastAPI()

@app.get("/search")
async def search(q: str):
    return {"message": f"Ricerca per: {q}", "status": "ok"}

@app.get("/")
async def root():
    return {"message": "API funzionante"}
