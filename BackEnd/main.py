import sys
import asyncio

# Fix esencial para Uvicorn en Windows: Evita NotImplementedError al lanzar subprocesos (Chromium)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.scraper_service import scrape_profile, scrape_posts, scrape_post_comments
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

@app.get("/api/profile/{username}/posts")
def get_user_posts(username: str):
    print(f"\n[API] Solicitud para extraer posts de: {username}")
    try:
        posts = asyncio.run(scrape_posts(username))
        posts_dict = [p.model_dump() for p in posts]
        
        # Guardar en MongoDB si está configurado
        if sync_collection is not None:
            sync_collection.update_one(
                {"username": username},
                {"$set": {"recent_posts": posts_dict}},
                upsert=True
            )
            print(f"[MongoDB] Posts de {username} guardados/actualizados.")
            
        return {"status": "success", "data": posts_dict}
    except Exception as e:
        print("[API Error] Falló la extracción de posts:")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/post/comments")
def get_post_comments(url: str = Query(...), username: str = Query(None)):
    print(f"\n[API] Solicitud para extraer comentarios del post: {url}")
    try:
        comments = asyncio.run(scrape_post_comments(url))
        comments_dict = [c.model_dump() for c in comments]
        
        # Si pasamos el username, podemos vincular el comentario en la DB
        if sync_collection is not None and username:
            sync_collection.update_one(
                {"username": username, "recent_posts.url": url},
                {"$set": {"recent_posts.$.comments": comments_dict}}
            )
            print(f"[MongoDB] Comentarios añadidos al post {url} de {username}.")
            
        return {"status": "success", "data": comments_dict}
    except Exception as e:
        print("[API Error] Falló la extracción de comentarios:")
        import traceback
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
