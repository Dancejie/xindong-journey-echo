"""Heart Journey Cowork backend: SSO, PostgreSQL state, bounded Agents and media receipts."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import httpx
import psycopg
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row

from backend.game_content import (
    CHARACTER_MAP,
    CHARACTERS,
    apply_choice,
    classify_agent_intent,
    commit_agent_memory,
    create_snapshot,
    project_view,
)

ROOT = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"


def _load_props(path: str) -> dict[str, str]:
    props: dict[str, str] = {}
    try:
        with open(path) as source:
            for raw in source:
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    props[key.strip()] = value.strip()
    except FileNotFoundError:
        pass
    return props


def _get_db_conn() -> psycopg.Connection:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return psycopg.connect(database_url, row_factory=dict_row)
    props = _load_props("db.properties")
    if not props.get("db.host"):
        raise HTTPException(status_code=503, detail="数据库尚未配置")
    return psycopg.connect(
        host=props["db.host"], port=int(props["db.port"]), dbname=props["db.database"],
        user=props["db.username"], password=props["db.password"], row_factory=dict_row,
    )


def _parse_sso_user(decrypted_userinfo: Optional[str]) -> Optional[dict]:
    if not decrypted_userinfo:
        return None
    try:
        data = json.loads(decrypted_userinfo.encode("latin-1").decode("utf-8"))
    except Exception:
        return None
    user_id = data.get("userId") or data.get("id")
    if not user_id:
        return None
    return {
        "userId": str(user_id),
        "username": data.get("username") or data.get("name") or data.get("displayName") or "心动嘉宾",
        "email": data.get("email") or data.get("workEmail"),
    }


def _require_user(decrypted_userinfo: Optional[str], client_id: Optional[str] = None) -> dict:
    user = _parse_sso_user(decrypted_userinfo)
    if user:
        return user
    if os.getenv("APP_AUTH_MODE", "sso").lower() == "public":
        normalized = (client_id or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9-]{16,64}", normalized):
            raise HTTPException(status_code=400, detail="访客身份无效，请刷新页面重试")
        return {"userId": f"public:{normalized}", "username": "心动嘉宾", "email": None}
    raise HTTPException(status_code=401, detail="请先通过小红书内网身份登录")


async def _llm_text(messages: list[dict], max_tokens: int = 500) -> str:
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if deepseek_key:
        base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "thinking": {"type": "disabled"},
                },
            )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        text = str(choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        if not text:
            raise RuntimeError("DeepSeek returned no output text")
        return text
    props = _load_props("ai.properties")
    if not props.get("ai.base_url") or not props.get("ai.api_key"):
        raise RuntimeError("AI gateway is not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{props['ai.base_url']}/bedrock_runtime/model/invoke",
            headers={"token": props["ai.api_key"], "Content-Type": "application/json"},
            json={"anthropic_version": "bedrock-2023-05-31", "max_tokens": max_tokens, "messages": messages},
        )
    data = response.json()
    if data.get("Code") or data.get("Error"):
        raise RuntimeError("Agent service returned a business error")
    return data["content"][0]["text"].strip()


def _load_run(conn: psycopg.Connection, run_id: str, owner_id: str, for_update: bool = False) -> dict:
    suffix = " FOR UPDATE" if for_update else ""
    row = conn.execute(
        f"SELECT id, snapshot, revision FROM game_runs WHERE id = %s AND owner_id = %s{suffix}",
        (run_id, owner_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="没有找到这段心动旅程")
    snapshot = row["snapshot"]
    return json.loads(snapshot) if isinstance(snapshot, str) else snapshot


def _save_run(conn: psycopg.Connection, run_id: str, owner_id: str, snapshot: dict) -> None:
    conn.execute(
        "UPDATE game_runs SET snapshot = %s, revision = %s, updated_at = NOW() WHERE id = %s AND owner_id = %s",
        (json.dumps(snapshot, ensure_ascii=False), snapshot["revision"], run_id, owner_id),
    )


def _record_event(conn: psycopg.Connection, run_id: str, owner_id: str, event_type: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO game_events (run_id, owner_id, event_type, payload) VALUES (%s, %s, %s, %s)",
        (run_id, owner_id, event_type, json.dumps(payload, ensure_ascii=False)),
    )


def _fallback_reply(character: dict, intent: str) -> str:
    if intent == "companion.boundary":
        return f"“我愿意继续聊，但不是用这种方式。”{character['name']}没有离开，只把边界说清楚了。"
    if intent == "companion.flirt":
        return f"“你把这句话留给我，我会当真一点。”{character['name']}看了你一秒，又补了一句：“但我们慢慢来。”"
    if intent == "companion.challenge":
        return f"“认真答案是：我在意。”{character['name']}没有躲开，“剩下的，等你也说真话。”"
    if intent == "companion.listen":
        return f"“我听见了。”{character['name']}把你的原话重复了一小段，“你更想被理解，还是更想有人先留下？”"
    return f"{character['name']}安静地接住这句话：“不用急着让它变成答案，我记得就好。”"


async def _agent_reply(character: dict, snapshot: dict, message: str) -> str:
    intent, _, _ = classify_agent_intent(message)
    memories = [m for m in snapshot["echoMemories"] if m["characterId"] == character["id"]][-4:]
    memory_lines = "\n".join(f"玩家：{m['playerText']}\n你：{m['agentReply']}" for m in memories) or "尚无共同记忆"
    prompt = f"""你正在扮演原创恋综角色 {character['name']}（{character['mbti']}）。
