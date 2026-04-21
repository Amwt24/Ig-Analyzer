import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from app.core.config import settings
from app.models.profile import ProfileStats
from app.services.auth_service import login_and_save_state

async def scrape_profile(username: str) -> ProfileStats:
    # Asegurar que exista state o fallbacks
    if not os.path.exists(settings.SESSION_FILE):
        if settings.IG_COOKIE_STRING:
            print("[ScraperService] No se encontró session_state.json. Se utilizarán cookies del .env como fallback.")
        else:
            print("[ScraperService] No se encontró session_state.json ni cookies. Delegando a AuthService...")
            success = await login_and_save_state(headless=True)
            if not success:
                raise Exception("No se pudo regenerar la sesión automáticamente ni hay cookies de fallback.")
                
    # Intento de scrape
    try:
        data = await _perform_scrape(username, use_state=True)
        return data
    except Exception as e:
        # Si hubo un problema de redirección (cookie caducada o baneada)
        if "redireccionó a Login" in str(e):
            print("[ScraperService] La sesión guardada expiró de repente. Regenerando desde 0...")
            if os.path.exists(settings.SESSION_FILE):
                os.remove(settings.SESSION_FILE)
                
            success = await login_and_save_state(headless=True)
            if not success:
                raise Exception("No se pudo iniciar sesión para refrescar la cookie vencida.")
            
            # Reintentamos UNA sola vez la extracción
            data = await _perform_scrape(username, use_state=True)
            return data
        else:
            raise e

async def _perform_scrape(username: str, use_state: bool) -> ProfileStats:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context_opts = {}
        if use_state and os.path.exists(settings.SESSION_FILE):
            context_opts['storage_state'] = settings.SESSION_FILE
            
        context = await browser.new_context(**context_opts)
        
        # INYECCIÓN FALLBACK: Si no hay state pero hay cookie string en .env
        if not os.path.exists(settings.SESSION_FILE) and settings.IG_COOKIE_STRING:
            print("[ScraperService] Inyectando session_id desde IG_COOKIE_STRING...")
            cookies_list = []
            for chunk in settings.IG_COOKIE_STRING.split(";"):
                if "=" in chunk:
                    name, value = chunk.split("=", 1)
                    cookies_list.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".instagram.com",
                        "path": "/"
                    })
            if cookies_list:
                await context.add_cookies(cookies_list)

        page = await context.new_page()
        
        await Stealth().apply_stealth_async(page)
        
        url = f"https://www.instagram.com/{username}/"
        print(f"[ScraperService] Navegando silenciosamente a {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        try:
            await page.wait_for_selector('meta[property="og:description"]', timeout=7000)
        except Exception:
            pass 

        if "/accounts/login" in page.url:
            await browser.close()
            raise Exception("Instagram redireccionó a Login. Sesión inválida.")
        
        desc_element = await page.query_selector('meta[property="og:description"]')
        img_element = await page.query_selector('meta[property="og:image"]')
        title_content = await page.title()
        
        description_content = await desc_element.get_attribute("content") if desc_element else ""
        img_url = await img_element.get_attribute("content") if img_element else ""
        
        await browser.close()
        
        if not description_content:
             raise Exception(f"No se pudo extraer OG:Meta. ¿Cuenta bloqueada u oculta? Titulo: {title_content}")
             
        # Parseo exacto
        data_parts = description_content.split("-")[0].strip()
        stats = data_parts.split(", ")
        
        followers, following, posts = "0", "0", "0"
        for stat in stats:
            val = stat.split(" ")[0].strip()
            if "Follower" in stat: followers = val
            elif "Following" in stat: following = val
            elif "Post" in stat: posts = val
        
        display_name = title_content.split("(@")[0].strip() if "(@" in title_content else username

        print("[ScraperService] Extracción finalizada con éxito!")
        return ProfileStats(
            username=username,
            display_name=display_name,
            followers=followers,
            following=following,
            posts=posts,
            profile_pic_url=img_url,
            raw_desc=description_content
        )
