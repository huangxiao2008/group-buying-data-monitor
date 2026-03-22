"""
大众点评抓取器
使用 Playwright 模拟浏览器行为，绕过反爬机制
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

from playwright.async_api import async_playwright

from skills.base.scraper import BaseScraper


class DianpingScraper(BaseScraper):
    """大众点评抓取器"""
    
    PLATFORM = 'dianping'
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        抓取大众点评数据
        返回门店列表的数据
        """
        stores = self.config.get('stores', [])
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for store in stores:
                store_id = store.get('dianping_id')
                if not store_id:
                    continue
                
                try:
                    data = await self._scrape_store(browser, store_id, store['name'])
                    if data:
                        results.append(data)
                        self.logger.info(f"✅ {store['name']} 抓取成功")
                except Exception as e:
                    self.logger.error(f"❌ {store['name']} 抓取失败: {e}")
                
                # 随机延迟，避免被封
                await self.random_delay(3, 8)
            
            await browser.close()
        
        return results
    
    async def _scrape_store(self, browser, store_id: str, store_name: str) -> Dict[str, Any]:
        """抓取单个门店数据"""
        context = await browser.new_context(
            user_agent=self.ua.random,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            # 访问门店页面
            url = f"https://www.dianping.com/shop/{store_id}"
            self.logger.info(f"🔍 正在抓取: {store_name} ({url})")
            
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(2)  # 等待页面渲染
            
            data = {
                'platform': self.PLATFORM,
                'store_name': store_name,
                'store_id': store_id,
                'timestamp': datetime.now().isoformat(),
                'url': url,
            }
            
            # 抓取评分
            try:
                rating_elem = await page.query_selector('.overall-score .score')
                if rating_elem:
                    data['rating'] = await rating_elem.inner_text()
            except:
                pass
            
            # 抓取评论数
            try:
                review_elem = await page.query_selector('.review-count')
                if review_elem:
                    review_text = await review_elem.inner_text()
                    data['review_count'] = self._extract_number(review_text)
            except:
                pass
            
            # 抓取细分评分（口味、环境、服务）
            try:
                score_items = await page.query_selector_all('.score-item')
                for item in score_items:
                    label_elem = await item.query_selector('.label')
                    score_elem = await item.query_selector('.score-num')
                    if label_elem and score_elem:
                        label = await label_elem.inner_text()
                        score = await score_elem.inner_text()
                        if '口味' in label:
                            data['taste_score'] = score
                        elif '环境' in label:
                            data['environment_score'] = score
                        elif '服务' in label:
                            data['service_score'] = score
            except:
                pass
            
            # 抓取最新评论
            try:
                reviews = await self._scrape_reviews(page)
                data['latest_reviews'] = reviews[:5]  # 只取最新5条
            except Exception as e:
                self.logger.warning(f"评论抓取失败: {e}")
            
            await context.close()
            return data
            
        except Exception as e:
            await context.close()
            raise e
    
    async def _scrape_reviews(self, page) -> List[Dict[str, Any]]:
        """抓取评论列表"""
        reviews = []
        
        try:
            # 点击"全部评价"标签
            review_tab = await page.query_selector('[data-tab="评论"]')
            if review_tab:
                await review_tab.click()
                await asyncio.sleep(2)
            
            # 抓取评论
            review_items = await page.query_selector_all('.review-item')
            
            for item in review_items[:5]:  # 只取前5条
                review = {}
                
                # 评分
                try:
                    star_elem = await item.query_selector('.star')
                    if star_elem:
                        review['rating'] = await star_elem.get_attribute('class')
                except:
                    pass
                
                # 评论内容
                try:
                    content_elem = await item.query_selector('.review-content')
                    if content_elem:
                        review['content'] = await content_elem.inner_text()
                except:
                    pass
                
                # 评论时间
                try:
                    time_elem = await item.query_selector('.review-time')
                    if time_elem:
                        review['time'] = await time_elem.inner_text()
                except:
                    pass
                
                if review:
                    reviews.append(review)
        
        except Exception as e:
            self.logger.error(f"评论抓取异常: {e}")
        
        return reviews
    
    def _extract_number(self, text: str) -> int:
        """从文本中提取数字"""
        import re
        numbers = re.findall(r'\d+', text.replace(',', ''))
        return int(numbers[0]) if numbers else 0