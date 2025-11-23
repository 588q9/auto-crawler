from __future__ import annotations

import time
from typing import Optional, Dict, List, Any

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


class MoodleClient:
    def __init__(self, base_url: str, cookie_header: Optional[str] = None, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if cookie_header:
            # set raw Cookie header to respect provided value
            self.session.headers["Cookie"] = cookie_header

    def get(self, path: str, params: Optional[Dict] = None, max_retries: int = 3, backoff: float = 0.8) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp
                # retry on 5xx or 429
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(backoff * attempt)
                    continue
                # Non-retryable status
                resp.raise_for_status()
                return resp
            except Exception as e:
                last_exc = e
                time.sleep(backoff * attempt)
        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed without exception")

    def get_my_courses_page(self) -> str:
        resp = self.get("/my/")
        return resp.text

    # --- Helpers for course overview via AJAX service ---
    @staticmethod
    def extract_sesskey(html: str) -> Optional[str]:
        """Extract sesskey from /my/ page HTML.
        Tries common patterns: input[name=sesskey], data-sesskey, JS vars.
        """
        import re
        # input field
        m = re.search(r'name=["\']sesskey["\']\s+value=["\']([a-zA-Z0-9]+)["\']', html)
        if m:
            return m.group(1)
        # data-sesskey or JSON
        m = re.search(r'sesskey["\']?\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', html)
        if m:
            return m.group(1)
        return None

    def fetch_overview_courses_api(self, html: str, classification: str = "all") -> List[Dict]:
        """Call Moodle AJAX service to get courses in '课程概览' (myoverview) block.

        Returns a list of dicts with keys like id, fullname, viewurl.
        """
        import json

        sesskey = self.extract_sesskey(html)
        if not sesskey:
            return []

        url = f"{self.base_url}/lib/ajax/service.php"
        params = {
            "sesskey": sesskey,
            "info": "core_course_get_enrolled_courses_by_timeline_classification",
        }
        payload = [
            {
                "index": 0,
                "methodname": "core_course_get_enrolled_courses_by_timeline_classification",
                "args": {
                    "offset": 0,
                    "limit": 0,
                    "classification": classification,  # 'inprogress' | 'all' | 'future' | 'past'
                    "sort": "fullname",
                    "customfieldname": "",
                    "customfieldvalue": "",
                },
            }
        ]

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Merge with default headers
        req_headers = dict(self.session.headers)
        req_headers.update(headers)

        resp = self.session.post(url, params=params, data=json.dumps(payload), headers=req_headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # Expected Moodle response: list with one entry
        if not isinstance(data, list) or not data:
            return []
        entry = data[0]
        if entry.get("error"):
            return []
        result = entry.get("data") or {}
        courses = result.get("courses") or []
        return courses

    # ---- Generic AJAX service caller ----
    def call_ajax_service(self, methodname: str, args: Dict[str, Any], html_context: Optional[str] = None) -> Any:
        """Call a Moodle AJAX service method with given args.

        If html_context is provided, extracts sesskey from it; otherwise tries to reuse page.
        Returns the 'data' field of the first entry or raw response JSON.
        """
        import json
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        else:
            sesskey = None
        # If still no sesskey, try fetching /my/ as a fallback
        if not sesskey:
            try:
                sesskey = self.extract_sesskey(self.get_my_courses_page())
            except Exception:
                pass

        params = {"sesskey": sesskey or ""}
        if methodname:
            params["info"] = methodname

        payload = [{"index": 0, "methodname": methodname, "args": args}]
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req_headers = dict(self.session.headers)
        req_headers.update(headers)
        url = f"{self.base_url}/lib/ajax/service.php"
        resp = self.session.post(url, params=params, data=json.dumps(payload), headers=req_headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            entry = data[0]
            if entry.get("error"):
                return entry
            return entry.get("data")
        return data

    def post_service(self, payload_list: List[Dict[str, Any]], html_context: Optional[str] = None, timestamp: Optional[int] = None) -> Any:
        """Post raw payload list to Moodle service.php with sesskey and timestamp.

        Returns parsed JSON.
        """
        import json, time as _time
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        else:
            sesskey = None
        if not sesskey:
            try:
                sesskey = self.extract_sesskey(self.get_my_courses_page())
            except Exception:
                pass

        ts = timestamp if timestamp is not None else int(_time.time() * 1000)
        params = {"sesskey": sesskey or "", "timestamp": ts}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req_headers = dict(self.session.headers)
        req_headers.update(headers)
        url = f"{self.base_url}/lib/ajax/service.php"
        resp = self.session.post(url, params=params, data=json.dumps(payload_list), headers=req_headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post_service_capture(self, payload_list: List[Dict[str, Any]], html_context: Optional[str] = None, timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Post to service.php and capture both raw text and parsed JSON.

        Returns dict: {"raw": str, "json": Any}
        """
        import json, time as _time
        if html_context:
            sesskey = self.extract_sesskey(html_context)
        else:
            sesskey = None
        if not sesskey:
            try:
                sesskey = self.extract_sesskey(self.get_my_courses_page())
            except Exception:
                pass

        ts = timestamp if timestamp is not None else int(_time.time() * 1000)
        params = {"sesskey": sesskey or "", "timestamp": ts}

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        req_headers = dict(self.session.headers)
        req_headers.update(headers)
        url = f"{self.base_url}/lib/ajax/service.php"
        resp = self.session.post(url, params=params, data=json.dumps(payload_list), headers=req_headers, timeout=self.timeout)
        resp.raise_for_status()
        raw_text = resp.text
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
        return {"raw": raw_text, "json": parsed}

    # ---- fsresource helpers ----
    @staticmethod
    def extract_fsresource_info(html: str) -> Dict[str, Any]:
        """Best-effort extraction of fsresource identifiers (fsresourceid, duration, name) from HTML.

        Returns dict like {fsresourceid: int|None, duration: int|None, name: str|None}
        """
        import re, json
        info: Dict[str, Any] = {"fsresourceid": None, "duration": None, "name": None, "sesskey": None}

        # Prefer playerdata object if present
        # Matches: var playerdata = {...}; or playerdata: {...}
        m = re.search(r"playerdata\s*=\s*(\{.*?\})\s*;", html, flags=re.DOTALL)
        if not m:
            m = re.search(r"playerdata\s*:\s*(\{.*?\})", html, flags=re.DOTALL)
        if m:
            raw = m.group(1)
            # Normalize to JSON: replace single quotes to double quotes cautiously
            cleaned = raw
            try:
                # Remove trailing commas
                cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
                # Convert single quotes to double quotes when used as string delimiter
                # This is heuristic and may not be perfect, but works for typical literal objects
                cleaned = cleaned.replace("'", '"')
                # Unescape backslashes properly for JSON
                # Attempt parse
                pdata = json.loads(cleaned)
                # Extract fields
                fsid = pdata.get("fsresourceid")
                if isinstance(fsid, int):
                    info["fsresourceid"] = fsid
                elif isinstance(fsid, str) and fsid.isdigit():
                    info["fsresourceid"] = int(fsid)
                # Some pages carry sesskey inside playerdata
                sk = pdata.get("sesskey")
                if isinstance(sk, str) and sk:
                    info["sesskey"] = sk
            except Exception:
                # Fall back to generic patterns below
                pass

        # Common patterns in inline JS or data attributes
        patterns = [
            r"fsresourceid\s*[:=]\s*(\d+)",
            r"data-fsresourceid\s*=\s*\"?(\d+)\"?",
            r"fsresource\s*:\s*\{[^}]*?id\s*:\s*(\d+)",
            r"cmid\s*[:=]\s*(\d+)",  # sometimes cmid equals activity id; may differ
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                try:
                    info["fsresourceid"] = int(m.group(1))
                    break
                except Exception:
                    pass

        # Duration patterns
        dur_patterns = [
            r"duration\s*[:=]\s*(\d+)",
            r"data-duration\s*=\s*\"?(\d+)\"?",
        ]
        for pat in dur_patterns:
            m = re.search(pat, html)
            if m:
                try:
                    info["duration"] = int(m.group(1))
                    break
                except Exception:
                    pass

        # Name/title
        m = re.search(r"<h2[^>]*>(.*?)</h2>", html, flags=re.DOTALL)
        if m:
            info["name"] = re.sub(r"\s+", " ", m.group(1)).strip()

        return info

    def get_course_module_info(self, cmid: int, html_context: Optional[str] = None) -> Dict[str, Any]:
        """Fetch Moodle course module info via AJAX to resolve instance id.

        Returns dict; for fsresource, the 'instance' field is commonly the fsresourceid.
        """
        payload = [{"index": 0, "methodname": "core_course_get_course_module", "args": {"cmid": cmid}}]
        data = self.post_service(payload, html_context=html_context)
        try:
            if isinstance(data, list) and data:
                entry = data[0]
                if entry.get("error"):
                    return {}
                return entry.get("data") or {}
        except Exception:
            return {}
        return {}

    # ---- Parse M.cfg from HTML ----
    @staticmethod
    def parse_m_cfg(html: str) -> Dict[str, Any]:
        """Extract M.cfg object from HTML. Returns dict (may be empty)."""
        import re, json
        # Look for M.cfg = {...}; allowing whitespace and escaped quotes
        m = re.search(r"M\.cfg\s*=\s*(\{.*?\})\s*;", html, flags=re.DOTALL)
        if not m:
            # Sometimes assigned via window.M = {...}; window.M.cfg = {...}
            m = re.search(r"cfg\s*:\s*(\{.*?\})", html, flags=re.DOTALL)
        if not m:
            return {}
        raw = m.group(1)
        # Unescape JS-specific sequences for JSON
        try:
            # Replace single quotes to double if necessary (best-effort)
            cleaned = raw
            # Allow trailing commas removal
            cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
            # Ensure valid JSON
            return json.loads(cleaned)
        except Exception:
            # Fallback: try to recover quotes
            try:
                cleaned = raw.replace("'", '"')
                cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
                return json.loads(cleaned)
            except Exception:
                return {}
