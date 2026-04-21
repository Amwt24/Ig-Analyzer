import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from app.core.config import settings

async def login_and_save_state(headless: bool = True) -> bool:
    print("\n[AuthService] Iniciando secuencia de Login Autónomo en Instagram...")
    if not settings.IG_USERNAME or not settings.IG_PASSWORD:
        print("[AuthService] ERROR: Credenciales no encontradas en .env")
        return False
        
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()
            
            # Stealth para login tambien
            await Stealth().apply_stealth_async(page)
            
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            
            print("[AuthService] Esperando inputs de login...")
            try:
                await page.wait_for_selector('input[name="username"]', timeout=15000)
            except Exception as e:
                print(f"[AuthService] Timeout en selector de login. Volcando codigo fuente para debuggear...")
                html_content = await page.content()
                with open("debug.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                raise e
            
            print("[AuthService] Ingresando credenciales...")
            # Escribir lentamente emula a un humano
            await page.fill('input[name="username"]', settings.IG_USERNAME)
            await asyncio.sleep(0.5)
            await page.fill('input[name="password"]', settings.IG_PASSWORD)
            
            await asyncio.sleep(1)
            await page.click('button[type="submit"]')
            
            print("[AuthService] Validando respuesta de Instagram...")
            # Esperamos 6 segundos fijos en vez de vigilar la URL exacta ya que IG redirecciona a paginas de onboarding como "Guardar info"
            await asyncio.sleep(6)
            
            # Chequeamos errores visibles ("La contraseña es incorrecta" etc)
            error_msg = await page.query_selector('p#slfErrorAlert')
            if error_msg:
                err_text = await error_msg.inner_text()
                print(f"[AuthService] Instagram rechazó el login: {err_text}")
                await browser.close()
                return False

            if "/accounts/login" in page.url:
                # O la página nunca navegó, o se requirió 2FA, o bloqueo sospechoso.
                print("[AuthService] Fallo crítico. La página se estancó en Login.")
                await browser.close()
                return False

            print("[AuthService] Capturando cookies de sesión...")
            await context.storage_state(path=settings.SESSION_FILE)
            print(f"[AuthService] OK! Login exitoso! Sesión fresca almacenada.")
            
            await browser.close()
            return True
            
    except Exception as e:
        print(f"[AuthService] Excepción durante el login autónomo: {e}")
        return False

# Esto permite ejecutar directamente solo el Auth Service para probar el UI de login
if __name__ == "__main__":
    asyncio.run(login_and_save_state(headless=False))
