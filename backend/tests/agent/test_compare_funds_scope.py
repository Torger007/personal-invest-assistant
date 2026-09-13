from app.agent.tools import executor


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, model, code):
        return None


async def test_compare_funds_uses_the_current_users_portfolio_and_advice(monkeypatch):
    async def fake_portfolio(session, user_id):
        assert user_id == "user-1"
        return [{"code": "008163", "name": "用户基金", "weight": 0.4}]

    calls = []

    async def fake_advice(session, fund_code, limit, user_id=None):
        calls.append((fund_code, limit, user_id))
        return []

    monkeypatch.setattr(executor, "AsyncSessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(executor, "get_user_portfolio", fake_portfolio)
    monkeypatch.setattr(executor, "_fetch_advice_records", fake_advice)

    result = await executor._execute_compare_funds({}, "user-1")

    assert result["data"]["funds"][0]["fund_name"] == "用户基金"
    assert calls == [("008163", 1, "user-1")]


async def test_compare_funds_requires_user_context():
    result = await executor._execute_compare_funds({}, None)

    assert result["status"] == "error"
