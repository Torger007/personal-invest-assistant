"""本地基金目录的下载、校验和入库。

目录下载仅在后台执行。用户搜索始终只查询数据库，因此上游短暂不可用
不会影响新增持仓。
"""
import asyncio
from datetime import datetime
import json
import logging
from typing import Any

import requests
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fund import Fund, FundCatalogSyncRun
from app.utils.db import AsyncSessionLocal

logger = logging.getLogger(__name__)

EASTMONEY_CATALOG_URL = "https://fund.eastmoney.com/js/fundcode_search.js"
CATALOG_SOURCE = "eastmoney_fundcode_search"
MINIMUM_CATALOG_SIZE = 10_000
_sync_lock = asyncio.Lock()


class FundCatalogError(RuntimeError):
    """The catalog provider returned data that must not replace local records."""


def parse_eastmoney_catalog(content: bytes) -> list[dict[str, str]]:
    """Parse the provider's JavaScript payload from raw UTF-8 bytes.

    AKShare currently reads this payload through ``response.text``.  In the
    affected curl_cffi path, that conversion corrupts Chinese text even though
    the bytes are valid UTF-8.  Decoding bytes explicitly avoids that failure.
    """
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise FundCatalogError("基金目录不是 UTF-8 数据") from exc

    prefix = "var r ="
    if not text.startswith(prefix):
        raise FundCatalogError("基金目录返回格式异常")
    payload = text[len(prefix):].strip().rstrip(";")
    try:
        rows = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FundCatalogError("基金目录 JSON 解析失败") from exc

    catalog: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        code, _, name, fund_type = (str(value).strip() for value in row[:4])
        if len(code) == 6 and code.isdigit() and name:
            catalog[code] = {"code": code, "name": name, "type": fund_type}
    return list(catalog.values())


def fetch_eastmoney_catalog() -> list[dict[str, str]]:
    """Download the complete catalog. This function must run off the event loop."""
    response = requests.get(
        EASTMONEY_CATALOG_URL,
        headers={"Accept": "application/javascript, text/javascript, */*;q=0.8"},
        timeout=30,
    )
    response.raise_for_status()
    catalog = parse_eastmoney_catalog(response.content)
    if len(catalog) < MINIMUM_CATALOG_SIZE:
        raise FundCatalogError(
            f"基金目录记录数异常：仅 {len(catalog)} 条，已拒绝写入"
        )
    return catalog


async def upsert_catalog(session: AsyncSession, catalog: list[dict[str, str]]) -> dict[str, int]:
    """Atomically replace catalog activity state and upsert valid records."""
    now = datetime.now()
    existing = {
        fund.code: fund
        for fund in (await session.execute(select(Fund))).scalars()
    }
    inserted = 0
    updated = 0

    # Only execute this after the entire remote payload passes validation.
    # If a later write fails, the caller rolls back and preserves the old index.
    await session.execute(update(Fund).values(is_active=False))
    for item in catalog:
        fund = existing.get(item["code"])
        if fund is None:
            session.add(Fund(
                code=item["code"], name=item["name"], type=item["type"],
                source=CATALOG_SOURCE, catalog_updated_at=now, is_active=True,
            ))
            inserted += 1
            continue
        fund.name = item["name"]
        fund.type = item["type"] or fund.type
        fund.source = CATALOG_SOURCE
        fund.catalog_updated_at = now
        fund.is_active = True
        updated += 1
    return {"inserted": inserted, "updated": updated, "total": len(catalog)}


async def get_catalog_status(session: AsyncSession) -> dict[str, Any]:
    total = await session.scalar(select(func.count()).select_from(Fund).where(Fund.is_active.is_(True)))
    latest = await session.scalar(
        select(FundCatalogSyncRun).order_by(FundCatalogSyncRun.id.desc()).limit(1)
    )
    return {
        "initialized": bool(total),
        "active_funds": total or 0,
        "last_sync": None if latest is None else {
            "status": latest.status,
            "source": latest.source,
            "started_at": latest.started_at.isoformat(),
            "finished_at": latest.finished_at.isoformat() if latest.finished_at else None,
            "total_records": latest.total_records,
            "inserted_records": latest.inserted_records,
            "updated_records": latest.updated_records,
            "error_message": latest.error_message,
        },
    }


async def sync_fund_catalog() -> dict[str, Any]:
    """Fetch and import the catalog, while retaining an auditable failure record."""
    if _sync_lock.locked():
        return {"status": "skipped", "reason": "catalog sync already running"}

    async with _sync_lock:
        async with AsyncSessionLocal() as session:
            run = FundCatalogSyncRun(status="running", source=CATALOG_SOURCE)
            session.add(run)
            await session.commit()
            await session.refresh(run)
            run_id = run.id

            try:
                catalog = await asyncio.to_thread(fetch_eastmoney_catalog)
                counts = await upsert_catalog(session, catalog)
                run.status = "success"
                run.finished_at = datetime.now()
                run.total_records = counts["total"]
                run.inserted_records = counts["inserted"]
                run.updated_records = counts["updated"]
                await session.commit()
                logger.info("基金目录同步完成：%s", counts)
                return {"status": "success", **counts}
            except Exception as exc:
                await session.rollback()
                failed_run = await session.get(FundCatalogSyncRun, run_id)
                if failed_run:
                    failed_run.status = "failed"
                    failed_run.finished_at = datetime.now()
                    failed_run.error_message = str(exc)[:2000]
                    await session.commit()
                logger.exception("基金目录同步失败")
                return {"status": "failed", "error": str(exc)}


async def sync_fund_catalog_if_empty() -> dict[str, Any]:
    """Bootstrap a fresh deployment without delaying a populated deployment."""
    async with AsyncSessionLocal() as session:
        active_count = await session.scalar(
            select(func.count()).select_from(Fund).where(Fund.is_active.is_(True))
        )
    if active_count:
        return {"status": "skipped", "reason": "catalog already initialized"}
    return await sync_fund_catalog()
