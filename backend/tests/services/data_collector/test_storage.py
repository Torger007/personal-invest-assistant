"""数据存储层单元测试（异步PostgreSQL版本，使用aiosqlite内存数据库测试）"""
import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.services.data_collector.storage import DataStorage
from app.utils.db import Base


@pytest_asyncio.fixture
async def db_session():
    """创建测试用异步数据库会话（aiosqlite内存数据库）"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def storage(db_session):
    """创建DataStorage实例"""
    return DataStorage(db_session)


class TestDataStorage:
    """数据存储层测试类"""

    async def test_save_fund_info(self, storage):
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
        result = await storage.save_fund_info(fund_data)
        assert result is True

        # 测试更新已有基金
        updated_data = {
            "code": "000001",
            "name": "华夏成长混合A",
            "type": "混合型",
            "manager": "李四",
            "company": "华夏基金",
            "create_date": date(2020, 1, 1)
        }
        result = await storage.save_fund_info(updated_data)
        assert result is True

        # 通过查询接口验证更新结果
        records = await storage.get_latest_index_data("000001")
        # 基金信息通过 save_fund_info 保存，这里直接查询验证
        from app.models.fund import Fund
        from sqlalchemy import select
        res = await storage._db.execute(select(Fund).where(Fund.code == "000001"))
        fund = res.scalar_one_or_none()
        assert fund is not None
        assert fund.name == "华夏成长混合A"
        assert fund.manager == "李四"

    async def test_save_index_daily(self, storage):
        """测试保存指数日线数据"""
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

        result = await storage.save_index_daily(index_data)
        assert result is True

        # 验证数据已保存（通过查询接口）
        records = await storage.get_latest_index_data("000001", days=10)
        assert len(records) == 2

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
        result = await storage.save_index_daily(updated_data)
        assert result is True

        # 验证没有新增重复记录
        records = await storage.get_latest_index_data("000001", days=10)
        assert len(records) == 2

        # 验证数据已更新
        updated_record = next(r for r in records if r["date"] == date(2024, 1, 2))
        assert updated_record["close"] == Decimal("3040.00")
        assert updated_record["volume"] == 110000000

    async def test_save_fund_flow(self, storage):
        """测试保存资金流向数据"""
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

        result = await storage.save_fund_flow(flow_data)
        assert result is True

        records = await storage.get_fund_flow_history(days=10)
        assert len(records) == 2

        # 测试更新已有数据
        updated_data = [
            {
                "date": date(2024, 1, 2),
                "north_flow": Decimal("1200000000.00"),
                "main_flow": Decimal("-600000000.00"),
                "retail_flow": Decimal("-600000000.00")
            }
        ]
        result = await storage.save_fund_flow(updated_data)
        assert result is True

        records = await storage.get_fund_flow_history(days=10)
        assert len(records) == 2
        updated_record = next(r for r in records if r["date"] == date(2024, 1, 2))
        assert updated_record["north_flow"] == Decimal("1200000000.00")
        assert updated_record["main_flow"] == Decimal("-600000000.00")

    async def test_get_latest_index_data(self, storage):
        """测试查询最新指数数据"""
        index_data = [
            {"code": "000001", "date": date(2024, 1, 2), "open": Decimal("3000"), "high": Decimal("3050"),
             "low": Decimal("2980"), "close": Decimal("3030"), "volume": 100000000, "amount": Decimal("300000000000")},
            {"code": "000001", "date": date(2024, 1, 3), "open": Decimal("3030"), "high": Decimal("3080"),
             "low": Decimal("3010"), "close": Decimal("3060"), "volume": 120000000, "amount": Decimal("360000000000")},
            {"code": "000001", "date": date(2024, 1, 4), "open": Decimal("3060"), "high": Decimal("3100"),
             "low": Decimal("3040"), "close": Decimal("3080"), "volume": 130000000, "amount": Decimal("390000000000")},
        ]
        await storage.save_index_daily(index_data)

        result = await storage.get_latest_index_data("000001", days=3)
        assert len(result) == 3
        # 按日期降序排列
        assert result[0]["date"] == date(2024, 1, 4)
        assert result[2]["date"] == date(2024, 1, 2)

        result = await storage.get_latest_index_data("000001", days=2)
        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 4)
        assert result[1]["date"] == date(2024, 1, 3)

    async def test_get_fund_flow_history(self, storage):
        """测试查询资金流向历史"""
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
        await storage.save_fund_flow(flow_data)

        result = await storage.get_fund_flow_history(days=3)
        assert len(result) == 3
        assert result[0]["date"] == date(2024, 1, 5)
        assert result[2]["date"] == date(2024, 1, 3)

        result = await storage.get_fund_flow_history(days=2)
        assert len(result) == 2
        assert result[0]["date"] == date(2024, 1, 5)
        assert result[1]["date"] == date(2024, 1, 4)

    async def test_sector_queries_only_use_the_latest_snapshot(self, storage):
        """Old high performers must not appear in the current board ranking."""
        await storage.save_sector_board([
            {
                "code": "old", "name": "Old winner", "type": "concept",
                "change_pct": 10.0, "volume": 0.0, "amount": 0.0,
                "leader": "", "leader_change": 0.0, "snap_date": date(2024, 1, 2),
            },
            {
                "code": "old-2", "name": "Old loser", "type": "concept",
                "change_pct": -5.0, "volume": 0.0, "amount": 0.0,
                "leader": "", "leader_change": 0.0, "snap_date": date(2024, 1, 2),
            },
        ])
        await storage.save_sector_board([
            {
                "code": "new", "name": "Current winner", "type": "concept",
                "change_pct": 1.0, "volume": 0.0, "amount": 0.0,
                "leader": "", "leader_change": 0.0, "snap_date": date(2024, 1, 3),
            },
            {
                "code": "new-2", "name": "Current runner-up", "type": "concept",
                "change_pct": 0.5, "volume": 0.0, "amount": 0.0,
                "leader": "", "leader_change": 0.0, "snap_date": date(2024, 1, 3),
            },
        ])

        boards = await storage.get_sector_board("concept", limit=10)
        assert [board["name"] for board in boards] == ["Current winner", "Current runner-up"]
        assert {board["snap_date"] for board in boards} == {"2024-01-03"}
        assert await storage.get_latest_sector_snapshot_date("concept") == date(2024, 1, 3)
        assert await storage.get_hot_sectors("concept", top_n=1) == ["Current winner"]
