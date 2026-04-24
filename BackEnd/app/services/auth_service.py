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
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Stealth para login tambien
            await Stealth().apply_stealth_async(page)
            
            # Usar domcontentloaded y esperar manualmente para ser más resiliente
            print("[AuthService] Navegando a login page...")
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=40000)

            # Intentar cerrar el banner de cookies si aparece
            try:
                # Selectores comunes para botones de cookies en IG
                cookie_selectors = [
                    'button:has-text("Allow all cookies")',
                    'button:has-text("Permitir todas las cookies")',
                    'button:has-text("Allow essential and optional cookies")',
                    'button._a9--._a9_0', # Clase común para botones de modal
                    'div[role="dialog"] button:first-child'
                ]
                for selector in cookie_selectors:
                    if await page.query_selector(selector):
                        print(f"[AuthService] Detectado banner de cookies ({selector}), haciendo click...")
                        await page.click(selector)
                        await asyncio.sleep(1)
                        break
            except Exception:
                pass

            print("[AuthService] Esperando inputs de login...")
            try:
                # Aumentar timeout a 45s y usar un selector más genérico si falla
                await page.wait_for_selector('input[name="username"]', state="visible", timeout=45000)
            except Exception as e:
                print(f"[AuthService] Timeout en selector de login. Reintentando con selector genérico...")
                try:
                    await page.wait_for_selector('input', state="visible", timeout=10000)
                except:
                    html_content = await page.content()
                    with open("debug.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    raise e

            
            print("[AuthService] Ingresando credenciales...")
            # Intentar diferentes nombres de campos (IG a veces usa email/pass en versiones reducidas)
            user_field = await page.query_selector('input[name="username"]') or await page.query_selector('input[name="email"]')
            pass_field = await page.query_selector('input[name="password"]') or await page.query_selector('input[name="pass"]')

            if not user_field or not pass_field:
                print("[AuthService] ERROR: No se encontraron los campos de login.")
                await browser.close()
                return False

            await user_field.fill(settings.IG_USERNAME)
            await asyncio.sleep(0.5)
            await pass_field.fill(settings.IG_PASSWORD)
            await asyncio.sleep(1)
            
            print("[AuthService] Enviando formulario (Enter)...")
            await page.keyboard.press("Enter")
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
