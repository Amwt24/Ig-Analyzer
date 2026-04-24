import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from app.core.config import settings
from app.models.profile import ProfileStats, Post, Comment
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
        
        # Guardamos la imagen clásica que funcionaba antes (no expira rápido)
        classic_img_url = await img_element.get_attribute("content") if img_element else ""
        
        api_data = None
        try:
            api_data = await page.evaluate('''async (username) => {
                const res = await fetch(`https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`, {
                    headers: {
                        "x-ig-app-id": "936619743392459"
                    }
                });
                return await res.json();
            }''', username)
        except Exception as e:
            print(f"[ScraperService] Warning: API evaluate failed {e}")
        
        if api_data and api_data.get("data", {}).get("user"):
            user = api_data["data"]["user"]
            followers = str(user.get("edge_followed_by", {}).get("count", 0))
            following = str(user.get("edge_follow", {}).get("count", 0))
            posts = str(user.get("edge_owner_to_timeline_media", {}).get("count", 0))
            display_name = user.get("full_name", username)
            img_url = classic_img_url or user.get("profile_pic_url_hd", "") or user.get("profile_pic_url", "")
            biography = user.get("biography", "")
            category = user.get("category_name", "")
            external_url = user.get("external_url", "")
            
            recent_posts = []
            edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
            
            # Si las cookies inyectadas provocan que Instagram oculte los posts (0 edges)
            # abrimos un contexto anónimo rápido para recuperarlos
            if len(edges) == 0:
                print("[ScraperService] Las cookies ocultaron los posts. Reintentando de forma anónima...")
                anon_context = await browser.new_context()
                anon_page = await anon_context.new_page()
                await anon_page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
                anon_data = await anon_page.evaluate('''async (username) => {
                    const res = await fetch(`https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`, {
                        headers: { "x-ig-app-id": "936619743392459" }
                    });
                    return await res.json();
                }''', username)
                edges = anon_data.get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {}).get("edges", [])
                await anon_context.close()
                print(f"[ScraperService] Posts encontrados anónimamente: {len(edges)}")

            for edge in edges[:10]:
                node = edge.get("node", {})
                shortcode = node.get("shortcode")
                post_img_url = node.get("display_url")
                caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                caption = caption_edges[0]["node"]["text"] if caption_edges else ""
                if shortcode:
                    recent_posts.append(Post(url=f"https://www.instagram.com/p/{shortcode}/", image_url=post_img_url, caption=caption))
            
            await browser.close()
            print("[ScraperService] Extracción finalizada con éxito (Vía API interna)!")
            return ProfileStats(
                username=username,
                display_name=display_name,
                followers=followers,
                following=following,
                posts=posts,
                profile_pic_url=img_url,
                raw_desc=biography,
                biography=biography,
                category=category,
                external_url=external_url,
                recent_posts=recent_posts
            )
        else:
            # Fallback a Meta Tags si la API falla
            if not description_content:
                 raise Exception(f"No se pudo extraer OG:Meta. ¿Cuenta bloqueada u oculta? Titulo: {title_content}")
                 
            # Parseo exacto
            data_parts = description_content.split("-")[0].strip()
            stats = data_parts.split(", ")
            
            followers_str, following_str, posts_str = "0", "0", "0"
            for stat in stats:
                val = stat.split(" ")[0].strip()
                if "Follower" in stat: followers_str = val
                elif "Following" in stat: following_str = val
                elif "Post" in stat: posts_str = val
            
            display_name_fallback = title_content.split("(@")[0].strip() if "(@" in title_content else username

            print("[ScraperService] Extracción finalizada con éxito (Vía Fallback Meta)!")
            return ProfileStats(
                username=username,
                display_name=display_name_fallback,
                followers=followers_str,
                following=following_str,
                posts=posts_str,
                profile_pic_url=img_url,
                raw_desc=description_content
            )

async def scrape_posts(username: str) -> list[Post]:
    print(f"[ScraperService] scrape_posts llamado. Delegando a scrape_profile para {username}...")
    profile = await scrape_profile(username)
    return profile.recent_posts or []

async def scrape_post_comments(post_url: str) -> list[Comment]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context_opts = {}
        if os.path.exists(settings.SESSION_FILE):
            context_opts['storage_state'] = settings.SESSION_FILE
            
        context = await browser.new_context(**context_opts)
        
        if not os.path.exists(settings.SESSION_FILE) and settings.IG_COOKIE_STRING:
            cookies_list = []
            for chunk in settings.IG_COOKIE_STRING.split(";"):
                if "=" in chunk:
                    name, value = chunk.split("=", 1)
                    cookies_list.append({"name": name.strip(), "value": value.strip(), "domain": ".instagram.com", "path": "/"})
            if cookies_list:
                await context.add_cookies(cookies_list)

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        print(f"[ScraperService] Buscando comentarios en {post_url}...")
        await page.goto(post_url, wait_until="domcontentloaded", timeout=25000)
        
        try:
            await page.wait_for_selector('ul', timeout=10000)
            await page.wait_for_timeout(2000)
        except Exception:
            print("[ScraperService] No se cargaron los comentarios o timeout.")
            
        comments_data = await page.evaluate('''() => {
            const comments = [];
            const h3s = document.querySelectorAll('h3, span[dir="auto"]');
            
            // Heurística robusta buscando autores
            const elements = document.querySelectorAll('ul li, article div[role="button"]');
            
            for (let el of Array.from(document.querySelectorAll('h3'))) {
                if (comments.length >= 10) break;
                const username = el.textContent.trim();
                if (!username) continue;
                
                let parent = el.parentElement;
                if(parent) parent = parent.parentElement;
                
                if (parent) {
                    const texts = Array.from(parent.querySelectorAll('span[dir="auto"], div[dir="auto"]'))
                                     .map(e => e.textContent.trim())
                                     .filter(t => t !== username && t !== 'Verified' && t.length > 0 && t !== 'Reply');
                    
                    if(texts.length > 0) {
                        comments.push({username: username, text: texts[0]});
                    }
                }
            }
            return comments.slice(1, 11); // Omitimos el primer H3 (suele ser el caption del dueño)
        }''')

        comments = []
        for c in comments_data:
            comments.append(Comment(username=c['username'], text=c['text']))
            
        await browser.close()
        return comments
