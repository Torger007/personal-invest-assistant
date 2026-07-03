"""数据存储层单元测试"""
import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.data_collector.storage import DataStorage
from app.utils.db import Base


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    # 使用内存SQLite数据库进行测试
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def storage(db_session):
    """创建DataStorage实例"""
    return DataStorage(db_session)


class TestDataStorage:
    """数据存储层测试类"""

    def test_save_fund_info(self, storage):
        """测试保存和更新基金信息"""
        # 准备测试数据
        fund_data = {
            "code": "000001",
            "name": "华夏成长混合",
            "type": "混合型",
            "manager": "张三",
            "company": "华夏基金",
            "create_date": date(2020, 1, 1)
        }

        # 测试保存新基金
        result = storage.save_fund_info(fund_data)
        assert result is True

        # 验证数据已保存
        fund = storage._db.query(storage._Fund).filter_by(code="000001").first()
        assert fund is not None
        assert fund.name == "华夏成长混合"
        assert fund.manager == "张三"

        # 测试更新已有基金
        updated_data = {
            "code": "000001",
            "name": "华夏成长混合A",
            "type": "混合型",
            "manager": "李四",
            "company": "华夏基金",
            "create_date": date(2020, 1, 1)
        }
        result = storage.save_fund_info(updated_data)
        assert result is True

        # 验证数据已更新
        fund = storage._db.query(storage._Fund).filter_by(code="000001").first()
        assert fund.name == "华夏成长混合A"
        assert fund.manager == "李四"

    def test_save_index_daily(self, storage):
        """测试保存指数日线数据"""
        # 准备测试数据
        index_data = [
            {
                "code": "000001",
                "date": date(2024, 1, 2),
                "open": Decimal("3000.00"),
                "high": Decimal("3050.00"),
                "low": Decimal("2980.00"),
                "close": Decimal("3030.00"),
                "volume": 100000000,
                "amount": Decimal("300000000000.00")
            },
            {
                "code": "000001",
                "date": date(2024, 1, 3),
                "open": Decimal("3030.00"),
                "high": Decimal("3080.00"),
                "low": Decimal("3010.00"),
                "close": Decimal("3060.00"),
                "volume": 120000000,
                "amount": Decimal("360000000000.00")
            }
        ]

        # 测试保存数据
        result = storage.save_index_daily(index_data)
        assert result is True

        # 验证数据已保存
        records = storage._db.query(storage._IndexDaily).filter_by(code="000001").all()
        assert len(records) == 2
        assert records[0].close == Decimal("3030.00")
        assert records[1].close == Decimal("3060.00")

        # 测试更新已有数据（相同日期）
        updated_data = [
            {
                "code": "000001",
                "date": date(2024, 1, 2),
                "open": Decimal("3000.00"),
                "high": Decimal("3060.00"),
                "low": Decimal("2980.00"),
                "close": Decimal("3040.00"),
                "volume": 110000000,
                "amount": Decimal("310000000000.00")
            }
        ]
        result = storage.save_index_daily(updated_data)
        assert result is True

        # 验证数据已更新
        record = storage._db.query(storage._IndexDaily).filter_by(
            code="000001", date=date(2024, 1, 2)
        ).first()
        assert record.close == Decimal("3040.00")
        assert record.volume == 110000000

    def test_save_fund_flow(self, storage):
        """测试保存资金流向数据"""
        # 准备测试数据
        flow_data = [
            {
                "date": date(2024, 1, 2),
                "north_flow": Decimal("1000000000.00"),
                "main_flow": Decimal("-500000000.00"),
                "retail_flow": Decimal("-500000000.00")
            },
            {
                "date": date(2024, 1, 3),
                "north_flow": Decimal("1500000000.00"),
                "main_flow": Decimal("-800000000.00"),
                "retail_flow": Decimal("-700000000.00")
            }
        ]

        # 测试保存数据
        result = storage.save_fund_flow(flow_data)
        assert result is True

        # 验证数据已保存
        records = storage._db.query(storage._FundFlow).all()
        assert len(records) == 2
        assert records[0].north_flow == Decimal("1000000000.00")
        assert records[1].north_flow == Decimal("1500000000.00")

        # 测试更新已有数据（相同日期）
        updated_data = [
            {
                "date": date(2024, 1, 2),
                "north_flow": Decimal("1200000000.00"),
                "main_flow": Decimal("-600000000.00"),
                "retail_flow": Decimal("-600000000.00")
            }
        ]
        result = storage.save_fund_flow(updated_data)
        assert result is True

        # 验证数据已更新
        record = storage._db.query(storage._FundFlow).filter_by(
            date=date(2024, 1, 2)
        ).first()
        assert record.north_flow == Decimal("1200000000.00")
        assert record.main_flow == Decimal("-600000000.00")

    def test_get_latest_index_data(self, storage):
        """测试查询最新指数数据"""
        # 先插入测试数据
        index_data = [
            {"code": "000001", "date": date(2024, 1, 2), "open": Decimal("3000"), "high": Decimal("3050"),
             "low": Decimal("2980"), "close": Decimal("3030"), "volume": 100000000, "amount": Decimal("300000000000")},
            {"code": "000001", "date": date(2024, 1, 3), "open": Decimal("3030"), "high": Decimal("3080"),
             "low": Decimal("3010"), "close": Decimal("3060"), "volume": 120000000, "amount": Decimal("360000000000")},
            {"code": "000001", "date": date(2024, 1, 4), "open": Decimal("3060"), "high": Decimal("3100"),
             "low": Decimal("3040"), "close": Decimal("3080"), "volume": 130000000, "amount": Decimal("390000000000")},
        ]
        storage.save_index_daily(index_data)

        # 查询最新3天数据
        result = storage.get_latest_index_data("000001", days=3)
        assert len(result) == 3
        # 按日期降序排列
        assert result[0]["date"] == date(2024, 1, 4)
        assert result[2]["date"] == date(2024, 1, 2)

        # 查询最新2天数据
        result = storage.get_latest_index_data("000001", days=2)
        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 4)
        assert result[1]["date"] == date(2024, 1, 3)

    def test_get_fund_flow_history(self, storage):
        """测试查询资金流向历史"""
        # 先插入测试数据
        flow_data = [
            {"date": date(2024, 1, 2), "north_flow": Decimal("1000000000"), "main_flow": Decimal("-500000000"),
             "retail_flow": Decimal("-500000000")},
            {"date": date(2024, 1, 3), "north_flow": Decimal("1500000000"), "main_flow": Decimal("-800000000"),
             "retail_flow": Decimal("-700000000")},
            {"date": date(2024, 1, 4), "north_flow": Decimal("1200000000"), "main_flow": Decimal("-600000000"),
             "retail_flow": Decimal("-600000000")},
            {"date": date(2024, 1, 5), "north_flow": Decimal("1800000000"), "main_flow": Decimal("-900000000"),
             "retail_flow": Decimal("-900000000")},
        ]
        storage.save_fund_flow(flow_data)

        # 查询最近3天数据
        result = storage.get_fund_flow_history(days=3)
        assert len(result) == 3
        # 按日期降序排列
        assert result[0]["date"] == date(2024, 1, 5)
        assert result[2]["date"] == date(2024, 1, 3)

        # 查询最近2天数据
        result = storage.get_fund_flow_history(days=2)
        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 5)
        assert result[1]["date"] == date(2024, 1, 4)
