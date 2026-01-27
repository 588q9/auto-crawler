import re
from typing import Optional, Dict
import requests
from loguru import logger

from ...config.base import CheckinConfig
from ...utils.helpers import retry_on_failure


class ApiCheckinWorker:
    def __init__(self, config: CheckinConfig, cookie_header: Optional[str] = None, api_user: Optional[str] = None):
        self.config = config
        self.cookie_header = cookie_header
        self.api_user = api_user

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.cookie_header:
            headers["Cookie"] = self.cookie_header
        if self.api_user:
            headers["New-API-User"] = self.api_user
        return headers

    @retry_on_failure(max_retries=3, delay=60)
    def perform_checkin(self) -> bool:
        headers = self._build_headers()
        logger.info(f"POST {self.config.url}")
        resp = requests.post(self.config.url, headers=headers, json={})
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text, "success": resp.ok}

        msg = str(data.get("message", "")) if isinstance(data, dict) else str(data)
        ok = bool(data.get("success")) if isinstance(data, dict) else resp.ok

        if re.search(r"签到.*(完成|成功)", msg):
            logger.success(f"签到成功: {msg}")
            return True
        if "今日已签到" in msg:
            logger.info("今日已签到，视为完成")
            return True
        if ok:
            logger.info(f"接口返回成功: {msg}")
            return True
        logger.error(f"签到失败: {msg}")
        return False

    def run(self):
        if not self.config.enabled:
            logger.info("签到功能未启用")
            return False
        try:
            success = self.perform_checkin()
        except Exception as e:
            logger.error(f"签到任务异常：{e}")
            return False
        if success:
            logger.success("签到任务完成")
            return True
        logger.error("签到任务失败")
        return False
