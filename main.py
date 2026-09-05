from fastapi import FastAPI
from app.routers import measurements

app = FastAPI(
    title="API de Monitoreo de Calidad de Agua",
    description="Backend para ingesta IoT (ESP32-S) y consultas",
    version="1.0.0"
)

app.include_router(measurements.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "API de Calidad de Agua funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)