公开面具：{character['publicMask']}
隐秘恐惧：{character['privateFear']}
长期记忆种子：{character['memorySeed']}
说话方式：{character['voice']}
现实边界：{character['boundary']}
已提交的你们之间的独立记忆：
{memory_lines}

玩家刚才说：{message[:240]}
系统已把这次输入裁决为 {intent}。你不能改写数值、剧情事实或玩家意图。
请用 35-90 个中文字符回应。保持恋综镜头感，但像真实的一对一交流；可以追问一个小问题。不要提模型、系统、MBTI 刻板印象、好感数值或后台记忆。若触碰边界，清楚而温和地拒绝。只输出角色回复。"""
    try:
        reply = await _llm_text([{"role": "user", "content": prompt}], max_tokens=220)
        return reply[:480]
    except Exception:
        return _fallback_reply(character, intent)


app = FastAPI(title="心动之旅：MBTI恋综模拟器")
_agent_windows: dict[str, list[float]] = {}


def _enforce_agent_rate_limit(user_id: str) -> None:
    now = time.time()
    window_seconds = 600
    limit = max(1, int(os.getenv("AGENT_RATE_LIMIT", "20")))
    recent = [stamp for stamp in _agent_windows.get(user_id, []) if now - stamp < window_seconds]
    if len(recent) >= limit:
        raise HTTPException(status_code=429, detail="心动信号有点拥挤，请稍后再聊")
    recent.append(now)
    _agent_windows[user_id] = recent


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "xindong-journey-echo",
        "contentVersion": "1.1.0",
        "authMode": os.getenv("APP_AUTH_MODE", "sso"),
        "agentProvider": "deepseek" if os.getenv("DEEPSEEK_API_KEY") else ("cowork" if _load_props("ai.properties").get("ai.api_key") else "fallback"),
        "databaseConfigured": bool(os.getenv("DATABASE_URL") or _load_props("db.properties").get("db.host")),
    }


@app.get("/api/whoami")
def whoami(decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"), x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> JSONResponse:
    return JSONResponse(_require_user(decrypted_userinfo, x_client_id))


@app.get("/api/bootstrap")
def bootstrap(decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"), x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> JSONResponse:
    user = _require_user(decrypted_userinfo, x_client_id)
    with _get_db_conn() as conn:
        row = conn.execute(
            "SELECT snapshot FROM game_runs WHERE owner_id = %s ORDER BY updated_at DESC LIMIT 1", (user["userId"],)
        ).fetchone()
    snapshot = row["snapshot"] if row else None
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)
    return JSONResponse({"user": user, "characters": CHARACTERS, "view": project_view(snapshot) if snapshot else None})


@app.post("/api/runs", status_code=201)
def start_run(body: dict, decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"), x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> JSONResponse:
    user = _require_user(decrypted_userinfo, x_client_id)
    mbti = str(body.get("mbti") or "INFP").upper()
    valid = {"INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"}
    if mbti not in valid:
        raise HTTPException(status_code=400, detail="请选择有效的 MBTI")
    snapshot = create_snapshot(mbti)
    with _get_db_conn() as conn:
        conn.execute(
            "INSERT INTO app_users (id, username, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET username = EXCLUDED.username, email = EXCLUDED.email, updated_at = NOW()",
            (user["userId"], user["username"], user["email"]),
        )
        conn.execute(
            "INSERT INTO game_runs (id, owner_id, content_version, snapshot, revision) VALUES (%s, %s, %s, %s, %s)",
            (snapshot["runId"], user["userId"], snapshot["contentVersion"], json.dumps(snapshot, ensure_ascii=False), 0),
        )
        _record_event(conn, snapshot["runId"], user["userId"], "run.started", {"mbti": mbti})
        conn.commit()
    return JSONResponse(project_view(snapshot), status_code=201)


@app.post("/api/runs/{run_id}/choices")
def choose(run_id: str, body: dict, decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"), x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> JSONResponse:
    user = _require_user(decrypted_userinfo, x_client_id)
    try:
        expected_revision = int(body.get("revision"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="缺少 revision")
    with _get_db_conn() as conn:
        snapshot = _load_run(conn, run_id, user["userId"], for_update=True)
        if snapshot["revision"] != expected_revision:
            raise HTTPException(status_code=409, detail="状态已经更新，请刷新后重试")
        try:
            next_snapshot, receipt = apply_choice(snapshot, str(body.get("choiceId") or ""), body.get("characterId"))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))
        _save_run(conn, run_id, user["userId"], next_snapshot)
        _record_event(conn, run_id, user["userId"], "story.choice", receipt)
        conn.commit()
    return JSONResponse({**project_view(next_snapshot), "receipt": receipt})


@app.post("/api/runs/{run_id}/agents/{character_id}/messages")
async def agent_message(run_id: str, character_id: str, body: dict, decrypted_userinfo: Optional[str] = Header(None, alias="Decrypted-Userinfo"), x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> JSONResponse:
    user = _require_user(decrypted_userinfo, x_client_id)
    character = CHARACTER_MAP.get(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="没有这位嘉宾")
    message = str(body.get("message") or "").strip()
    if not message or len(message) > 240:
        raise HTTPException(status_code=400, detail="请输入 1-240 个字")
    _enforce_agent_rate_limit(user["userId"])
    try:
        expected_revision = int(body.get("revision"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="缺少 revision")
    with _get_db_conn() as conn:
        snapshot = _load_run(conn, run_id, user["userId"])
    if snapshot["revision"] != expected_revision:
        raise HTTPException(status_code=409, detail="状态已经更新，请刷新后重试")
    reply = await _agent_reply(character, snapshot, message)
    with _get_db_conn() as conn:
        current = _load_run(conn, run_id, user["userId"], for_update=True)
        if current["revision"] != expected_revision:
            raise HTTPException(status_code=409, detail="关系状态已变化，这句话没有被重复写入")
        next_snapshot, receipt = commit_agent_memory(current, character_id, message, reply)
        _save_run(conn, run_id, user["userId"], next_snapshot)
        conn.execute(
            "INSERT INTO agent_memories (run_id, owner_id, character_id, memory_id, player_text, agent_reply, intent_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (run_id, user["userId"], character_id, receipt["id"], message, reply, receipt["intentId"]),
        )
        _record_event(conn, run_id, user["userId"], "agent.memory", receipt)
        conn.commit()
    return JSONResponse({**project_view(next_snapshot), "reply": reply, "receipt": receipt})


if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
if (FRONTEND_DIST / "media").exists():
    app.mount("/media", StaticFiles(directory=str(FRONTEND_DIST / "media")), name="media")


@app.get("/")
def index():
    if not INDEX_HTML.exists():
        return HTMLResponse("<h1>《心动之旅》前端尚未构建</h1>", status_code=503)
    return FileResponse(INDEX_HTML)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse({"error": "not found"}, status_code=404)
    real = FRONTEND_DIST / full_path
    if real.is_file():
        return FileResponse(real)
    return FileResponse(INDEX_HTML) if INDEX_HTML.exists() else JSONResponse({"error": "frontend missing"}, status_code=503)
