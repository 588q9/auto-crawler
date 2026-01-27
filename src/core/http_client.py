import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class MoodleClient:
    def __init__(self, base_url: str, cookie_header: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        
        if cookie_header:
            self._set_cookie(cookie_header)
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
    
    def _set_cookie(self, cookie_header: str):
        cookies = {}
        for item in cookie_header.split(";"):
            item = item.strip()
            if "=" in item:
                name, value = item.split("=", 1)
                cookies[name.strip()] = value.strip()
        self.session.cookies.update(cookies)
    
    def get(self, path: str, **kwargs) -> requests.Response:
        url = urljoin(self.base_url, path)
        return self.session.get(url, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        url = urljoin(self.base_url, path)
        return self.session.post(url, **kwargs)
    
    def get_my_courses_page(self) -> str:
        resp = self.get("/my/")
        resp.raise_for_status()
        return resp.text
    
    def parse_m_cfg(self, html: str) -> Dict[str, Any]:
        m_cfg = {}
        pattern = r'M\.cfg\s*=\s*({[^;]+});'
        match = re.search(pattern, html)
        if match:
            try:
                m_cfg = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return m_cfg
    
    def extract_sesskey(self, html: str) -> Optional[str]:
        pattern = r'"sesskey"\s*:\s*"([^"]+)"'
        match = re.search(pattern, html)
        return match.group(1) if match else None
    
    def extract_fsresource_info(self, html: str) -> Dict[str, Any]:
        info = {}
        pattern = r'playerdata\s*=\s*({[^;]+});'
        match = re.search(pattern, html)
        if match:
            try:
                info = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return info
    
    def get_course_module_info(self, cmid: int, html_context: Optional[str] = None) -> Dict[str, Any]:
        sesskey = None
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        
        if not sesskey:
            return {}
        
        payload = [{
            "index": 0,
            "methodname": "core_course_get_course_module",
            "args": {
                "cmid": cmid
            }
        }]
        
        try:
            resp = self.post("/lib/ajax/service.php?sesskey=" + sesskey, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return data[0].get("data", {})
        except Exception:
            pass
        
        return {}
    
    def post_service(self, payload: List[Dict], html_context: Optional[str] = None, timestamp: Optional[int] = None) -> Any:
        sesskey = None
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        
        if not sesskey:
            raise ValueError("Cannot find sesskey")
        
        url = f"/lib/ajax/service.php?sesskey={sesskey}"
        if timestamp:
            url += f"&info={timestamp}"
        
        resp = self.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def post_service_capture(self, payload: List[Dict], html_context: Optional[str] = None, timestamp: Optional[int] = None) -> Dict[str, Any]:
        sesskey = None
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        
        if not sesskey:
            raise ValueError("Cannot find sesskey")
        
        url = f"/lib/ajax/service.php?sesskey={sesskey}"
        if timestamp:
            url += f"&info={timestamp}"
        
        resp = self.post(url, json=payload)
        resp.raise_for_status()
        
        try:
            json_data = resp.json()
        except json.JSONDecodeError:
            json_data = None
        
        return {
            "raw": resp.text,
            "json": json_data
        }
    
    def fetch_overview_courses_api(self, html: str, classification: str = "all") -> List[Dict]:
        sesskey = self.extract_sesskey(html)
        if not sesskey:
            return []
        
        payload = [{
            "index": 0,
            "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
            "args": {
                "classification": classification,
                "limit": 0,
                "offset": 0
            }
        }]
        
        try:
            resp = self.post("/lib/ajax/service.php?sesskey=" + sesskey, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data and len(data) > 0:
                return data[0].get("data", {}).get("courses", [])
        except Exception:
            pass
        
        return []
