import asyncio
import os
import traceback
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from dotenv import load_dotenv

load_dotenv()

def build_playwright_cookies(cookie_string: str):
    cookies = []
    if not cookie_string:
        return cookies
    cookie_string = cookie_string.strip('\'"')
    for pair in cookie_string.split(";"):
        if "=" in pair:
            key, val = pair.strip().split("=", 1)
            val = val.strip('\'"')
            cookies.append({
                "name": key,
                "value": val,
                "domain": ".instagram.com",
                "path": "/"
            })
    return cookies

async def main():
    cookie_str = os.getenv("IG_COOKIE_STRING", "")
    cookies_list = build_playwright_cookies(cookie_str)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            
            if cookies_list:
                await context.add_cookies(cookies_list)
            
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            url = f"https://www.instagram.com/andersliinky/"
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            try:
                await page.wait_for_selector('meta[property="og:description"]', timeout=7000)
            except Exception:
                pass 

            if "/accounts/login" in page.url:
                await browser.close()
                print({"error": True, "message": "Instagram redireccionó a Login. Tus cookies están expiradas o vacías en .env"})
                return
            
            desc_element = await page.query_selector('meta[property="og:description"]')
            img_element = await page.query_selector('meta[property="og:image"]')
            
            description_content = await desc_element.get_attribute("content") if desc_element else ""
            img_url = await img_element.get_attribute("content") if img_element else ""
            title_content = await page.title()
            
            await browser.close()
            
            if not description_content:
                 print({"error": True, "message": f"No se pudo extraer la info de OG:Meta. Cuenta privada, baneada o no existe. Titulo devuelto: {title_content}"})
                 return
                 
            data_parts = description_content.split("-")[0].strip()
            stats = data_parts.split(", ")
            
            followers, following, posts = "0", "0", "0"
            for stat in stats:
                val = stat.split(" ")[0].strip()
                if "Follower" in stat: followers = val
                elif "Following" in stat: following = val
                elif "Post" in stat: posts = val
            
            display_name = title_content.split("(@")[0].strip() if "(@" in title_content else "andersliinky"

            print({
                "username": "andersliinky",
                "display_name": display_name,
                "followers": followers,
                "following": following,
                "posts": posts,
                "profile_pic_url": img_url
            })
            
    except Exception as e:
        print("ERROR THROWN:")
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
