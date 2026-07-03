"""
数据源基类
所有数据源继承此类，实现统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import httpx
import asyncio


class BaseDataSource(ABC):
    """数据源基类"""

    def __init__(self, name: str, base_url: str = ""):
        self.name = name
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

    @abstractmethod
    async def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        pass

    @abstractmethod
    async def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金净值数据"""
        pass

    @abstractmethod
    async def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据"""
        pass

    @abstractmethod
    async def get_fund_flow(self, days: int = 30) -> List[Dict]:
        """获取资金流向数据"""
        pass

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    async def fetch(self, url: str, params: Optional[Dict] = None) -> Dict:
        """发送GET请求"""
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[{self.name}] 请求失败 {url}: {e}")
            return {}