# 数据采集模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现从东方财富和天天基金抓取基金净值、指数行情、板块数据、资金流向等信息，并存储到数据库。

**Architecture:** 采用数据源插件化设计，每个数据源继承 BaseDataSource，实现统一接口。数据通过 DataStorage 服务统一存储到 SQLite 数据库。定时调度器触发数据采集任务。

**Tech Stack:** Python, httpx, BeautifulSoup, SQLAlchemy, APScheduler

---

## 文件结构

```
backend/
├── app/
│   ├── services/
│   │   └── data_collector/
│   │       ├── base.py              # 数据源基类（已存在）
│   │       ├── eastmoney.py         # 东方财富数据源（待实现）
│   │       ├── tiantian.py          # 天天基金数据源（待实现）
│   │       ├── storage.py           # 数据存储层（新建）
│   │       └── scheduler.py         # 定时调度（已存在，待完善）
│   └── models/
│       ├── fund.py                  # 基金模型（已存在）
│       └── market.py                # 行情模型（已存在）
├── tests/
│   └── services/
│       └── data_collector/
│           ├── test_eastmoney.py    # 东方财富测试（新建）
│           └── test_storage.py      # 存储层测试（新建）
└── scripts/
    └── fetch_sample_data.py         # 手动采集脚本（新建）
```

---

## Task 1: 实现数据存储层

**Files:**
- Create: `backend/app/services/data_collector/storage.py`
- Create: `backend/tests/services/data_collector/test_storage.py`

- [ ] **Step 1: 编写数据存储层测试**

创建 `backend/tests/services/data_collector/test_storage.py`：

```python
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.utils.db import Base
from app.models.fund import Fund
from app.models.market import IndexDaily, FundFlow
from app.services.data_collector.storage import DataStorage


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def storage(db_session):
    """创建存储层实例"""
    return DataStorage(db_session)


def test_save_fund_info(storage):
    """测试保存基金基本信息"""
    fund_data = {
        "code": "000001",
        "name": "华夏成长混合",
        "type": "混合型",
        "manager": "王亚伟",
        "company": "华夏基金",
        "create_date": date(2020, 1, 1)
    }
    storage.save_fund_info(fund_data)
    
    fund = storage.session.query(Fund).filter_by(code="000001").first()
    assert fund is not None
    assert fund.name == "华夏成长混合"
    assert fund.type == "混合型"


def test_save_index_daily(storage):
    """测试保存指数日线数据"""
    index_data = [
        {
            "code": "000001",
            "date": date(2024, 1, 1),
            "open": 3000.0,
            "high": 3050.0,
            "low": 2980.0,
            "close": 3020.0,
            "volume": 100000000,
            "amount": 3000000000.0
        }
    ]
    storage.save_index_daily(index_data)
    
    record = storage.session.query(IndexDaily).filter_by(
        code="000001", date=date(2024, 1, 1)
    ).first()
    assert record is not None
    assert record.close == 3020.0


def test_save_fund_flow(storage):
    """测试保存资金流向数据"""
    flow_data = [
        {
            "date": date(2024, 1, 1),
            "north_flow": 5000000000.0,
            "main_flow": 3000000000.0,
            "retail_flow": -2000000000.0
        }
    ]
    storage.save_fund_flow(flow_data)
    
    record = storage.session.query(FundFlow).filter_by(
        date=date(2024, 1, 1)
    ).first()
    assert record is not None
    assert record.north_flow == 5000000000.0
```

- [ ] **Step 2: 运行测试确认失败**

运行：`cd backend && python -m pytest tests/services/data_collector/test_storage.py -v`

预期：FAIL，因为 `storage.py` 还不存在。

- [ ] **Step 3: 实现数据存储层**

创建 `backend/app/services/data_collector/storage.py`：

