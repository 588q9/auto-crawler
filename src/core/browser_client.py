from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from ..config.base import BrowserConfig


class BrowserClient:
    def __init__(self, config: BrowserConfig):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.config.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        self.context = self.browser.new_context(
            user_agent=self.config.user_agent,
            viewport={"width": 1920, "height": 1080}
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.timeout)
    
    def stop(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def set_cookie(self, cookie_header: str):
        if not self.context:
            raise RuntimeError("Browser not started")
        
        cookies = []
        for item in cookie_header.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".gdut.edu.cn",
                    "path": "/"
                })
        
        self.context.add_cookies(cookies)
    
    def navigate(self, url: str):
        if not self.page:
            raise RuntimeError("Browser not started")
        return self.page.goto(url)
    
    def get_page(self) -> Page:
        if not self.page:
            raise RuntimeError("Browser not started")
        return self.page
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
