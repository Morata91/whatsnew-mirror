#!/usr/bin/env python3
"""AWS What's New / AWS News Blog の RSS を取得して data/latest.json に保存する。標準ライブラリのみ使用。"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

FEEDS = {
    "whats_new": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
    "aws_blog": "https://aws.amazon.com/jp/blogs/news/feed/",
}
OUT = Path("data/latest.json")
MAX_ITEMS = 50


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "aws-feed-archiver/1.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read()


def to_iso(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return value


def parse(xml_bytes: bytes) -> list:
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        items.append(
            {
                "title": (it.findtext("title") or "").strip(),
                "link": (it.findtext("link") or "").strip(),
                "published": to_iso(it.findtext("pubDate")),
                "summary": (it.findtext("description") or "").strip(),
                "categories": [c.text.strip() for c in it.findall("category") if c.text],
            }
        )
    return items[:MAX_ITEMS]


def main() -> None:
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
    old_feeds = old.get("feeds", {})

    feeds = {}
    for name, url in FEEDS.items():
        try:
            feeds[name] = {"source": url, "items": parse(fetch(url))}
        except Exception as e:  # 失敗時は前回分を維持
            print(f"WARN: {name} の取得に失敗: {e}")
            if name in old_feeds:
                feeds[name] = old_feeds[name]

    if feeds == old_feeds:
        print("変更なし")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {"generated_at": datetime.now(timezone.utc).isoformat(), "feeds": feeds}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"保存: {OUT}")


if __name__ == "__main__":
    main()
