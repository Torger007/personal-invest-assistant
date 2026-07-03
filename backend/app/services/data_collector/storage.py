"""数据存储层 - 统一处理数据入库"""
from typing import Dict, List, Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.fund import Fund
from app.models.market import IndexDaily, FundFlow


class DataStorage:
    """数据存储层类，提供统一的数据入库接口"""

    def __init__(self, db_session: Session):
        """初始化存储层

        Args:
            db_session: SQLAlchemy数据库会话
        """
        self._db = db_session
        # 引用模型类，方便测试中访问
        self._Fund = Fund
        self._IndexDaily = IndexDaily
        self._FundFlow = FundFlow

    def save_fund_info(self, fund_data: Dict) -> bool:
        """保存基金信息，支持更新

        Args:
            fund_data: 基金信息字典，包含 code, name, type, manager, company, create_date

        Returns:
            bool: 是否保存成功
        """
        try:
            # 查询是否已存在
            existing = self._db.query(Fund).filter_by(code=fund_data["code"]).first()

            if existing:
                # 更新已有记录
                for key, value in fund_data.items():
                    setattr(existing, key, value)
            else:
                # 新增记录
                new_fund = Fund(**fund_data)
                self._db.add(new_fund)

            self._db.commit()
            return True
        except Exception as e:
            self._db.rollback()
            raise e

    def save_index_daily(self, index_data: List[Dict]) -> bool:
        """保存指数日线数据，支持批量和更新

        Args:
            index_data: 指数日线数据列表，每个元素包含 code, date, open, high, low, close, volume, amount

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in index_data:
                # 根据 code 和 date 判断是否已存在
                existing = self._db.query(IndexDaily).filter_by(
                    code=data["code"], date=data["date"]
                ).first()

                if existing:
                    # 更新已有记录
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # 新增记录
                    new_record = IndexDaily(**data)
                    self._db.add(new_record)

            self._db.commit()
            return True
        except Exception as e:
            self._db.rollback()
            raise e

    def save_fund_flow(self, flow_data: List[Dict]) -> bool:
        """保存资金流向数据，支持批量和更新

        Args:
            flow_data: 资金流向数据列表，每个元素包含 date, north_flow, main_flow, retail_flow

        Returns:
            bool: 是否保存成功
        """
        try:
            for data in flow_data:
                # 根据 date 判断是否已存在
                existing = self._db.query(FundFlow).filter_by(date=data["date"]).first()

                if existing:
                    # 更新已有记录
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # 新增记录
                    new_record = FundFlow(**data)
                    self._db.add(new_record)

            self._db.commit()
            return True
        except Exception as e:
            self._db.rollback()
            raise e

    def get_latest_index_data(self, code: str, days: int = 30) -> List[Dict]:
        """查询最新指数数据

        Args:
            code: 指数代码
            days: 查询天数

        Returns:
            List[Dict]: 指数数据列表，按日期降序排列（最新的在前）
        """
        records = (
            self._db.query(IndexDaily)
            .filter_by(code=code)
            .order_by(IndexDaily.date.desc())
            .limit(days)
            .all()
        )

        # 按日期降序返回（最新的在前）
        result = []
        for record in records:
            result.append({
                "code": record.code,
                "date": record.date,
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
                "amount": record.amount,
            })

        return result

    def get_fund_flow_history(self, days: int = 30) -> List[Dict]:
        """查询资金流向历史

        Args:
            days: 查询天数

        Returns:
            List[Dict]: 资金流向数据列表，按日期降序排列（最新的在前）
        """
        records = (
            self._db.query(FundFlow)
            .order_by(FundFlow.date.desc())
            .limit(days)
            .all()
        )

        # 按日期降序返回（最新的在前）
        result = []
        for record in records:
            result.append({
                "date": record.date,
                "north_flow": record.north_flow,
                "main_flow": record.main_flow,
                "retail_flow": record.retail_flow,
            })

        return result
