"""
基础抓取器类
提供通用的抓取功能和反爬策略
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from fake_useragent import UserAgent


class BaseScraper(ABC):
    """抓取器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ua = UserAgent()
        self.session = None
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头（带随机User-Agent）"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def random_delay(self, min_sec: int = None, max_sec: int = None):
        """随机延迟，避免被封"""
        min_sec = min_sec or 3
        max_sec = max_sec or 8
        delay = random.uniform(min_sec, max_sec)
        self.logger.debug(f"⏱️ 随机延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
    
    @abstractmethod
    async def scrape(self) -> Dict[str, Any]:
        """执行抓取，子类必须实现"""
        pass
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """验证数据完整性"""
        if not data:
            return False
        # 基础验证：关键字段不能为空
        required_fields = ['store_name', 'timestamp']
        return all(field in data for field in required_fields)