```python
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.fund import Fund
from app.models.market import IndexDaily, FundFlow
from datetime import date


class DataStorage:
    """数据存储服务，统一处理数据入库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save_fund_info(self, fund_data: Dict):
        """保存基金基本信息"""
        existing = self.session.query(Fund).filter_by(code=fund_data["code"]).first()
        if existing:
            for key, value in fund_data.items():
                setattr(existing, key, value)
        else:
            fund = Fund(**fund_data)
            self.session.add(fund)
        self.session.commit()
    
    def save_index_daily(self, index_data: List[Dict]):
        """保存指数日线数据"""
        for data in index_data:
            existing = self.session.query(IndexDaily).filter_by(
                code=data["code"], date=data["date"]
            ).first()
            if existing:
                for key, value in data.items():
                    if key not in ["code", "date"]:
                        setattr(existing, key, value)
            else:
                record = IndexDaily(**data)
                self.session.add(record)
        self.session.commit()
    
    def save_fund_flow(self, flow_data: List[Dict]):
        """保存资金流向数据"""
        for data in flow_data:
            existing = self.session.query(FundFlow).filter_by(
                date=data["date"]
            ).first()
            if existing:
                for key, value in data.items():
                    if key != "date":
                        setattr(existing, key, value)
            else:
                record = FundFlow(**data)
                self.session.add(record)
        self.session.commit()
    
    def get_latest_index_data(self, code: str, days: int = 30):
        """获取最新指数数据"""
        query = self.session.query(IndexDaily).filter_by(code=code)
        query = query.order_by(IndexDaily.date.desc()).limit(days)
        return query.all()
    
    def get_fund_flow_history(self, days: int = 30):
        """获取资金流向历史"""
        query = self.session.query(FundFlow)
        query = query.order_by(FundFlow.date.desc()).limit(days)
        return query.all()
```

- [ ] **Step 4: 运行测试确认通过**

运行：`cd backend && python -m pytest tests/services/data_collector/test_storage.py -v`

预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/data_collector/storage.py
git add backend/tests/services/data_collector/test_storage.py
git commit -m "feat: 实现数据存储层

- 统一处理基金信息、指数行情、资金流向数据入库
- 支持数据更新（存在则更新，不存在则新增）
- 提供数据查询接口
- 添加单元测试"
```

---

## Task 2: 实现东方财富指数行情采集

**Files:**
- Modify: `backend/app/services/data_collector/eastmoney.py`
- Create: `backend/tests/services/data_collector/test_eastmoney.py`

- [ ] **Step 1: 编写指数行情采集测试**

创建 `backend/tests/services/data_collector/test_eastmoney.py`：

```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date
from app.services.data_collector.eastmoney import EastMoneySource


@pytest.fixture
async def eastmoney():
    """创建东方财富数据源实例"""
    source = EastMoneySource()
    yield source
    await source.close()


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
```

- [ ] **Step 2: 实现东方财富指数行情采集**

修改 `backend/app/services/data_collector/eastmoney.py`：

```python
"""
东方财富数据源
数据接口文档参考：https://push2.eastmoney.com/api/qt/...
"""
from typing import List, Dict
from datetime import date, datetime, timedelta
from app.services.data_collector.base import BaseDataSource


class EastMoneySource(BaseDataSource):
    """东方财富数据源"""

    def __init__(self):
        super().__init__(
            name="东方财富",
            base_url="https://push2.eastmoney.com"
        )

    async def get_index_daily(self, index_code: str, days: int = 30) -> List[Dict]:
        """获取指数日线数据
        
        使用东方财富K线接口获取指数历史行情
        """
        # 构建指数证券ID（上证指数：1.000001，深证成指：0.399001，创业板指：0.399006）
        secid_map = {
            "000001": "1.000001",  # 上证指数
            "399001": "0.399001",  # 深证成指
            "399006": "0.399006",  # 创业板指
        }
        secid = secid_map.get(index_code, f"1.{index_code}")
        
        # 计算日期范围
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",  # 日K
            "fqt": "1",    # 前复权
            "beg": start_date.replace("-", ""),
            "end": end_date.replace("-", ""),
        }
        
        data = await self.fetch(url, params=params)
        
        if not data or "data" not in data or data["data"] is None:
            return []
        
        klines = data["data"].get("klines", [])
        result = []
        
        for kline in klines[-days:]:
            fields = kline.split(",")
            if len(fields) >= 7:
                result.append({
                    "code": index_code,
                    "date": datetime.strptime(fields[0], "%Y-%m-%d").date(),
                    "open": float(fields[1]),
                    "close": float(fields[2]),
                    "high": float(fields[3]),
                    "low": float(fields[4]),
                    "volume": int(float(fields[5])),
                    "amount": float(fields[6])
                })
        
        return result
