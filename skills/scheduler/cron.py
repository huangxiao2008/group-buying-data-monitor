"""
定时调度模块
基于 schedule 库实现精确的时间窗口调度
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict

import schedule


class CronScheduler:
    """定时调度器"""
    
    def __init__(self, config: Dict[str, Any], task_func: Callable):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task_func = task_func
        self.scraping_config = config.get('scraping', {})
    
    def start(self):
        """启动调度器"""
        self.logger.info("🕐 启动定时调度器...")
        
        # 配置评价平台调度
        self._setup_review_scheduler()
        
        # 配置外卖平台调度
        self._setup_delivery_scheduler()
        
        # 启动调度循环
        self.logger.info("✅ 调度器已启动")
        self._run_scheduler()
    
    def _setup_review_scheduler(self):
        """配置评价平台调度（大众点评、抖音、高德）"""
        review_platforms = ['dianping', 'douyin', 'gaode']
        
        for platform in review_platforms:
            if platform not in self.scraping_config:
                continue
            
            config = self.scraping_config[platform]
            if not config.get('enabled', False):
                continue
            
            interval = config.get('interval_hours', 2)
            start_time = config.get('start_time', '10:00')
            end_time = config.get('end_time', '20:00')
            
            # 每N小时执行一次
            schedule.every(interval).hours.do(
                self._run_task,
                platform=platform,
                start_time=start_time,
                end_time=end_time
            )
            
            self.logger.info(f"📅 已配置 {platform} 调度: 每{interval}小时 ({start_time}-{end_time})")
    
    def _setup_delivery_scheduler(self):
        """配置外卖平台调度"""
        if 'delivery' not in self.scraping_config:
            return
        
        config = self.scraping_config['delivery']
        if not config.get('enabled', False):
            return
        
        interval = config.get('interval_minutes', 30)
        
        # 午餐时段
        lunch_start = config.get('lunch_start', '10:30')
        lunch_end = config.get('lunch_end', '12:30')
        
        # 晚餐时段
        dinner_start = config.get('dinner_start', '17:00')
        dinner_end = config.get('dinner_end', '19:00')
        
        # 在午餐时段每N分钟执行
        schedule.every(interval).minutes.do(
            self._run_delivery_task,
            start_time=lunch_start,
            end_time=lunch_end
        )
        
        # 在晚餐时段每N分钟执行
        schedule.every(interval).minutes.do(
            self._run_delivery_task,
            start_time=dinner_start,
            end_time=dinner_end
        )
        
        self.logger.info(f"🍔 已配置外卖平台调度: 每{interval}分钟")
        self.logger.info(f"   午餐时段: {lunch_start}-{lunch_end}")
        self.logger.info(f"   晚餐时段: {dinner_start}-{dinner_end}")
    
    def _run_task(self, platform: str, start_time: str, end_time: str):
        """运行单个平台任务（检查时间窗口）"""
        if not self._is_in_time_window(start_time, end_time):
            self.logger.debug(f"⏭️ 跳过 {platform} - 不在时间窗口内")
            return
        
        self.logger.info(f"🚀 执行定时任务: {platform}")
        
        import asyncio
        try:
            asyncio.run(self.task_func(platform=platform))
        except Exception as e:
            self.logger.error(f"❌ 任务执行失败 {platform}: {e}")
    
    def _run_delivery_task(self, start_time: str, end_time: str):
        """运行外卖平台任务"""
        if not self._is_in_time_window(start_time, end_time):
            return
        
        self.logger.info("🚀 执行外卖平台定时任务")
        
        import asyncio
        try:
            asyncio.run(self.task_func(platform='delivery'))
        except Exception as e:
            self.logger.error(f"❌ 外卖任务执行失败: {e}")
    
    def _is_in_time_window(self, start_time: str, end_time: str) -> bool:
        """检查当前是否在时间窗口内"""
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        return start_time <= current_time <= end_time
    
    def _run_scheduler(self):
        """运行调度循环"""
        self.logger.info("🔄 调度器运行中... (按 Ctrl+C 停止)")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            self.logger.info("👋 调度器已停止")