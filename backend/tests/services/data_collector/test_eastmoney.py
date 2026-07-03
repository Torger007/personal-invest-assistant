"""东方财富数据源单元测试"""
import pytest
from datetime import date, datetime
from app.services.data_collector.eastmoney import EastMoneySource


@pytest.mark.asyncio
async def test_get_index_daily_sample():
    """测试获取指数日线数据（真实请求）"""
    source = EastMoneySource()
    try:
        data = await source.get_index_daily("000001", days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert "code" in record
            assert "date" in record
            assert "open" in record
            assert "high" in record
            assert "low" in record
            assert "close" in record
            assert "volume" in record
            assert "amount" in record
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_index_daily_shanghai():
    """测试获取上证指数日线数据"""
    source = EastMoneySource()
    try:
        data = await source.get_index_daily("000001", days=10)
        assert isinstance(data, list)
        assert len(data) <= 10

        if len(data) > 0:
            # 验证数据结构
            record = data[0]
            assert record["code"] == "000001"
            assert isinstance(record["date"], date)
            assert isinstance(record["open"], float)
            assert isinstance(record["high"], float)
            assert isinstance(record["low"], float)
            assert isinstance(record["close"], float)
            assert isinstance(record["volume"], int)
            assert isinstance(record["amount"], float)

            # 验证价格合理性
            assert record["open"] > 0
            assert record["high"] >= record["low"]
            assert record["high"] >= record["open"]
            assert record["low"] <= record["close"]
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_index_daily_shenzhen():
    """测试获取深证成指日线数据"""
    source = EastMoneySource()
    try:
        data = await source.get_index_daily("399001", days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert record["code"] == "399001"
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_index_daily_chinext():
    """测试获取创业板指日线数据"""
    source = EastMoneySource()
    try:
        data = await source.get_index_daily("399006", days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert record["code"] == "399006"
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_index_daily_empty_result():
    """测试无效指数代码返回空结果"""
    source = EastMoneySource()
    try:
        data = await source.get_index_daily("999999", days=5)
        assert isinstance(data, list)
        # 无效指数代码应返回空列表或无数据
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_index_daily_days_parameter():
    """测试days参数控制返回数据量"""
    source = EastMoneySource()
    try:
        # 获取5天数据
        data_5 = await source.get_index_daily("000001", days=5)
        # 获取10天数据
        data_10 = await source.get_index_daily("000001", days=10)

        assert len(data_5) <= 5
        assert len(data_10) <= 10
        assert len(data_5) <= len(data_10)
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_fund_flow_sample():
    """测试获取资金流向数据（真实请求）"""
    source = EastMoneySource()
    try:
        data = await source.get_fund_flow(days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert "date" in record
            assert "north_flow" in record
            assert "main_flow" in record
            assert "retail_flow" in record
            assert isinstance(record["date"], date)
            assert isinstance(record["north_flow"], float)
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_fund_flow_days_parameter():
    """测试days参数控制资金流向数据量"""
    source = EastMoneySource()
    try:
        data_5 = await source.get_fund_flow(days=5)
        data_10 = await source.get_fund_flow(days=10)

        assert len(data_5) <= 5
        assert len(data_10) <= 10
        assert len(data_5) <= len(data_10)
    finally:
        await source.close()
