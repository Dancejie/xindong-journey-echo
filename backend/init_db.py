"""Idempotent PostgreSQL schema for Heart Journey."""
from __future__ import annotations

import os
import psycopg


def load_db_props(path: str = "../db.properties") -> dict[str, str]:
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


SCHEMA = """
CREATE TABLE IF NOT EXISTS app_users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS game_runs (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES app_users(id),
    content_version TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_game_runs_owner_updated ON game_runs(owner_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS game_events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES game_runs(id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_game_events_run ON game_events(run_id, id);
CREATE TABLE IF NOT EXISTS agent_memories (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES game_runs(id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    memory_id UUID NOT NULL UNIQUE,
    player_text TEXT NOT NULL,
    agent_reply TEXT NOT NULL,
    intent_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_memories_owner_character ON agent_memories(owner_id, character_id, created_at DESC);
"""


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        with psycopg.connect(database_url) as conn:
            conn.execute(SCHEMA)
            conn.commit()
        print("[init_db] DATABASE_URL schema ready")
        return
    props = load_db_props()
    if not props.get("db.host"):
        print("[init_db] db.properties 未找到或为空 — 跳过")
        return
    with psycopg.connect(
        host=props["db.host"], port=int(props["db.port"]), dbname=props["db.database"],
        user=props["db.username"], password=props["db.password"],
    ) as conn:
        conn.execute(SCHEMA)
        conn.commit()
    print("[init_db] done")


if __name__ == "__main__":
    main()
