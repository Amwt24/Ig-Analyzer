import sys
import asyncio

# Fix esencial para Uvicorn en Windows: Evita NotImplementedError al lanzar subprocesos (Chromium)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.scraper_service import scrape_profile
from app.core.config import settings
from app.core.database import sync_collection, async_collection
from datetime import datetime

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
        data_dict = data.model_dump()
        
        # Guardar en MongoDB si está configurado
        if sync_collection is not None:
            data_dict["last_scraped"] = datetime.utcnow().isoformat()
            sync_collection.update_one(
                {"username": data_dict["username"]},
                {"$set": data_dict},
                upsert=True
            )
            print(f"[MongoDB] Perfil de {username} guardado/actualizado en dbigp.")
            
        return {"status": "success", "data": data_dict}
    except Exception as e:
        import traceback
        print("[API Error] Falló la extracción en el servicio modular:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_history():
    if async_collection is None:
        raise HTTPException(status_code=500, detail="MongoDB no está configurado.")
    try:
        # Recuperar los últimos 50 perfiles guardados, ordenados por fecha descendente
        cursor = async_collection.find({}, {"_id": 0}).sort("last_scraped", -1).limit(50)
        history = await cursor.to_list(length=50)
        return {"status": "success", "data": history}
    except Exception as e:
        print("[API Error] Falló al obtener historial de MongoDB:")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
