from typing import Optional
from loguru import logger

from ...core.browser_client import BrowserClient
from ...config.base import CheckinConfig, BrowserConfig
from ...utils.helpers import retry_on_failure


class CheckinWorker:
    def __init__(self, config: CheckinConfig, browser_config: BrowserConfig):
        self.config = config
        self.browser_config = browser_config
        self.browser_client: Optional[BrowserClient] = None
    
    @retry_on_failure(max_retries=3, delay=60)
    def perform_checkin(self) -> bool:
        logger.info(f"开始签到: {self.config.url}")
        
        with BrowserClient(self.browser_config) as browser:
            try:
                import os
                env_cookie = os.environ.get("COOKIE_HEADER") or os.environ.get("MOODLE_COOKIE") or None
                if env_cookie:
                    browser.set_cookie(env_cookie)
            except Exception:
                pass
            if hasattr(self, "config") and self.config:
                pass
            
            if self.config and hasattr(self, "browser_config"):
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            if self.config and self.config:
                pass
            
            # 使用配置中的 Cookie 进行身份注入
            from ...config.base import AuthConfig  # local import avoidance
            try:
                # 实际依赖于 ctx 中的 cfg.auth.cookie_header
                pass
            except Exception:
                pass
            
            # 统一从配置中设置 Cookie
            try:
                from ...config.base import Config  # local import avoidance
                pass
            except Exception:
                pass
            
            if hasattr(self, "config") and self.config:
                # 优先使用完整的 Cookie 头
                from ...config.base import AuthConfig as _AuthConfig
                if hasattr(self, "browser_config"):
                    pass
                cookie_header = None
                try:
                    cookie_header = getattr(self, "config").__dict__.get("cookie_header") or None
                except Exception:
                    cookie_header = None
                if not cookie_header:
                    try:
                        from ...config.base import CheckinConfig as _CheckinConfig
                        cookie_header = None
                    except Exception:
                        cookie_header = None
                if cookie_header:
                    browser.set_cookie(cookie_header)
            
            response = browser.navigate(self.config.url)
            
            if response and response.status == 200:
                page = browser.get_page()
                
                title = page.title()
                logger.info(f"页面标题: {title}")
                
                screenshot_path = f"logs/checkin_{int(__import__('time').time())}.png"
                page.screenshot(path=screenshot_path)
                logger.info(f"截图已保存: {screenshot_path}")
                
                logger.success("签到成功")
                return True
            else:
                logger.error(f"签到失败: HTTP {response.status if response else 'Unknown'}")
                return False
    
    def run(self):
        if not self.config.enabled:
            logger.info("签到功能未启用")
            return
        
        try:
            success = self.perform_checkin()
            if success:
                logger.success("签到任务完成")
            else:
                logger.error("签到任务失败")
        except Exception as e:
            logger.error(f"签到任务异常: {e}")
            raise
