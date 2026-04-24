"""
Debug v3: Check if comments render in DOM, and test with session state
"""
import asyncio
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

POST_URL = "https://www.instagram.com/p/DXeh-kYiIge/"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "session_state.json")

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        # Test 1: Anonymous
        print("=" * 60)
        print("TEST 1: ANONIMO")
        print("=" * 60)
        ctx1 = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page1 = await ctx1.new_page()
        await Stealth().apply_stealth_async(page1)
        await page1.goto(POST_URL, wait_until="networkidle", timeout=30000)
        await page1.wait_for_timeout(5000)
        
        # Count h3 and spans
        dom1 = await page1.evaluate(r'''() => {
            const h3s = Array.from(document.querySelectorAll("h3"));
            const lis = Array.from(document.querySelectorAll("ul > li"));
            return {
                h3_count: h3s.length,
                h3_texts: h3s.slice(0, 5).map(h => h.textContent.trim().substring(0, 40)),
                li_count: lis.length,
                body_text_len: document.body.innerText.length
            };
        }''')
        print(f"  DOM: {dom1}")
        
        # Try to get media_id and use v1 comments WITH the page cookies
        mid_result = await page1.evaluate(r'''() => {
            const meta = document.querySelector('meta[property="al:ios:url"]');
            if (meta) {
                const match = (meta.getAttribute("content") || "").match(/id=(\d+)/);
                if (match) return match[1];
            }
            return null;
        }''')
        print(f"  media_id: {mid_result}")
        
        if mid_result:
            # Try the comments endpoint with cookies (session context of the browser)
            comments1 = await page1.evaluate(r'''async (mid) => {
                try {
                    const res = await fetch(`https://www.instagram.com/api/v1/media/${mid}/comments/?can_support_threading=true&permalink_enabled=false`, {
                        headers: { "x-ig-app-id": "936619743392459" },
                        credentials: "include"
                    });
                    if (res.status !== 200) return { status: res.status, error: "non-200" };
                    const ct = res.headers.get("content-type") || "";
                    if (!ct.includes("json")) return { status: res.status, error: "not-json", ct: ct };
                    const data = await res.json();
                    const comments = (data.comments || []).slice(0, 5);
                    return {
                        status: res.status,
                        comment_count: (data.comments || []).length,
                        samples: comments.map(c => ({ user: c.user?.username, text: (c.text || "").substring(0, 60) }))
                    };
                } catch(e) {
                    return { error: e.toString() };
                }
            }''', mid_result)
            print(f"  v1 comments (anon): {comments1}")
        
        await ctx1.close()
        
        # Test 2: With session_state.json (if exists)
        print("\n" + "=" * 60)
        print("TEST 2: CON SESION")
        print("=" * 60)
        
        if os.path.exists(SESSION_FILE):
            print(f"  session_state.json encontrado!")
            ctx2 = await browser.new_context(
                storage_state=SESSION_FILE,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page2 = await ctx2.new_page()
            await Stealth().apply_stealth_async(page2)
            await page2.goto(POST_URL, wait_until="networkidle", timeout=30000)
            await page2.wait_for_timeout(5000)
            
            url2 = page2.url
            print(f"  URL: {url2}")
            
            if "/accounts/login" not in url2:
                dom2 = await page2.evaluate(r'''() => {
                    const h3s = Array.from(document.querySelectorAll("h3"));
                    const lis = Array.from(document.querySelectorAll("ul > li"));
                    return {
                        h3_count: h3s.length,
                        h3_texts: h3s.slice(0, 10).map(h => h.textContent.trim().substring(0, 40)),
                        li_count: lis.length
                    };
                }''')
                print(f"  DOM: {dom2}")
                
                if mid_result:
                    comments2 = await page2.evaluate(r'''async (mid) => {
                        try {
                            const res = await fetch(`https://www.instagram.com/api/v1/media/${mid}/comments/?can_support_threading=true&permalink_enabled=false`, {
                                headers: { "x-ig-app-id": "936619743392459" },
                                credentials: "include"
                            });
                            if (res.status !== 200) return { status: res.status, error: "non-200" };
                            const ct = res.headers.get("content-type") || "";
                            if (!ct.includes("json")) return { status: res.status, error: "not-json", ct: ct };
                            const data = await res.json();
                            const comments = (data.comments || []).slice(0, 5);
                            return {
                                status: res.status,
                                comment_count: (data.comments || []).length,
                                samples: comments.map(c => ({ user: c.user?.username, text: (c.text || "").substring(0, 60) }))
                            };
                        } catch(e) {
                            return { error: e.toString() };
                        }
                    }''', mid_result)
                    print(f"  v1 comments (auth): {comments2}")
            else:
                print("  REDIRIGIDO A LOGIN - sesion invalida")
                
            await ctx2.close()
        else:
            print(f"  NO existe session_state.json")
            print(f"  Intentando login para generar sesion...")
            
            # Quick login
            from app.services.auth_service import login_and_save_state
            success = await login_and_save_state(headless=True)
            print(f"  Login result: {success}")
            
            if success and os.path.exists(SESSION_FILE):
                ctx3 = await browser.new_context(
                    storage_state=SESSION_FILE,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page3 = await ctx3.new_page()
                await Stealth().apply_stealth_async(page3)
                await page3.goto(POST_URL, wait_until="networkidle", timeout=30000)
                await page3.wait_for_timeout(5000)
                
                if mid_result:
                    comments3 = await page3.evaluate(r'''async (mid) => {
                        try {
                            const res = await fetch(`https://www.instagram.com/api/v1/media/${mid}/comments/?can_support_threading=true&permalink_enabled=false`, {
                                headers: { "x-ig-app-id": "936619743392459" },
                                credentials: "include"
                            });
                            if (res.status !== 200) return { status: res.status };
                            const ct = res.headers.get("content-type") || "";
                            if (!ct.includes("json")) return { status: res.status, error: "not-json" };
                            const data = await res.json();
                            const comments = (data.comments || []).slice(0, 5);
                            return {
                                status: res.status,
                                comment_count: (data.comments || []).length,
                                samples: comments.map(c => ({ user: c.user?.username, text: (c.text || "").substring(0, 60) }))
                            };
                        } catch(e) {
                            return { error: e.toString() };
                        }
                    }''', mid_result)
                    print(f"  v1 comments (fresh auth): {comments3}")
                    
                await ctx3.close()
        
        await browser.close()
        print("\n[DONE]")

if __name__ == "__main__":
    asyncio.run(debug())
