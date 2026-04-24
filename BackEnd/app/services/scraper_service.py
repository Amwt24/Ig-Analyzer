import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from app.core.config import settings
from app.models.profile import ProfileStats, Post, Comment
from app.services.auth_service import login_and_save_state

async def scrape_profile(username: str) -> ProfileStats:
    # ESTRATEGIA: Primero intentar scraping anónimo (funciona para perfiles públicos).
    # Solo recurrir a sesión autenticada si el perfil es privado o IG bloquea.
    
    try:
        print(f"[ScraperService] Intentando scraping anónimo para {username}...")
        data = await _perform_scrape(username, use_state=False)
        return data
    except Exception as anon_error:
        print(f"[ScraperService] Scraping anónimo falló: {anon_error}")
        
        # Si el anónimo falla, intentar con sesión autenticada
        if os.path.exists(settings.SESSION_FILE):
            print("[ScraperService] Reintentando con session_state.json...")
            try:
                data = await _perform_scrape(username, use_state=True)
                return data
            except Exception as auth_error:
                if "redireccionó a Login" in str(auth_error):
                    print("[ScraperService] Sesión expirada. Eliminando session_state.json...")
                    os.remove(settings.SESSION_FILE)
                else:
                    raise auth_error
        
        # Si hay cookie string en .env, intentar con eso
        if settings.IG_COOKIE_STRING:
            print("[ScraperService] Reintentando con IG_COOKIE_STRING del .env...")
            try:
                data = await _perform_scrape(username, use_state=False, use_cookie_string=True)
                return data
            except Exception as cookie_error:
                print(f"[ScraperService] Cookie string también falló: {cookie_error}")
        
        # Último recurso: intentar auto-login
        if settings.IG_USERNAME and settings.IG_PASSWORD:
            print("[ScraperService] Intentando login autónomo como último recurso...")
            success = await login_and_save_state(headless=True)
            if success:
                data = await _perform_scrape(username, use_state=True)
                return data
        
        # Si todo falla, re-lanzar el error original con más contexto
        raise Exception(f"No se pudo extraer el perfil de '{username}'. Error anónimo: {anon_error}")

async def _perform_scrape(username: str, use_state: bool, use_cookie_string: bool = False) -> ProfileStats:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context_opts = {
            'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if use_state and os.path.exists(settings.SESSION_FILE):
            context_opts['storage_state'] = settings.SESSION_FILE
            
        context = await browser.new_context(**context_opts)
        
        # INYECCIÓN FALLBACK: Si se indica usar cookie string del .env
        if use_cookie_string and settings.IG_COOKIE_STRING:
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
        description_content = await desc_element.get_attribute("content") if desc_element else ""
        
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
                await Stealth().apply_stealth_async(anon_page)
                await anon_page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
                try:
                    anon_data = await anon_page.evaluate('''async (username) => {
                        const res = await fetch(`https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`, {
                            headers: { "x-ig-app-id": "936619743392459" }
                        });
                        return await res.json();
                    }''', username)
                    edges = anon_data.get("data", {}).get("user", {}).get("edge_owner_to_timeline_media", {}).get("edges", [])
                except Exception as e:
                    print(f"[ScraperService] Warning: Anon API evaluate failed {e}")
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

            await browser.close()
            print("[ScraperService] Extracción finalizada con éxito (Vía Fallback Meta)!")
            return ProfileStats(
                username=username,
                display_name=display_name_fallback,
                followers=followers_str,
                following=following_str,
                posts=posts_str,
                profile_pic_url=classic_img_url,
                raw_desc=description_content
            )

async def scrape_posts(username: str) -> list[Post]:
    print(f"[ScraperService] scrape_posts llamado. Delegando a scrape_profile para {username}...")
    profile = await scrape_profile(username)
    return profile.recent_posts or []

async def scrape_post_comments(post_url: str) -> list[Comment]:
    """
    Extrae comentarios de un post usando la API interna de Instagram.
    Estrategia: Navegar al post, ejecutar fetch a la API de comentarios dentro del contexto del navegador.
    """
    # Extraer shortcode de la URL del post
    import re
    shortcode_match = re.search(r'/p/([A-Za-z0-9_-]+)', post_url)
    if not shortcode_match:
        print(f"[ScraperService] No se pudo extraer shortcode de {post_url}")
        return []
    
    shortcode = shortcode_match.group(1)
    print(f"[ScraperService] Extrayendo comentarios del post {shortcode}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        # Intentar primero de forma anónima
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # Navegar al post para establecer cookies de sesión del navegador
        await page.goto(post_url, wait_until="domcontentloaded", timeout=25000)
        
        try:
            await page.wait_for_selector('meta[property="og:description"]', timeout=7000)
        except Exception:
            pass
        
        # Intentar extraer comentarios via API GraphQL interna
        comments_data = []
        try:
            comments_data = await page.evaluate('''async (shortcode) => {
                try {
                    // Método 1: API GraphQL para comentarios
                    const queryHash = "bc3296d44b68399f230bdcb3e52355cb"; // Hash para comentarios
                    const variables = JSON.stringify({
                        shortcode: shortcode,
                        first: 20
                    });
                    
                    const url = `https://www.instagram.com/graphql/query/?query_hash=${queryHash}&variables=${encodeURIComponent(variables)}`;
                    const res = await fetch(url, {
                        headers: {
                            "x-ig-app-id": "936619743392459",
                            "x-requested-with": "XMLHttpRequest"
                        }
                    });
                    
                    if (res.ok) {
                        const data = await res.json();
                        const edges = data?.data?.shortcode_media?.edge_media_to_parent_comment?.edges || 
                                      data?.data?.shortcode_media?.edge_media_to_comment?.edges || [];
                        
                        return edges.slice(0, 15).map(edge => ({
                            username: edge.node?.owner?.username || "unknown",
                            text: edge.node?.text || ""
                        })).filter(c => c.text.length > 0);
                    }
                } catch(e) {
                    console.log("GraphQL failed:", e);
                }
                
                try {
                    // Método 2: API v1 web_info
                    const res2 = await fetch(`https://www.instagram.com/api/v1/media/${shortcode}/comments/?can_support_threading=true&permalink_enabled=false`, {
                        headers: {
                            "x-ig-app-id": "936619743392459"
                        }
                    });
                    
                    if (res2.ok) {
                        const data2 = await res2.json();
                        const comments = data2?.comments || [];
                        return comments.slice(0, 15).map(c => ({
                            username: c.user?.username || "unknown",
                            text: c.text || ""
                        })).filter(c => c.text.length > 0);
                    }
                } catch(e2) {
                    console.log("V1 API failed:", e2);
                }
                
                return [];
            }''', shortcode)
        except Exception as e:
            print(f"[ScraperService] API evaluate para comentarios falló: {e}")
        
        # Fallback: DOM scraping si la API no devolvió nada
        if not comments_data:
            print("[ScraperService] API de comentarios no respondió. Usando DOM fallback...")
            try:
                await page.wait_for_timeout(3000)
                comments_data = await page.evaluate('''() => {
                    const comments = [];
                    for (let el of Array.from(document.querySelectorAll('h3'))) {
                        if (comments.length >= 15) break;
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
                    return comments.slice(1, 16);
                }''')
            except Exception as e:
                print(f"[ScraperService] DOM fallback también falló: {e}")
        
        comments = []
        for c in comments_data:
            if c.get('text'):
                comments.append(Comment(username=c['username'], text=c['text']))
        
        await browser.close()
        print(f"[ScraperService] Comentarios extraídos: {len(comments)}")
        return comments

