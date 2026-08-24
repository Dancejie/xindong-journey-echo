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
    CHARACTER_CARD_MAP,
    CHARACTER_MAP,
    CHARACTERS,
    apply_choice,
    commit_agent_turn,
    create_snapshot,
    migrate_snapshot,
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
    if not deepseek_key:
        raise RuntimeError("DeepSeek is not configured")
    base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False, "thinking": {"type": "disabled"}},
        )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    text = str(choices[0].get("message", {}).get("content") or "").strip() if choices else ""
    if not text:
        raise RuntimeError("DeepSeek returned no output text")
    return text


def _load_run(conn: psycopg.Connection, run_id: str, owner_id: str, for_update: bool = False) -> dict:
    suffix = " FOR UPDATE" if for_update else ""
    row = conn.execute(
        f"SELECT id, snapshot, revision FROM game_runs WHERE id = %s AND owner_id = %s{suffix}",
        (run_id, owner_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="没有找到这段心动旅程")
    snapshot = row["snapshot"]
    raw = json.loads(snapshot) if isinstance(snapshot, str) else snapshot
    migrated = migrate_snapshot(raw)
    assert migrated is not None
    return migrated


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


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise RuntimeError("DeepSeek did not return a JSON object")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise RuntimeError("DeepSeek returned a non-object payload")
    return data


async def _agent_turn(character: dict, snapshot: dict, message: str) -> dict:
    card = CHARACTER_CARD_MAP[character["id"]]
    memories = [item for item in snapshot["echoMemories"] if item.get("characterId") == character["id"]][-6:]
    events = [item for item in snapshot.get("eventLedger", []) if item.get("characterId") == character["id"]]
    context = {
        "scene": {"nodeId": snapshot["nodeId"], "flags": snapshot["flags"]},
        "player": snapshot["player"],
        "relationship": snapshot["relationships"][character["id"]],
        "currentAttitude": snapshot["attitudes"].get(character["id"], "curious"),
        "recentMemories": [{key: item.get(key) for key in ("kind", "summary", "interpretation", "rawQuote", "agentReply", "attitude")} for item in memories],
        "activatedEvents": events,
    }
    schema = {
        "dialogue": "35-120个中文字符的原创角色台词",
        "stageDirection": "不超过30字、镜头可见的动作",
        "attitude": sorted(["warm", "curious", "guarded", "challenging", "vulnerable", "softened", "uncertain", "honest", "moved", "careful", "steady", "boundary"]),
        "intentId": card["agentPolicy"]["allowedIntentIds"],
        "publicReason": "不暴露后台的关系变化原因，不超过40字",
        "relationshipDelta": {axis: "必须为人物卡对应范围内整数" for axis in card["agentPolicy"]["deltaBounds"]},
        "memory": {"kind": ["episodic", "promise", "preference", "semantic"], "summary": "第三人称事实摘要", "interpretation": "角色自己的可修正理解", "salience": "0-100整数", "emotionalValence": "-100到100整数"},
        "proposedEventId": [None, *card["agentPolicy"]["allowedEventIds"]],
    }
    system = """你是回声剧场的角色决策 Agent。你不是通用陪聊助手。
你必须只依据人物卡、当前场景、该角色可见的关系与私有记忆做出本轮判断。
人物台词、态度、七轴变化、新记忆和事件意图必须来自同一次角色判断。
MBTI 只是一层行为偏好，人物卡中的目标、边界、盲点和现场压力优先。
不得新增人物卡没有的身世或节目事实；不得替玩家定义感受；不得复制参考文学作品的原句或风格。
参数变化要克制：普通交流多为 -1 到 1，只有具体承诺、明显越界或事件激活才可到 2 或 3。
只有角色确实愿意让专属物件/邀约进入剧情时才提出 proposedEventId；否则返回 null。
只输出一个合法 JSON 对象，不要 Markdown，不要解释。"""
    prompt = "人物卡：\n" + json.dumps(card, ensure_ascii=False) + "\n\n当前状态：\n" + json.dumps(context, ensure_ascii=False) + "\n\n玩家输入：\n" + message[:240] + "\n\n输出合同：\n" + json.dumps(schema, ensure_ascii=False)
    raw = await _llm_text([{"role": "system", "content": system}, {"role": "user", "content": prompt}], max_tokens=760)
    return _extract_json(raw)


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
        "contentVersion": "2.0.0",
        "authMode": os.getenv("APP_AUTH_MODE", "sso"),
        "agentProvider": "deepseek" if os.getenv("DEEPSEEK_API_KEY") else "unconfigured",
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
    snapshot = migrate_snapshot(snapshot)
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
    try:
        turn = await _agent_turn(character, snapshot, message)
    except Exception as error:
        raise HTTPException(status_code=503, detail="DeepSeek 角色判断暂时没有完成，请重试这句话") from error
    with _get_db_conn() as conn:
        current = _load_run(conn, run_id, user["userId"], for_update=True)
        if current["revision"] != expected_revision:
            raise HTTPException(status_code=409, detail="关系状态已变化，这句话没有被重复写入")
        try:
            next_snapshot, receipt = commit_agent_turn(current, character_id, message, turn)
        except ValueError as error:
            raise HTTPException(status_code=502, detail=f"DeepSeek 角色输出未通过人物卡校验：{error}") from error
        reply = next_snapshot["echoMemories"][-1]["agentReply"]
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
