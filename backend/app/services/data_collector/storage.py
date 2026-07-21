"""数据存储层 - 统一处理数据入库（异步PostgreSQL版本）"""
from typing import Dict, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fund import Fund, FundNav
from app.models.market import IndexDaily, FundFlow, SectorBoard, SectorDaily


class DataStorage:
    """数据存储层类，提供统一的数据入库接口（异步版本）"""

    def __init__(self, db_session: AsyncSession):
        """初始化存储层

        Args:
            db_session: SQLAlchemy异步数据库会话
        """
        self._db = db_session

    async def save_fund_info(self, fund_data: Dict) -> bool:
        """保存基金信息，支持更新。已有记录时只更新有效字段，防止脏数据覆盖。

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
                # 只更新有效字段，不覆盖已有正确数据
                for key, value in fund_data.items():
                    if key == "code":
                        continue
                    # 跳过占位名称（格式: "基金"+纯数字代码）
                    if key == "name" and self._is_placeholder_name(fund_data["code"], value):
                        continue
                    # 跳过无效值
                    if key == "type" and (not value or value == "未知" or value.strip() == ""):
                        continue
                    if value is not None and value != "":
                        setattr(existing, key, value)
            else:
                # 新增记录，但跳过占位名称
                if not self._is_placeholder_name(fund_data.get("code", ""), fund_data.get("name", "")):
                    new_fund = Fund(**fund_data)
                    self._db.add(new_fund)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    @staticmethod
    def _is_placeholder_name(code: str, name: str) -> bool:
        """判断名称是否为占位名称（如 基金008163）"""
        if not name or not code:
            return True
        name = str(name).strip()
        code = str(code).strip()
        return name == f"基金{code}"

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

    async def save_fund_nav(self, nav_data: List[Dict]) -> bool:
        """保存基金净值数据，支持批量和更新

        Args:
            nav_data: 基金净值数据列表，每个元素包含 fund_code, date, unit_nav, acc_nav, daily_return

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in nav_data:
                # 根据 fund_code 和 date 判断是否已存在
                result = await self._db.execute(
                    select(FundNav).where(
                        FundNav.fund_code == data["fund_code"],
                        FundNav.date == data["date"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新已有记录
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # 新增记录
                    new_record = FundNav(**data)
                    self._db.add(new_record)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def get_fund_nav_history(self, fund_code: str, days: int = 30) -> List[Dict]:
        """查询基金净值历史

        Args:
            fund_code: 基金代码
            days: 查询天数

        Returns:
            List[Dict]: 净值数据列表，按日期降序排列（最新的在前）
        """
        result = await self._db.execute(
            select(FundNav)
            .where(FundNav.fund_code == fund_code)
            .order_by(FundNav.date.desc())
            .limit(days)
        )
        records = result.scalars().all()

        data_list = []
        for record in records:
            data_list.append({
                "fund_code": record.fund_code,
                "date": record.date,
                "unit_nav": float(record.unit_nav) if record.unit_nav else None,
                "acc_nav": float(record.acc_nav) if record.acc_nav else None,
                "daily_return": float(record.daily_return) if record.daily_return else None,
            })

        return data_list

    # ============== 板块数据 ==============

    async def save_sector_board(self, sector_list: List[Dict]) -> bool:
        """保存板块排名快照（先清空当日同类型旧数据，再批量插入）

        Args:
            sector_list: 板块数据列表，每个包含 code/name/type/change_pct/volume/amount/leader/leader_change/snap_date

        Returns:
            bool: 是否保存成功
        """
        try:
            if not sector_list:
                return True

            sector_type = sector_list[0].get("type", "concept")
            snap_date = sector_list[0].get("snap_date")

            # 删除同一日期+类型的旧快照
            from sqlalchemy import delete
            if snap_date:
                await self._db.execute(
                    delete(SectorBoard).where(
                        SectorBoard.snap_date == snap_date,
                        SectorBoard.type == sector_type
                    )
                )

            # 批量插入新数据
            for data in sector_list:
                record = SectorBoard(**data)
                self._db.add(record)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def get_sector_board(self, sector_type: str = "concept",
                               limit: int = 50) -> List[Dict]:
        """查询最新板块排名

        Args:
            sector_type: 板块类型 concept / industry
            limit: 返回条数

        Returns:
            List[Dict]: 板块排名列表，按涨跌幅降序
        """
        from sqlalchemy import desc
        result = await self._db.execute(
            select(SectorBoard)
            .where(SectorBoard.type == sector_type)
            .order_by(desc(SectorBoard.change_pct))
            .limit(limit)
        )
        records = result.scalars().all()

        return [
            {
                "code": r.code,
                "name": r.name,
                "type": r.type,
                "change_pct": r.change_pct,
                "volume": r.volume,
                "amount": r.amount,
                "leader": r.leader,
                "leader_change": r.leader_change,
                "snap_date": str(r.snap_date) if r.snap_date else None,
            }
            for r in records
        ]

    async def save_sector_daily(self, daily_list: List[Dict]) -> bool:
        """保存板块日线数据（支持批量 upsert）

        Args:
            daily_list: 板块日线列表，每项含 sector_name/date/open/close/high/low/change_pct/volume/amount

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in daily_list:
                result = await self._db.execute(
                    select(SectorDaily).where(
                        SectorDaily.sector_name == data["sector_name"],
                        SectorDaily.date == data["date"]
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    record = SectorDaily(**data)
                    self._db.add(record)

            await self._db.commit()
            return True
        except Exception as e:
            await self._db.rollback()
            raise e

    async def get_sector_daily_hist(self, sector_name: str,
                                    days: int = 30) -> List[Dict]:
        """查询单个板块历史K线

        Args:
            sector_name: 板块名称
            days: 查询天数

        Returns:
            List[Dict]: 日线列表，按日期降序（最新在前）
        """
        result = await self._db.execute(
            select(SectorDaily)
            .where(SectorDaily.sector_name == sector_name)
            .order_by(SectorDaily.date.desc())
            .limit(days)
        )
        records = result.scalars().all()

        return [
            {
                "sector_name": r.sector_name,
                "date": str(r.date) if r.date else None,
                "open": r.open,
                "close": r.close,
                "high": r.high,
                "low": r.low,
                "change_pct": r.change_pct,
                "volume": r.volume,
                "amount": r.amount,
            }
            for r in records
        ]

    async def get_hot_sectors(self, sector_type: str = "concept",
                              top_n: int = 10) -> List[str]:
        """获取涨幅前N的板块名称列表（用于按需采集历史K线）

        Args:
            sector_type: 板块类型
            top_n: 前N名

        Returns:
            List[str]: 板块名称列表
        """
        from sqlalchemy import desc
        result = await self._db.execute(
            select(SectorBoard.name)
            .where(SectorBoard.type == sector_type)
            .order_by(desc(SectorBoard.change_pct))
            .limit(top_n)
        )
        return [row[0] for row in result.all()]