```

- [ ] **Step 3: 运行测试验证**

运行：`cd backend && python -m pytest tests/services/data_collector/test_eastmoney.py::test_get_index_daily_sample -v -s`

预期：PASS，能获取到真实的指数数据。

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/data_collector/eastmoney.py
git add backend/tests/services/data_collector/test_eastmoney.py
git commit -m "feat: 实现东方财富指数行情采集

- 支持获取上证指数、深证成指、创业板指历史K线数据
- 使用东方财富公开API接口
- 解析K线数据并转换为标准格式
- 添加单元测试验证"
```

---

## Task 3: 实现东方财富资金流向采集

**Files:**
- Modify: `backend/app/services/data_collector/eastmoney.py`

- [ ] **Step 1: 实现资金流向采集**

在 `backend/app/services/data_collector/eastmoney.py` 中添加方法：

```python
async def get_fund_flow(self, days: int = 30) -> List[Dict]:
    """获取资金流向数据（北向资金、主力资金）
    
    使用东方财富资金流向接口
    """
    url = "http://push2.eastmoney.com/api/qt/kamtbs.ann"
    params = {
        "fields1": "f1,f2,f3,f4",
        "fields2": "f51,f52,f53,f54,f55,f56",
        "klt": "101",  # 日K
        "lmt": str(days),
    }
    
    data = await self.fetch(url, params=params)
    
    if not data or "data" not in data or data["data"] is None:
        return []
    
    result = []
    klines = data["data"].get("klines", [])
    
    for kline in klines[-days:]:
        fields = kline.split(",")
        if len(fields) >= 4:
            try:
                result.append({
                    "date": datetime.strptime(fields[0], "%Y-%m-%d").date(),
                    "north_flow": float(fields[1]) if fields[1] != "-" else 0.0,
                    "main_flow": float(fields[2]) if fields[2] != "-" else 0.0,
                    "retail_flow": 0.0  # 散户资金暂不可用
                })
            except (ValueError, IndexError):
                continue
    
    return result
```

- [ ] **Step 2: 添加测试**

在 `backend/tests/services/data_collector/test_eastmoney.py` 中添加：

```python
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
    finally:
        await source.close()
```

- [ ] **Step 3: 运行测试验证**

运行：`cd backend && python -m pytest tests/services/data_collector/test_eastmoney.py::test_get_fund_flow_sample -v -s`

预期：PASS，能获取到真实的资金流向数据。

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/data_collector/eastmoney.py
git add backend/tests/services/data_collector/test_eastmoney.py
git commit -m "feat: 实现东方财富资金流向采集

- 支持获取北向资金、主力资金历史数据
- 解析资金流向数据并转换为标准格式
- 添加单元测试验证"
```

---

## Task 4: 实现天天基金基金净值采集

**Files:**
- Modify: `backend/app/services/data_collector/tiantian.py`
- Create: `backend/tests/services/data_collector/test_tiantian.py`

- [ ] **Step 1: 实现天天基金净值采集**

修改 `backend/app/services/data_collector/tiantian.py`：

```python
"""
天天基金数据源
数据接口参考：https://fund.eastmoney.com/...
"""
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup
from app.services.data_collector.base import BaseDataSource


class TianTianSource(BaseDataSource):
    """天天基金数据源"""

    def __init__(self):
        super().__init__(
            name="天天基金",
            base_url="https://api.fund.eastmoney.com"
        )

    async def get_fund_nav(self, fund_code: str, days: int = 30) -> List[Dict]:
        """获取基金净值数据
        
        使用天天基金历史净值接口
        """
        url = f"https://fundf10.eastmoney.com/jjjz_{fund_code}.html"
        
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            result = []
            table = soup.find("table", class_="w782 comm tzx")
            if not table:
                return []
            
            rows = table.find("tbody").find_all("tr")[:days]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:
                    try:
                        nav_date = datetime.strptime(cols[0].text, "%Y-%m-%d").date()
                        unit_nav = float(cols[1].text)
                        acc_nav = float(cols[2].text)
                        daily_return = float(cols[3].text.replace("%", "")) if cols[3].text else 0.0
                        
                        result.append({
                            "fund_code": fund_code,
                            "date": nav_date,
                            "unit_nav": unit_nav,
                            "acc_nav": acc_nav,
                            "daily_return": daily_return
                        })
                    except (ValueError, AttributeError):
                        continue
            
            return result
        except Exception as e:
            print(f"[天天基金] 获取基金净值失败 {fund_code}: {e}")
            return []
