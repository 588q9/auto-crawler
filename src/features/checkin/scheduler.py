import time
import random
from datetime import datetime, timedelta
from loguru import logger

from ...config.base import CheckinConfig, BrowserConfig
from ...utils.helpers import parse_time_range
from .api_worker import ApiCheckinWorker


class CheckinScheduler:
    def __init__(self, config: CheckinConfig, browser_config: BrowserConfig, cookie_header: str = "", api_user: str = ""):
        self.config = config
        self.browser_config = browser_config
        self.worker = ApiCheckinWorker(config, cookie_header or None, api_user or None)
    
    def _attempt_checkin_with_retry(self) -> bool:
        success = False
        for attempt in range(self.config.retry_times):
            if self.worker.run():
                success = True
                break
            if attempt < self.config.retry_times - 1:
                logger.warning(f"签到失败，准备重试 {attempt + 1}/{self.config.retry_times}，等待 {self.config.retry_interval} 秒")
                time.sleep(self.config.retry_interval)
        if not success:
            logger.error("本次签到失败，已记录")
        return success
    
    def run_once(self):
        delay = random.randint(0, int(self.config.startup_window_seconds or 50))
        logger.info(f"将在启动后 {delay} 秒内执行一次签到")
        time.sleep(delay)
        self.worker.run()
    
    def run_daily(self):
        if not self.config.enabled:
            logger.info("签到功能未启用")
            return
        
        logger.info(f"启动每日签到调度器，活动时间段: {self.config.time_range}，随机窗口秒数: {self.config.startup_window_seconds}")
        
        initial_delay = random.randint(0, int(self.config.startup_window_seconds or 50))
        logger.info(f"首次将在启动后 {initial_delay} 秒执行签到")
        time.sleep(initial_delay)
        self._attempt_checkin_with_retry()
        
        while True:
            try:
                start_dt, end_dt = parse_time_range(self.config.time_range)
                now = datetime.now()
                if now < start_dt:
                    wait_seconds = (start_dt - now).total_seconds()
                    logger.info(f"等待至每日窗口开始 {start_dt.strftime('%H:%M:%S')}，约 {int(wait_seconds)} 秒")
                    time.sleep(wait_seconds)
                    now = datetime.now()
                if now > end_dt:
                    next_start = (now + timedelta(days=1)).replace(hour=start_dt.hour, minute=start_dt.minute, second=start_dt.second, microsecond=0)
                    wait_seconds = (next_start - now).total_seconds()
                    logger.info(f"当前已过每日窗口结束，等待至次日 {next_start.strftime('%H:%M:%S')}，约 {int(wait_seconds)} 秒")
                    time.sleep(wait_seconds)
                    now = datetime.now()

                remaining = max(0, int((end_dt - now).total_seconds()))
                delay = min(random.randint(0, int(self.config.startup_window_seconds or 50)), remaining)
                logger.info(f"本次将在当前时间后 {delay} 秒执行签到（不在凌晨执行）")
                time.sleep(delay)

                self._attempt_checkin_with_retry()
                
                tomorrow_start = (datetime.now() + timedelta(days=1)).replace(hour=start_dt.hour, minute=start_dt.minute, second=start_dt.second, microsecond=0)
                wait_seconds = (tomorrow_start - datetime.now()).total_seconds()
                logger.info(f"等待至次日窗口开始 {tomorrow_start.strftime('%H:%M:%S')}，约 {int(wait_seconds)} 秒")
                time.sleep(wait_seconds)
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止签到调度器")
                break
            except Exception as e:
                logger.error(f"签到调度器异常: {e}")
                time.sleep(300)
