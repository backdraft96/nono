#!/usr/bin/env python3
"""성경 말씀 묵상 쇼츠 → 유튜브 롱폼(1920x1080) 자동 제작.

1단계  python make_longform.py plan  [--channel URL] [--limit N]
       채널 쇼츠 목록을 받아 말씀·묵상 쇼츠만 골라 clips.json 작성
       (제목·성경 구절·본문을 자동 추출 → 필요하면 직접 수정)
2단계  python make_longform.py build [--bg 배경.jpg]
       쇼츠 다운로드 → 가운데 쇼츠 + 좌우 배경·큰 글씨 합성 → 하나로 이어 붙임
       → output/ 에 영상·썸네일·유튜브 제목/설명/고정댓글/챕터 생성
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import assets

ROOT = Path(__file__).parent
WORK = ROOT / "work"
OUT = ROOT / "output"
CLIPS = ROOT / "clips.json"
SETTINGS = ROOT / "settings.json"

DEFAULT_SETTINGS = {
    "channel": "https://www.youtube.com/@bible_every",
    "series": "매일 말씀 묵상",
    "main_title": "하루를 여는 말씀 묵상",
    "sub_title": "성경 말씀 읽기와 묵상",
    "keywords": ["말씀", "묵상", "성경", "구절", "절", "장", "기도", "주님", "하나님", "예수"],
    "exclude": ["광고", "공지", "라이브"],
}

BOOKS = [
    "창세기", "출애굽기", "레위기", "민수기", "신명기", "여호수아", "사사기", "룻기", "사무엘상", "사무엘하",
    "열왕기상", "열왕기하", "역대상", "역대하", "에스라", "느헤미야", "에스더", "욥기", "시편", "잠언",
    "전도서", "아가", "이사야", "예레미야애가", "예레미야", "에스겔", "다니엘", "호세아", "요엘", "아모스",
    "오바댜", "요나", "미가", "나훔", "하박국", "스바냐", "학개", "스가랴", "말라기",
    "마태복음", "마가복음", "누가복음", "요한복음", "사도행전", "로마서", "고린도전서", "고린도후서",
    "갈라디아서", "에베소서", "빌립보서", "골로새서", "데살로니가전서", "데살로니가후서", "디모데전서",
    "디모데후서", "디도서", "빌레몬서", "히브리서", "야고보서", "베드로전서", "베드로후서",
    "요한일서", "요한이서", "요한삼서", "유다서", "요한계시록",
]
ABBR = {
    "창": "창세기", "출": "출애굽기", "레": "레위기", "민": "민수기", "신": "신명기", "수": "여호수아",
    "삿": "사사기", "삼상": "사무엘상", "삼하": "사무엘하", "왕상": "열왕기상", "왕하": "열왕기하",
    "대상": "역대상", "대하": "역대하", "스": "에스라", "느": "느헤미야", "에": "에스더", "욥": "욥기",
    "시": "시편", "잠": "잠언", "전": "전도서", "사": "이사야", "렘": "예레미야", "애": "예레미야애가",
    "겔": "에스겔", "단": "다니엘", "호": "호세아", "욜": "요엘", "암": "아모스", "옵": "오바댜", "욘": "요나",
    "미": "미가", "나": "나훔", "합": "하박국", "습": "스바냐", "학": "학개", "슥": "스가랴", "말": "말라기",
    "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음", "행": "사도행전", "롬": "로마서",
    "고전": "고린도전서", "고후": "고린도후서", "갈": "갈라디아서", "엡": "에베소서", "빌": "빌립보서",
    "골": "골로새서", "살전": "데살로니가전서", "살후": "데살로니가후서", "딤전": "디모데전서",
    "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서", "히": "히브리서", "약": "야고보서",
    "벧전": "베드로전서", "벧후": "베드로후서", "요일": "요한일서", "요이": "요한이서", "요삼": "요한삼서",
    "유": "유다서", "계": "요한계시록",
}
_names = sorted(BOOKS, key=len, reverse=True) + sorted(ABBR, key=len, reverse=True)
_NUM = r"(\d{1,3})\s*(?:장|:|：)\s*(\d{1,3})(?:\s*절)?(?:\s*[-~]\s*(\d{1,3})(?:\s*절)?)?"
REF_RE = re.compile(r"(?<![가-힣])(" + "|".join(_names) + r")\s*" + _NUM)


def find_reference(text):
    m = REF_RE.search(text or "")
    if not m:
        return ""
    book = ABBR.get(m.group(1), m.group(1))
    ref = f"{book} {m.group(2)}:{m.group(3)}"
    return ref + (f"-{m.group(4)}" if m.group(4) else "")


def find_verse_text(desc, ref):
    """설명란에서 본문으로 보이는 첫 문장을 찾는다 (따옴표 우선)."""
    if not desc:
        return ""
    q = re.search(r"[\"“「『]([^\"”」』]{10,200})[\"”」』]", desc)
    if q:
        return q.group(1).strip()
    for line in desc.splitlines():
        s = line.strip()
        if len(s) < 12 or s.startswith(("#", "http", "@")) or "구독" in s or "좋아요" in s:
            continue
        s = REF_RE.sub("", s).strip(" -–—:()[]")
        if len(s) >= 12:
            return s[:200]
    return ""


def clean_title(title):
    t = re.sub(r"#\S+", "", title or "")
    t = re.sub(r"\s{2,}", " ", t).strip(" |-")
    return t


def run(cmd):
    print("  $", " ".join(str(c) for c in cmd)[:160])
    subprocess.run(cmd, check=True)


def load_settings():
    if not SETTINGS.exists():
        SETTINGS.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**DEFAULT_SETTINGS, **json.loads(SETTINGS.read_text(encoding="utf-8"))}


# ---------------------------------------------------------------- plan

def plan(args):
    import yt_dlp

    st = load_settings()
    channel = (args.channel or st["channel"]).rstrip("/")
    print(f"쇼츠 목록 가져오는 중: {channel}/shorts")
    with yt_dlp.YoutubeDL({"extract_flat": True, "quiet": True}) as ydl:
        listing = ydl.extract_info(channel + "/shorts", download=False)
    entries = [e for e in listing.get("entries", []) if e.get("id")]
    print(f"  쇼츠 {len(entries)}개 발견 → 상세 정보 확인")

    clips = []
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        for e in entries:
            if args.limit and len(clips) >= args.limit:
                break
            url = f"https://www.youtube.com/shorts/{e['id']}"
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as err:  # 비공개·삭제 영상 등
                print(f"  건너뜀 {e['id']}: {err}")
                continue
            title, desc = info.get("title", ""), info.get("description", "")
            blob = title + "\n" + desc
            ref = find_reference(blob)
            if any(x in blob for x in st["exclude"]):
                continue
            if not ref and not any(k in blob for k in st["keywords"]):
                continue
            clips.append({
                "use": True,
                "id": e["id"],
                "url": url,
                "upload_date": info.get("upload_date", ""),
                "duration": info.get("duration"),
                "title": clean_title(title),
                "reference": ref,
                "verse_text": find_verse_text(desc, ref),
            })
            print(f"  ✓ {ref or '(구절 미확인)':<16} {clean_title(title)}")

    order = args.order or "oldest"
    clips.sort(key=lambda c: c["upload_date"], reverse=(order == "newest"))
    CLIPS.write_text(json.dumps(clips, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(clips)}개 선정 → {CLIPS.name} 저장")
    print("제목·구절(reference)·본문(verse_text)을 확인/수정하고, 뺄 영상은 \"use\": false 로 바꾼 뒤 build 를 실행하세요.")


# ---------------------------------------------------------------- build

def fmt_time(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def has_audio(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return bool(out.stdout.strip())


def download(clip):
    dst = WORK / "src" / f"{clip['id']}.mp4"
    if clip.get("file"):
        return Path(clip["file"])
    if dst.exists():
        return dst
    import yt_dlp
    dst.parent.mkdir(parents=True, exist_ok=True)
    opts = {"format": "bv*[height<=1920][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
            "merge_output_format": "mp4", "outtmpl": str(dst), "quiet": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([clip["url"]])
    return dst


ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def render_segment(frame_png, src, out, fade=0.5):
    dur = probe_duration(src)
    sw, sh = assets.SHORT_W, assets.H
    vf = (f"[1:v]scale={sw}:{sh}:force_original_aspect_ratio=decrease,setsar=1[s];"
          f"[0:v][s]overlay=(W-w)/2:(H-h)/2:shortest=1,"
          f"fade=t=in:st=0:d={fade},fade=t=out:st={max(dur - fade, 0):.3f}:d={fade}[v]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(frame_png), "-i", str(src)]
    if has_audio(src):
        af = f"[1:a]afade=t=in:st=0:d={fade},afade=t=out:st={max(dur - fade, 0):.3f}:d={fade}[a]"
        cmd += ["-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex", vf, "-map", "[v]", "-map", "2:a"]
    run(cmd + ["-t", f"{dur:.3f}"] + ENC + [str(out)])
    return probe_duration(out)


def render_still(png, out, seconds):
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", "fade=t=in:st=0:d=0.8,fade=t=out:st="
         f"{seconds - 0.8}:d=0.8", "-t", str(seconds)] + ENC + [str(out)])
    return seconds


def build(args):
    if not CLIPS.exists():
        sys.exit("clips.json 이 없습니다. 먼저 plan 을 실행하세요.")
    st = load_settings()
    clips = [c for c in json.loads(CLIPS.read_text(encoding="utf-8")) if c.get("use", True)]
    if not clips:
        sys.exit("사용할 클립이 없습니다.")
    for d in (WORK / "frames", WORK / "seg", OUT):
        d.mkdir(parents=True, exist_ok=True)

    if args.bg:
        bg = assets.load_background(args.bg)
    else:
        bg_path = WORK / "background.jpg"
        assets.make_background(bg_path)
        bg = assets.load_background(bg_path)
    bg.save(OUT / "background_used.jpg", quality=92)

    segments, chapters, t = [], [], 0.0
    intro_png = assets.make_intro(bg, WORK / "frames" / "intro.png", st["main_title"], st["sub_title"], len(clips))
    if args.intro > 0:
        segments.append(WORK / "seg" / "000_intro.mp4")
        t += render_still(intro_png, segments[-1], args.intro)
        chapters.append(("00:00", "오프닝"))

    for i, c in enumerate(clips, 1):
        print(f"[{i}/{len(clips)}] {c['reference'] or ''} {c['title']}")
        src = download(c)
        png = assets.make_frame(bg, WORK / "frames" / f"{i:03d}.png", st["series"], i,
                                c["title"], c.get("reference", ""), c.get("verse_text", ""))
        seg = WORK / "seg" / f"{i:03d}.mp4"
        label = f"{c['reference']} · {c['title']}" if c.get("reference") else c["title"]
        chapters.append((fmt_time(t), label))
        t += render_segment(png, src, seg)
        segments.append(seg)

    listfile = WORK / "concat.txt"
    listfile.write_text("".join(f"file '{s.resolve()}'\n" for s in segments), encoding="utf-8")
    final = OUT / "longform.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c", "copy", "-movflags", "+faststart", str(final)])
    print(f"\n영상 완성: {final}  (총 {fmt_time(probe_duration(final))})")

    # 썸네일: 첫 번째 프레임 PNG에서 쇼츠 자리를 잘라 오른쪽에 배치
    sample = WORK / "thumb_sample.jpg"
    first_seg = segments[1] if args.intro > 0 else segments[0]
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(first_seg), "-frames:v", "1",
         "-vf", f"crop={assets.SHORT_W}:{assets.H}:{assets.PANEL_W}:0", str(sample)])
    assets.make_thumbnail(bg, OUT / "thumbnail.jpg", ["하루를 여는", "말씀 묵상"],
                          f"{len(clips)}편 연속 듣기", "잠들기 전 · 출근길 · 기도 시간에", sample)
    assets.make_thumbnail(bg, OUT / "thumbnail_text_only.jpg", ["지친 마음에", "주시는 말씀"],
                          f"말씀 묵상 {len(clips)}편 모음", "성경 구절 읽기 + 짧은 묵상")

    write_youtube_texts(st, clips, chapters, t)


def write_youtube_texts(st, clips, chapters, total):
    refs = [c["reference"] for c in clips if c.get("reference")]
    ref_line = ", ".join(refs[:6]) + (" 외" if len(refs) > 6 else "")
    titles = [
        f"[말씀 묵상 모음] {st['main_title']} | 성경 구절 {len(clips)}편 연속 듣기",
        f"잠들기 전 듣는 성경 말씀 {len(clips)}편 | 짧은 묵상 모음 ({fmt_time(total)})",
        f"마음이 지칠 때 듣는 하나님의 말씀 | 성경 구절 묵상 {len(clips)}편",
    ]
    chap = "\n".join(f"{ts} {label}" for ts, label in chapters)
    desc = f"""{st['main_title']} — 매일 한 구절씩 나누던 말씀 묵상 쇼츠 {len(clips)}편을 한 번에 이어 들을 수 있도록 모았습니다.