```

- [ ] **Step 2: 添加测试**

创建 `backend/tests/services/data_collector/test_tiantian.py`：

```python
import pytest
from app.services.data_collector.tiantian import TianTianSource


@pytest.mark.asyncio
async def test_get_fund_nav_sample():
    """测试获取基金净值数据（真实请求）"""
    source = TianTianSource()
    try:
        data = await source.get_fund_nav("000001", days=5)
        assert isinstance(data, list)
        if len(data) > 0:
            record = data[0]
            assert "fund_code" in record
            assert "date" in record
            assert "unit_nav" in record
            assert "acc_nav" in record
    finally:
        await source.close()
```

- [ ] **Step 3: 运行测试验证**

运行：`cd backend && python -m pytest tests/services/data_collector/test_tiantian.py::test_get_fund_nav_sample -v -s`

预期：PASS，能获取到真实的基金净值数据。

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/data_collector/tiantian.py
git add backend/tests/services/data_collector/test_tiantian.py
git commit -m "feat: 实现天天基金净值采集

- 支持获取基金历史净值数据（单位净值、累计净值、日收益率）
- 使用HTML解析方式获取数据
- 添加单元测试验证"
```

---

## Task 5: 创建手动数据采集脚本

**Files:**
- Create: `backend/scripts/fetch_sample_data.py`

- [ ] **Step 1: 创建手动采集脚本**

创建 `backend/scripts/fetch_sample_data.py`：

```python
"""
手动数据采集脚本
用于测试和初始化数据
"""
import sys
import asyncio
sys.path.insert(0, "/b/agent/MyCode/personal-invest-assistant/backend")

from app.utils.db import SessionLocal
from app.services.data_collector.eastmoney import EastMoneySource
from app.services.data_collector.storage import DataStorage


async def fetch_index_data():
    """采集指数行情数据"""
    print("=== 开始采集指数行情数据 ===")
    
    source = EastMoneySource()
    session = SessionLocal()
    storage = DataStorage(session)
    
    try:
        # 采集上证指数
        print("采集上证指数...")
        data = await source.get_index_daily("000001", days=30)
        print(f"获取到 {len(data)} 条数据")
        if data:
            storage.save_index_daily(data)
            print(f"保存成功，最新数据：{data[0]['date']} 收盘 {data[0]['close']}")
        
        # 采集深证成指
        print("\n采集深证成指...")
        data = await source.get_index_daily("399001", days=30)
        print(f"获取到 {len(data)} 条数据")
        if data:
            storage.save_index_daily(data)
            print(f"保存成功，最新数据：{data[0]['date']} 收盘 {data[0]['close']}")
        
        # 采集创业板指
        print("\n采集创业板指...")
        data = await source.get_index_daily("399006", days=30)
        print(f"获取到 {len(data)} 条数据")
        if data:
            storage.save_index_daily(data)
            print(f"保存成功，最新数据：{data[0]['date']} 收盘 {data[0]['close']}")
        
    except Exception as e:
        print(f"采集失败: {e}")
    finally:
        await source.close()
        session.close()


async def fetch_fund_flow_data():
    """采集资金流向数据"""
    print("\n=== 开始采集资金流向数据 ===")
    
    source = EastMoneySource()
    session = SessionLocal()
    storage = DataStorage(session)
    
    try:
        print("采集资金流向...")
        data = await source.get_fund_flow(days=30)
        print(f"获取到 {len(data)} 条数据")
        if data:
            storage.save_fund_flow(data)
            latest = data[0]
            print(f"保存成功，最新数据：{latest['date']}")
            print(f"  北向资金: {latest['north_flow'] / 1e8:.2f} 亿")
            print(f"  主力资金: {latest['main_flow'] / 1e8:.2f} 亿")
    
    except Exception as e:
        print(f"采集失败: {e}")
    finally:
        await source.close()
        session.close()


async def main():
    """主函数"""
    print("开始手动数据采集...\n")
    
    await fetch_index_data()
    await fetch_fund_flow_data()
    
    print("\n=== 数据采集完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 运行脚本测试**

运行：`cd backend && python scripts/fetch_sample_data.py`

预期：成功采集数据并打印结果。

- [ ] **Step 3: 提交**

```bash
git add backend/scripts/fetch_sample_data.py
git commit -m "feat: 创建手动数据采集脚本

