"""天天基金数据源单元测试"""
import pytest
from datetime import date
from app.services.data_collector.tiantian import TianTianSource


@pytest.mark.asyncio
async def test_get_fund_nav_sample():
    """测试获取基金净值数据（真实请求）"""
    source = TianTianSource()
    try:
        # 005827 易方达蓝筹精选混合
        data = await source.get_fund_nav("005827", days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert "fund_code" in record
            assert "date" in record
            assert "unit_nav" in record
            assert "acc_nav" in record
            assert "daily_return" in record
            assert record["fund_code"] == "005827"
            assert isinstance(record["date"], date)
            assert record["unit_nav"] > 0
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_fund_nav_days_parameter():
    """测试days参数控制净值数据量"""
    source = TianTianSource()
    try:
        data_5 = await source.get_fund_nav("005827", days=5)
        data_10 = await source.get_fund_nav("005827", days=10)

        assert isinstance(data_5, list)
        assert isinstance(data_10, list)
        assert len(data_5) <= 5
        assert len(data_10) <= 10
        assert len(data_5) <= len(data_10)
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_fund_nav_invalid_code():
    """测试无效基金代码返回空结果"""
    source = TianTianSource()
    try:
        data = await source.get_fund_nav("999999", days=5)
        assert isinstance(data, list)
        # 无效基金代码应返回空列表
        assert len(data) == 0
    finally:
        await source.close()


@pytest.mark.asyncio
async def test_get_fund_info_sample():
    """测试获取基金基本信息（真实请求）"""
    source = TianTianSource()
    try:
        info = await source.get_fund_info("005827")
        assert isinstance(info, dict)
        assert info.get("code") == "005827"
        # 名称可能为空（取决于JS解析），但有值时应为字符串
        if "name" in info:
            assert isinstance(info["name"], str)
    finally:
        await source.close()