출근길, 잠들기 전, 기도 시간에 틀어 두고 말씀 앞에 머물러 보세요.

📖 이번 영상의 말씀
{ref_line}

⏱ 챕터
{chap}

🙏 이렇게 들어 보세요
1. 구절을 천천히 따라 읽어 보세요.
2. 오늘 내 마음에 닿은 한 단어를 붙잡아 보세요.
3. 그 말씀으로 짧게 기도하며 하루를 시작(마무리)해 보세요.

💬 오늘 마음에 남은 구절을 댓글로 나눠 주세요. 함께 기도하겠습니다.
🔔 구독과 알림 설정을 하시면 매일 새로운 말씀 묵상을 받아 보실 수 있습니다.

※ 본 영상은 채널에 게시된 말씀 묵상 쇼츠를 모아 재편집한 영상입니다.

#성경말씀 #말씀묵상 #성경구절 #오늘의말씀 #기독교 #큐티 #QT #기도 #하나님말씀 #잠들기전말씀
"""
    pin = f"""🙏 오늘도 말씀 앞에 머물러 주셔서 감사합니다.

📌 {len(clips)}편의 말씀 가운데 오늘 가장 마음에 닿은 구절은 무엇인가요?
댓글로 구절과 짧은 기도 제목을 남겨 주시면 함께 기도하겠습니다.

