import asyncio
from app.services.scraper_service import scrape_profile

async def test():
    try:
        print("====== SCRAPER PIPELINE TEST ======")
        # Vamos a raspar adorn_quran pero usando nuestra nueva arquitectura con Login Autónomo
        res = await scrape_profile("adorn_quran")
        print("====== RESULTADO DE EXTRACCIÓN ======")
        print(res.model_dump_json(indent=2))
        print("=====================================")
    except Exception as e:
        import traceback
        print("--- FALLO LOCAL ---")
        print(traceback.format_exc())
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test())
