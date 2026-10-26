#!/usr/bin/env python3
"""나노바나나(Gemini 이미지 모델)로 롱폼 배경·썸네일 배경을 생성.

사용법: GEMINI_API_KEY=... python nanobanana.py [이름 ...]
결과:   backgrounds/<이름>.png
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

MODEL = os.environ.get("NANOBANANA_MODEL", "gemini-3-pro-image")
OUT = Path(__file__).parent / "backgrounds"

COMMON = (
    "Photorealistic, cinematic, 16:9 widescreen, soft warm golden light, gentle film grain, "
    "peaceful and reverent mood, high detail. No text, no letters, no logos, no watermark, no people's faces. "
    "IMPORTANT composition: the central third of the frame will be covered by a vertical video, so place the "
    "main subjects in the LEFT third and RIGHT third, and keep the center calm, softly lit and uncluttered. "
    "Leave darker, low-detail areas in the upper part of the left and right thirds for large overlaid text."
)

PROMPTS = {
    "church": "Interior of an old stone church at dawn. Tall arched stained-glass windows on the left and right "
              "sides cast warm god rays across wooden pews; a simple wooden cross glows softly far in the center "
              "background, out of focus. Floating dust in the light beams.",
    "hands": "Two pairs of praying hands: an elderly person's hands folded in prayer resting on an open old Bible "
             "on the left side, and a young person's hands clasped in prayer resting beside a small wooden cross "
             "on the right side, both on a rustic wooden table near a window with warm morning sunlight, "
             "shallow depth of field, soft bokeh in the center.",
    "chapel": "A small white chapel on a green hill at golden-hour sunset, seen from a distance on the right side; "
              "on the left side a silhouette of an old olive tree; wide sky with soft glowing clouds and sun rays "
              "breaking through in the center, serene countryside.",
}


def generate(name, prompt, key):
    body = {
        "contents": [{"parts": [{"text": prompt + " " + COMMON}]}],
        "generationConfig": {"responseModalities": ["IMAGE"],
                             "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    for part in res["candidates"][0]["content"]["parts"]:
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            OUT.mkdir(exist_ok=True)
            path = OUT / f"{name}.png"
            path.write_bytes(base64.b64decode(data["data"]))
            print(f"✓ {path}")
            return path
    raise RuntimeError(f"{name}: 이미지가 반환되지 않았습니다 → {json.dumps(res)[:300]}")


def main():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY 환경 변수를 설정하세요.")
    for name in sys.argv[1:] or PROMPTS:
        generate(name, PROMPTS[name], key)


if __name__ == "__main__":
    main()
