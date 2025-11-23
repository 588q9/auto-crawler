import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    base_url: str = "https://courses.gdut.edu.cn"
    cookie_header: Optional[str] = None  # e.g. "MoodleSession=..."


def load_config(cookie_header: Optional[str] = None, cookie_value: Optional[str] = None) -> Config:
    """Load configuration from args or environment.

    Priority:
    1) explicit cookie_header (full Cookie header string)
    2) cookie_value (raw MoodleSession value -> builds header)
    3) env var MOODLE_SESSION
    """
    if cookie_header and cookie_header.strip():
        header = cookie_header.strip()
    else:
        raw = (
            cookie_value
            if (cookie_value and cookie_value.strip())
            else os.environ.get("MOODLE_SESSION", "").strip()
        )
        header = f"MoodleSession={raw}" if raw else None

    return Config(cookie_header=header)

