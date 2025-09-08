import anyio
import pytest
from httpx import AsyncClient
from backend.app.main import app


@pytest.mark.anyio
async def test_healthz():
	async with AsyncClient(app=app, base_url="http://test") as ac:
		r = await ac.get("/healthz")
		assert r.status_code == 200
		assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_search_flow():
	async with AsyncClient(app=app, base_url="http://test") as ac:
		r = await ac.post("/search/start", json={"name":"test user","email":"test@example.com"})
		assert r.status_code == 200
		jid = r.json()["job_id"]
		await anyio.sleep(0.25)
		res = await ac.get(f"/search/{jid}")
		body = res.json()
		assert body["status"] in ("running","completed")
