import os
from pathlib import Path
from typing import Optional

import yaml

from .base import Config, AppConfig, AuthConfig, CheckinConfig, CourseConfig, BrowserConfig


def load_config(config_path: Optional[str] = None) -> Config:
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH", "config/config.yaml")
    
    config_file = Path(config_path)
    if not config_file.exists():
        return Config()
    
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    return Config(
        app=AppConfig(**data.get("app", {})),
        auth=AuthConfig(**data.get("auth", {})),
        checkin=CheckinConfig(**data.get("checkin", {})),
        course=CourseConfig(**data.get("course", {})),
        browser=BrowserConfig(**data.get("browser", {})),
    )


def save_config(config: Config, config_path: str = "config/config.yaml"):
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "app": {
            "base_url": config.app.base_url,
            "log_level": config.app.log_level,
        },
        "auth": {
            "cookie_header": config.auth.cookie_header,
            "new_api_user": config.auth.new_api_user,
            "username": config.auth.username,
            "password": config.auth.password,
        },
        "checkin": {
            "enabled": config.checkin.enabled,
            "time_range": config.checkin.time_range,
            "url": config.checkin.url,
            "retry_times": config.checkin.retry_times,
            "retry_interval": config.checkin.retry_interval,
            "startup_window_seconds": config.checkin.startup_window_seconds,
        },
        "course": {
            "enabled": config.course.enabled,
            "duration_seconds": config.course.duration_seconds,
            "interval_seconds": config.course.interval_seconds,
            "payload_template": config.course.payload_template,
            "limit": config.course.limit,
            "gap_seconds": config.course.gap_seconds,
        },
        "browser": {
            "headless": config.browser.headless,
            "timeout": config.browser.timeout,
            "user_agent": config.browser.user_agent,
        },
    }
    
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
