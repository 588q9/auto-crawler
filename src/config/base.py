from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppConfig:
    base_url: str = "https://courses.gdut.edu.cn"
    log_level: str = "INFO"


@dataclass
class AuthConfig:
    cookie_header: Optional[str] = None
    new_api_user: Optional[str] = None
    username: str = ""
    password: str = ""


@dataclass
class CheckinConfig:
    enabled: bool = True
    time_range: str = "08:00-10:00"
    url: str = "https://duckcoding.com/api/user/checkin"
    retry_times: int = 3
    retry_interval: int = 60
    startup_window_seconds: int = 50


@dataclass
class CourseConfig:
    enabled: bool = True
    duration_seconds: int = 300
    interval_seconds: int = 60
    payload_template: Optional[str] = None
    limit: Optional[int] = None
    gap_seconds: int = 5


@dataclass
class BrowserConfig:
    headless: bool = True
    timeout: int = 30000
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


@dataclass
class Config:
    app: AppConfig = field(default_factory=AppConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    checkin: CheckinConfig = field(default_factory=CheckinConfig)
    course: CourseConfig = field(default_factory=CourseConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
