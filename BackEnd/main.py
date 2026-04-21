import sys
import asyncio

# Fix esencial para Uvicorn en Windows: Evita NotImplementedError al lanzar subprocesos (Chromium)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.scraper_service import scrape_profile
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Configuración de CORS para permitir solicitudes del Frontend React + Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/profile/{username}")
def get_profile(username: str):
    print(f"\n[API] Recibida solicitud desde Frontend para scrapear a: {username}")
    try:
        # Al no ser "async def", FastAPI lo ejecuta en un hilo separado. 
        # Aquí creamos un Event Loop nuevo (Proactor por defecto en Python 3.12)
        # evadiendo así el loop defectuoso (SelectorEventLoop) que impone Uvicorn.
        data = asyncio.run(scrape_profile(username))
        
        # Se retorna model_dump() del ProfileStats de Pydantic
        return {"status": "success", "data": data.model_dump()}
    except Exception as e:
        import traceback
        print("[API Error] Falló la extracción en el servicio modular:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
