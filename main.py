#!/usr/bin/env python3
"""
团购+外卖数据监测系统 - 主程序
基于 OpenClaw Skills 架构
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

# 配置日志
def setup_logging(config):
    log_config = config.get('logging', {})
    level = getattr(logging, log_config.get('level', 'INFO'))
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file := log_config.get('file'):
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_size', '10MB'),
            backupCount=log_config.get('backup_count', 5)
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    return logging.getLogger(__name__)


class GroupBuyingMonitor:
    """团购+外卖数据监测主类"""
    
    def __init__(self, config_path='config.yaml'):
        self.config = self._load_config(config_path)
        self.logger = setup_logging(self.config)
        self.logger.info("🚀 数据监测系统初始化完成")
    
    def _load_config(self, path):
        """加载配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ 配置文件未找到: {path}")
            print("请复制 config.example.yaml 为 config.yaml 并填写配置")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 配置文件解析失败: {e}")
            sys.exit(1)
    
    async def run_once(self, platform=None, test_mode=False):
        """运行一次数据抓取"""
        self.logger.info(f"📊 开始数据抓取 | 平台: {platform or 'all'} | 测试模式: {test_mode}")
        
        from skills.dianping.scraper import DianpingScraper
        from skills.delivery.scraper import DeliveryScraper
        from skills.feishu.notifier import FeishuNotifier
        
        results = {}
        
        # 大众点评
        if platform in [None, 'dianping'] and self.config['scraping']['dianping']['enabled']:
            self.logger.info("🎯 开始抓取大众点评数据...")
            scraper = DianpingScraper(self.config)
            results['dianping'] = await scraper.scrape()
        
        # 外卖平台
        if platform in [None, 'delivery', 'meituan', 'eleme', 'jd'] and self.config['scraping']['delivery']['enabled']:
            self.logger.info("🍔 开始抓取外卖平台数据...")
            scraper = DeliveryScraper(self.config)
            results['delivery'] = await scraper.scrape()
        
        # 发送飞书通知
        if not test_mode and results:
            self.logger.info("📤 发送飞书通知...")
            notifier = FeishuNotifier(self.config)
            await notifier.send(results)
        elif test_mode:
            self.logger.info("🧪 测试模式 - 跳过飞书推送")
            self.logger.info(f"📋 抓取结果预览: {results}")
        
        self.logger.info("✅ 本次抓取完成")
        return results
    
    def start_scheduler(self):
        """启动定时调度器"""
        from skills.scheduler.cron import CronScheduler
        scheduler = CronScheduler(self.config, self.run_once)
        scheduler.start()
    
    async def test_all(self):
        """测试所有平台"""
        self.logger.info("🧪 开始测试所有平台...")
        results = await self.run_once(test_mode=True)
        
        # 输出测试报告
        print("\n" + "="*50)
        print("📊 测试结果报告")
        print("="*50)
        for platform, data in results.items():
            status = "✅ 成功" if data else "❌ 失败"
            print(f"{platform:15} {status}")
        print("="*50)
        
        return results


def main():
    parser = argparse.ArgumentParser(description='团购+外卖数据监测系统')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--test', action='store_true', help='测试模式（不发送飞书通知）')
    parser.add_argument('--run', action='store_true', help='运行一次')
    parser.add_argument('--schedule', action='store_true', help='启动定时调度')
    parser.add_argument('--platform', '-p', choices=['dianping', 'douyin', 'gaode', 'meituan', 'eleme', 'jd', 'delivery'], 
                       help='指定平台')
    
    args = parser.parse_args()
    
    monitor = GroupBuyingMonitor(args.config)
    
    if args.test:
        asyncio.run(monitor.test_all())
    elif args.run:
        asyncio.run(monitor.run_once(platform=args.platform, test_mode=False))
    elif args.schedule:
        monitor.start_scheduler()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()