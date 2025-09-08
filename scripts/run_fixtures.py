import json
import anyio
from httpx import AsyncClient
from backend.app.main import app


async def run():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        with open("backend/fixtures/personas.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                payload = json.loads(line)
                r = await ac.post("/search/start", json=payload)
                jid = r.json()["job_id"]
                await anyio.sleep(0.3)
                res = await ac.get(f"/search/{jid}")
                print(json.dumps(res.json(), ensure_ascii=False)[:400] + "...")


if __name__ == "__main__":
    anyio.run(run)

