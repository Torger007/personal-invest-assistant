"""数据存储层 - 统一处理数据入库（异步PostgreSQL版本）"""
from typing import Dict, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fund import Fund
from app.models.market import IndexDaily, FundFlow


class DataStorage:
    """数据存储层类，提供统一的数据入库接口（异步版本）"""

    def __init__(self, db_session: AsyncSession):
        """初始化存储层

        Args:
            db_session: SQLAlchemy异步数据库会话
        """
        self._db = db_session

    async def save_fund_info(self, fund_data: Dict) -> bool:
        """保存基金信息，支持更新

        Args:
            fund_data: 基金信息字典，包含 code, name, type, manager, company, create_date

        Returns:
            bool: 是否保存成功
        """
        try:
            # 查询是否已存在
            result = await self._db.execute(
                select(Fund).where(Fund.code == fund_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新已有记录
                for key, value in fund_data.items():
                    setattr(existing, key, value)
            else:
                # 新增记录
                new_fund = Fund(**fund_data)
                self._db.add(new_fund)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def save_index_daily(self, index_data: List[Dict]) -> bool:
        """保存指数日线数据，支持批量和更新

        Args:
            index_data: 指数日线数据列表，每个元素包含 code, date, open, high, low, close, volume, amount

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in index_data:
                # 根据 code 和 date 判断是否已存在
                result = await self._db.execute(
                    select(IndexDaily).where(
                        IndexDaily.code == data["code"],
                        IndexDaily.date == data["date"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新已有记录
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # 新增记录
                    new_record = IndexDaily(**data)
                    self._db.add(new_record)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def save_fund_flow(self, flow_data: List[Dict]) -> bool:
        """保存资金流向数据，支持批量和更新

        Args:
            flow_data: 资金流向数据列表，每个元素包含 date, north_flow, main_flow, retail_flow

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in flow_data:
                # 根据 date 判断是否已存在
                result = await self._db.execute(
                    select(FundFlow).where(FundFlow.date == data["date"])
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新已有记录
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # 新增记录
                    new_record = FundFlow(**data)
                    self._db.add(new_record)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def get_latest_index_data(self, code: str, days: int = 30) -> List[Dict]:
        """查询最新指数数据

        Args:
            code: 指数代码
            days: 查询天数

        Returns:
            List[Dict]: 指数数据列表，按日期降序排列（最新的在前）
        """
        result = await self._db.execute(
            select(IndexDaily)
            .where(IndexDaily.code == code)
            .order_by(IndexDaily.date.desc())
            .limit(days)
        )
        records = result.scalars().all()

        # 按日期降序返回（最新的在前）
        data_list = []
        for record in records:
            data_list.append({
                "code": record.code,
                "date": record.date,
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
                "amount": record.amount,
            })

        return data_list

    async def get_fund_flow_history(self, days: int = 30) -> List[Dict]:
        """查询资金流向历史

        Args:
            days: 查询天数

        Returns:
            List[Dict]: 资金流向数据列表，按日期降序排列（最新的在前）
        """
        result = await self._db.execute(
            select(FundFlow)
            .order_by(FundFlow.date.desc())
            .limit(days)
        )
        records = result.scalars().all()

        # 按日期降序返回（最新的在前）
        data_list = []
        for record in records:
            data_list.append({
                "date": record.date,
                "north_flow": record.north_flow,
                "main_flow": record.main_flow,
                "retail_flow": record.retail_flow,
            })

        return data_list
