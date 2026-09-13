import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.fund import Fund
from app.services.data_collector.fund_catalog import FundCatalogError, parse_eastmoney_catalog, upsert_catalog
from app.utils.db import Base


def test_parse_eastmoney_catalog_decodes_utf8_bytes_and_deduplicates_codes():
    content = (
        '\ufeffvar r = [["005827", "YFDLCJ", "易方达蓝筹精选混合", "混合型", ""], '
        '["005827", "YFDLCJ", "新名称", "混合型", ""], '
        '["bad", "", "无效", "", ""]];'
    ).encode("utf-8")

    assert parse_eastmoney_catalog(content) == [{
        "code": "005827", "name": "新名称", "type": "混合型",
    }]


def test_parse_eastmoney_catalog_rejects_unexpected_payload():
    with pytest.raises(FundCatalogError, match="返回格式异常"):
        parse_eastmoney_catalog(b"<html>blocked</html>")


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_upsert_catalog_marks_missing_records_inactive_and_updates_existing(db_session):
    db_session.add_all([
        Fund(code="000001", name="旧名称", type="旧类型", is_active=True),
        Fund(code="000002", name="已下线基金", is_active=True),
    ])
    await db_session.commit()

    counts = await upsert_catalog(db_session, [{
        "code": "000001", "name": "新名称", "type": "混合型",
    }, {
        "code": "005827", "name": "易方达蓝筹精选混合", "type": "混合型",
    }])
    await db_session.commit()

    funds = {fund.code: fund for fund in (await db_session.execute(select(Fund))).scalars()}
    assert counts == {"inserted": 1, "updated": 1, "total": 2}
    assert funds["000001"].name == "新名称"
    assert funds["000001"].is_active is True
    assert funds["005827"].is_active is True
    assert funds["000002"].is_active is False
