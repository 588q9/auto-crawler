import random
import time
from datetime import datetime, timedelta
from typing import Tuple


def parse_time_range(time_range: str) -> Tuple[datetime, datetime]:
    start_str, end_str = time_range.split("-")
    today = datetime.now().date()
    
    start_time = datetime.combine(today, datetime.strptime(start_str, "%H:%M").time())
    end_time = datetime.combine(today, datetime.strptime(end_str, "%H:%M").time())
    
    return start_time, end_time


def get_random_time_in_range(time_range: str) -> datetime:
    start_time, end_time = parse_time_range(time_range)
    delta = end_time - start_time
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start_time + timedelta(seconds=random_seconds)


def wait_until(target_time: datetime):
    now = datetime.now()
    if target_time > now:
        wait_seconds = (target_time - now).total_seconds()
        print(f"等待到 {target_time.strftime('%H:%M:%S')} ({wait_seconds:.0f}秒)...")
        time.sleep(wait_seconds)


def retry_on_failure(max_retries: int = 3, delay: int = 60):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"重试 {attempt + 1}/{max_retries}，等待 {delay} 秒...")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
