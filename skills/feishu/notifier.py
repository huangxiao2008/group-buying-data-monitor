"""
飞书通知模块
支持Webhook推送和富文本卡片
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

import requests


class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.webhook_url = config['feishu']['webhook_url']
        self.secret = config['feishu'].get('secret', '')
        self.at_users = config['feishu'].get('at_users', [])
    
    def _gen_sign(self, timestamp: int) -> str:
        """生成飞书签名"""
        if not self.secret:
            return ''
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = hmac_code.hex()
        return sign
    
    async def send(self, data: Dict[str, Any]) -> bool:
        """
        发送数据到飞书
        """
        try:
            message = self._build_message(data)
            return self._send_webhook(message)
        except Exception as e:
            self.logger.error(f"飞书通知发送失败: {e}")
            return False
    
    def _build_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建飞书消息"""
        timestamp = int(datetime.now().timestamp())
        
        # 构建内容
        content = self._format_content(data)
        
        message = {
            "timestamp": timestamp,
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "📊 团购+外卖数据监测报告"
                    },
                    "template": "blue"
                },
                "elements": content
            }
        }
        
        if self.secret:
            message['sign'] = self._gen_sign(timestamp)
        
        return message
    
    def _format_content(self, data: Dict[str, Any]) -> List[Dict]:
        """格式化数据为飞书卡片内容"""
        elements = []
        
        # 添加时间
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**数据更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        })
        
        # 大众点评数据
        if 'dianping' in data and data['dianping']:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "### 🏪 大众点评数据"
                }
            })
            
            for store in data['dianping']:
                content = f"**{store.get('store_name', '未知门店')}**\n"
                content += f"• 评分: {store.get('rating', 'N/A')}\n"
                content += f"• 评论数: {store.get('review_count', 0)}\n"
                if 'taste_score' in store:
                    content += f"• 口味/环境/服务: {store.get('taste_score', '-')}/{store.get('environment_score', '-')}/{store.get('service_score', '-')}\n"
                
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                })
        
        # 外卖平台数据
        if 'delivery' in data and data['delivery']:
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "### 🍔 外卖平台数据"
                }
            })
            
            for platform, stores in data['delivery'].items():
                if stores:
                    platform_name = {'meituan': '美团', 'eleme': '饿了么', 'jd': '京东'}.get(platform, platform)
                    elements.append({
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{platform_name}**: {len(stores)} 家门店数据已更新"
                        }
                    })
        
        # 添加@用户
        if self.at_users:
            at_text = ' '.join([f"<at id=\"{phone}\"></at>" for phone in self.at_users])
            elements.append({"tag": "hr"})
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": at_text
                }
            })
        
        return elements
    
    def _send_webhook(self, message: Dict[str, Any]) -> bool:
        """发送Webhook请求"""
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    self.logger.info("✅ 飞书通知发送成功")
                    return True
                else:
                    self.logger.error(f"飞书API返回错误: {result}")
                    return False
            else:
                self.logger.error(f"飞书Webhook请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"飞书Webhook请求异常: {e}")
            return False