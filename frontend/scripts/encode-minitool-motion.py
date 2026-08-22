#!/usr/bin/env python3
"""Encode retained MP4 masters as Mini Tool-safe animated WebP projections."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image, features

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "minitool-src" / "motion-requirements.json"

def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

def encode(source: Path, target: Path, width: int, height: int, fps: int, quality: int) -> int:
    frame_size = width * height * 3
    command = ["ffmpeg", "-v", "error", "-i", str(source), "-vf", f"fps={fps},scale={width}:{height}:flags=lanczos", "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    assert process.stdout is not None
    frames: list[Image.Image] = []
    while True:
        raw = process.stdout.read(frame_size)
        if not raw:
            break
        if len(raw) != frame_size:
            process.kill()
            raise RuntimeError(f"truncated frame: {source.name}")
        frames.append(Image.frombytes("RGB", (width, height), raw))
    if process.wait() != 0 or not frames:
        raise RuntimeError(f"decode failed: {source.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(target, format="WEBP", save_all=True, append_images=frames[1:], duration=round(1000/fps), loop=0, quality=quality, method=4, minimize_size=True, allow_mixed=True)
    return len(frames)

def main() -> int:
    if not features.check("webp") or not features.check("webp_anim"):
        raise SystemExit("Pillow animated WebP support is required")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source_dir = (CONFIG_PATH.parent / config["sourceDirectory"]).resolve()
    output_dir = (CONFIG_PATH.parent / config["outputDirectory"]).resolve()
    records = []
    for item in config["items"]:
        source, target = source_dir / item["source"], output_dir / item["target"]
        if not source.is_file():
            raise SystemExit(f"missing source: {source}")
        frames = encode(source, target, item["width"], item["height"], item["fps"], item["quality"])
        record = {**item, "frames": frames, "bytes": target.stat().st_size, "sha256": digest(target), "sourceSha256": digest(source)}
        records.append(record)
        print(f"{target.name}: {frames} frames, {record['bytes']:,} bytes")
    (output_dir / "animated-webp-manifest.json").write_text(json.dumps({"format":"animated-webp","audio":False,"items":records}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
