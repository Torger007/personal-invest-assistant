"""Run ``python -m app.jobs.sync_fund_catalog`` after migrations are applied."""
import asyncio

# The collector relies on the same network setup as the web application.
from app import startup_patch  # noqa: F401
from app.services.data_collector.fund_catalog import sync_fund_catalog


if __name__ == "__main__":
    result = asyncio.run(sync_fund_catalog())
    print(result)
    raise SystemExit(0 if result["status"] == "success" else 1)
