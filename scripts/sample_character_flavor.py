#!/usr/bin/env python3
"""Call DeepSeek locally with every v3 card and produce a compact flavor report."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.agent_prompt import build_agent_messages, extract_json  # noqa: E402
from backend.game_content import (  # noqa: E402
    CHARACTER_CARDS,
    apply_choice,
    commit_agent_turn,
    create_snapshot,
    validate_agent_turn,
)


DEFAULT_INPUT = "我不想听节目里的标准答案。告诉我，你为什么还留在这里？如果现在只能做一件真事，你会做什么？"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


async def request_turn(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, card: dict, snapshot: dict, player_input: str, api_key: str, base_url: str, model: str) -> dict:
    async with semaphore:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": build_agent_messages(card, snapshot, player_input), "max_tokens": 760, "stream": False, "thinking": {"type": "disabled"}},
        )
        response.raise_for_status()
        choices = response.json().get("choices") or []
        raw = str(choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        validated = validate_agent_turn(card, extract_json(raw))
        _, receipt = commit_agent_turn(snapshot, card["id"], player_input, validated)
        committed_delta = {axis: int(receipt["patch"].get(f"relationships.{card['id']}.{axis}", 0)) for axis in card["agentPolicy"]["deltaBounds"]}
        return {
            "characterId": card["id"], "name": card["names"]["primary"], "mbti": card["mbti"],
            **validated, "relationshipDelta": committed_delta,
            "activatedEventId": (receipt.get("eventActivation") or {}).get("eventId"),
        }


def markdown_report(results: list[dict], player_input: str, model: str) -> str:
    generated = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    lines = [
        "# DeepSeek 人物对白风味样片（本地）",
        "",
        f"- 生成时间：{generated}",
        f"- 模型：`{model}`",
        "- 人物卡：`content/character_cards.v3.json`",
        f"- 同一玩家输入：{player_input}",
        "- 边界：本报告只验证角色表演、态度、记忆与受约束参数建议；未写入线上数据库。",
        "",
        "## 横向速览",
        "",
        "| 人物 | MBTI | 态度 | 意图 | 事件提议 / 实际激活 |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        proposed = "是" if item.get("proposedEventId") else "否"
        activated = "是" if item.get("activatedEventId") else "否"
        lines.append(f"| {item['name']} | {item['mbti']} | {item['attitude']} | {item['intentId']} | {proposed} / {activated} |")
    for item in results:
        delta = "、".join(f"{key} {value:+d}" for key, value in item["relationshipDelta"].items() if value) or "无"
        lines.extend([
            "",
            f"## {item['name']} · {item['mbti']}",
            "",
            f"> {item['stageDirection']} {item['dialogue']}",
            "",
            f"- 公开判断：{item['publicReason']}",
            f"- 参数建议：{delta}",
            f"- 写入候选记忆：{item['memory']['summary']}（角色解释：{item['memory']['interpretation']}）",
            f"- 事件建议 / 实际激活：{item.get('proposedEventId') or '无'} / {item.get('activatedEventId') or '无'}",
        ])
    lines.extend([
        "",
        "## 人工验收重点",
        "",
        "- 八个人是否能在不显示 MBTI 术语的情况下被区分。",
        "- 台词是否至少推进一个事实、动作、问题、反价或边界。",
        "- 零信任是否避免直接倾倒隐藏身世。",
        "- 参数是否克制，事件是否只在角色确实交出物件或邀约时提出。",
        "- 文学锚点是否只留下决策结构，没有出现原句复刻。",
        "",
    ])
    return "\n".join(lines)


async def run(args: argparse.Namespace) -> int:
    env = {**load_env(Path(args.env_file)), **os.environ}
    api_key = env.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY 未配置")
    base_url = env.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    model = env.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    snapshot = create_snapshot(args.player_mbti)
    snapshot, _ = apply_choice(snapshot, "arrive-ask-rule")
    snapshot, _ = apply_choice(snapshot, "first-person")
    cards = [card for card in CHARACTER_CARDS if not args.character or card["id"] in args.character]
    semaphore = asyncio.Semaphore(max(1, min(args.concurrency, 2)))
    async with httpx.AsyncClient(timeout=90) as client:
        jobs = [request_turn(client, semaphore, card, snapshot, args.player_input, api_key, base_url, model) for card in cards]
        results = await asyncio.gather(*jobs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown_report(results, args.player_input, model), encoding="utf-8")
    json_output = output.with_suffix(".json")
    json_output.write_text(json.dumps({"model": model, "playerInput": args.player_input, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(results)} validated turns -> {output}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(ROOT / ".env.deepseek.local"))
    parser.add_argument("--output", default=str(ROOT / "qa" / "DEEPSEEK-CHARACTER-FLAVOR.md"))
    parser.add_argument("--player-input", default=DEFAULT_INPUT)
    parser.add_argument("--player-mbti", default="INFP")
    parser.add_argument("--character", action="append")
    parser.add_argument("--concurrency", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parse_args())))