▶ 바로 듣기
{chap}

🔔 매일 새로운 말씀 묵상 쇼츠가 올라옵니다. 구독·알림 설정으로 함께해 주세요!"""
    text = "■ 유튜브 제목 (후보)\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(titles, 1))
    text += "\n\n■ 설명\n" + desc + "\n■ 고정 댓글\n" + pin + "\n\n■ 태그\n"
    text += "성경말씀, 말씀묵상, 성경구절, 오늘의말씀, 성경읽기, 큐티, QT, 기도, 잠들기전말씀, 하나님말씀, 묵상, 기독교, 찬양, 은혜, " + ", ".join(refs[:10]) + "\n"
    (OUT / "youtube_texts.txt").write_text(text, encoding="utf-8")
    print(f"유튜브 제목·설명·고정댓글: {OUT / 'youtube_texts.txt'}")


# ---------------------------------------------------------------- main

def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg 이 필요합니다. https://ffmpeg.org 에서 설치하세요.")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("plan", help="쇼츠 목록 수집 → clips.json")
    a.add_argument("--channel")
    a.add_argument("--limit", type=int, default=0, help="최대 클립 수 (0=전체)")
    a.add_argument("--order", choices=["oldest", "newest"])
    b = sub.add_parser("build", help="clips.json → 롱폼 영상 제작")
    b.add_argument("--bg", help="배경 이미지(교회·기도하는 손 사진). 없으면 교회 실루엣 배경 자동 생성")
    b.add_argument("--intro", type=float, default=5, help="오프닝 타이틀 길이(초), 0이면 생략")
    args = p.parse_args()
    {"plan": plan, "build": build}[args.cmd](args)


if __name__ == "__main__":
    main()