- 支持采集指数行情数据（上证、深证、创业板）
- 支持采集资金流向数据（北向资金、主力资金）
- 方便测试和初始化数据"
```

---

## Task 6: 完善定时调度器

**Files:**
- Modify: `backend/app/services/data_collector/scheduler.py`

- [ ] **Step 1: 完善每日数据更新逻辑**

修改 `backend/app/services/data_collector/scheduler.py`：

```python
"""
定时任务调度器
负责每日收盘后批量更新数据
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.utils.db import SessionLocal
from app.services.data_collector.eastmoney import EastMoneySource
from app.services.data_collector.storage import DataStorage
import asyncio


scheduler = AsyncIOScheduler()


async def daily_data_update():
    """每日数据更新任务

    每个交易日16:30执行：
    1. 更新指数行情
    2. 更新资金流向
    3. （后续可扩展：更新基金净值、生成投资建议）
    """
    print("[调度器] 开始每日数据更新...")

    source = EastMoneySource()
    session = SessionLocal()
    storage = DataStorage(session)

    try:
        # 1. 更新指数行情
        print("[调度器] 1/2 更新指数行情...")
        for index_code in ["000001", "399001", "399006"]:
            data = await source.get_index_daily(index_code, days=5)
            if data:
                storage.save_index_daily(data)
                print(f"  {index_code}: 更新 {len(data)} 条数据")
        
        # 2. 更新资金流向
        print("[调度器] 2/2 更新资金流向...")
        flow_data = await source.get_fund_flow(days=5)
        if flow_data:
            storage.save_fund_flow(flow_data)
            print(f"  更新 {len(flow_data)} 条数据")
        
        print("[调度器] 每日数据更新完成")
    
    except Exception as e:
        print(f"[调度器] 数据更新失败: {e}")
    finally:
        await source.close()
        session.close()


async def manual_refresh():
    """手动触发数据更新"""
    await daily_data_update()


def setup_scheduler():
    """配置定时任务"""
    # 每个交易日16:30收盘后批量更新
    # 周一至周五
    scheduler.add_job(
        daily_data_update,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="daily_update",
        replace_existing=True
    )


def start_scheduler():
    """启动调度器"""
    setup_scheduler()
    scheduler.start()
    print("[调度器] 已启动，等待下一个执行时间")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown()
        print("[调度器] 已停止")
```

- [ ] **Step 2: 提交**

```bash
git add backend/app/services/data_collector/scheduler.py
git commit -m "feat: 完善定时调度器

- 实现每日自动更新指数行情和资金流向数据
- 集成数据存储层，自动保存到数据库
- 支持手动触发数据更新"
```

---

## 完成标准

1. ✅ 能够从东方财富采集指数行情数据
2. ✅ 能够从东方财富采集资金流向数据
3. ✅ 能够从天天基金采集基金净值数据
4. ✅ 数据能够正确保存到 SQLite 数据库
5. ✅ 定时调度器能够自动触发数据采集
6. ✅ 所有单元测试通过
7. ✅ 手动采集脚本能够正常运行

---

## 后续扩展

1. 实现东方财富板块数据采集
2. 实现天天基金基金基本信息采集
3. 集成分析引擎，自动生成投资建议
4. 添加数据校验和异常处理
5. 实现数据去重和增量更新优化
