import motor.motor_asyncio
from pymongo import MongoClient
from app.core.config import settings

# Conexión asíncrona (para endpoints async)
async_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI) if settings.MONGODB_URI else None
async_collection = async_client.iganalyzer.dbigp if async_client else None

# Conexión síncrona (para endpoints sync que se ejecutan en threadpool)
sync_client = MongoClient(settings.MONGODB_URI) if settings.MONGODB_URI else None
sync_collection = sync_client.iganalyzer.dbigp if sync_client else None
