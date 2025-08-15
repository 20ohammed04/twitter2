import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://twitter.com/login")
        print("سجل الدخول يدويًا، ثم اضغط Enter هنا لحفظ الجلسة...")
        input()
        await context.storage_state(path="storage_state.json")
        print("تم حفظ حالة الجلسة في storage_state.json")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

