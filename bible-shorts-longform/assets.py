"""배경 이미지·사이드 패널·썸네일 생성 모듈 (Pillow 사용)."""
import math
import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SHORT_W = 608  # 1080 높이에 맞춘 9:16 쇼츠 폭
PANEL_W = (W - SHORT_W) // 2  # 좌우 여백 656px

FONT_DIR = Path(__file__).parent / "fonts"
FONT_URLS = {
    "title": "https://raw.githubusercontent.com/google/fonts/main/ofl/blackhansans/BlackHanSans-Regular.ttf",
    "serif_bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/nanummyeongjo/NanumMyeongjo-ExtraBold.ttf",
    "serif": "https://raw.githubusercontent.com/google/fonts/main/ofl/gowunbatang/GowunBatang-Bold.ttf",
}

GOLD = (244, 208, 128)
CREAM = (255, 246, 228)


def font(kind, size):
    FONT_DIR.mkdir(exist_ok=True)
    url = FONT_URLS[kind]
    path = FONT_DIR / url.rsplit("/", 1)[1]
    if not path.exists():
        print(f"  폰트 다운로드: {path.name}")
        urllib.request.urlretrieve(url, path)
    return ImageFont.truetype(str(path), size)


# ---------------------------------------------------------------- 배경

def _gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def _glow(size, center, radius, color, alpha=255):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius * 0.6))


def _rays(size, origin, color, count=14, spread=1.3, alpha=60):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = origin
    length = size[0] * 1.2
    rnd = random.Random(7)
    for i in range(count):
        a = math.pi / 2 - spread / 2 + spread * i / (count - 1) + rnd.uniform(-0.03, 0.03)
        w = rnd.uniform(0.015, 0.04)
        p1 = (ox + length * math.cos(a - w), oy + length * math.sin(a - w))
        p2 = (ox + length * math.cos(a + w), oy + length * math.sin(a + w))
        d.polygon([origin, p1, p2], fill=color + (rnd.randint(alpha // 2, alpha),))
    return layer.filter(ImageFilter.GaussianBlur(18))


def _church(d, x, base, s, color, window=None):
    """x: 교회 중심, base: 지면 y, s: 배율."""
    bw, bh = 260 * s, 170 * s
    d.rectangle((x - bw / 2, base - bh, x + bw / 2, base), fill=color)
    d.polygon([(x - bw / 2 - 14 * s, base - bh), (x, base - bh - 110 * s), (x + bw / 2 + 14 * s, base - bh)], fill=color)
    tw, th = 70 * s, 300 * s
    tx = x - bw / 2 - tw * 0.2
    d.rectangle((tx - tw / 2, base - th, tx + tw / 2, base), fill=color)
    d.polygon([(tx - tw / 2 - 6 * s, base - th), (tx, base - th - 150 * s), (tx + tw / 2 + 6 * s, base - th)], fill=color)
    cy = base - th - 150 * s
    d.rectangle((tx - 4 * s, cy - 70 * s, tx + 4 * s, cy), fill=color)
    d.rectangle((tx - 24 * s, cy - 52 * s, tx + 24 * s, cy - 44 * s), fill=color)
    if window:
        # 스테인드글라스 창 (따뜻한 빛)
        for i, wx in enumerate((x - 70 * s, x, x + 70 * s)):
            ww, wh = 30 * s, (90 if i == 1 else 70) * s
            top = base - bh + 40 * s
            d.rectangle((wx - ww / 2, top + ww / 2, wx + ww / 2, top + wh), fill=window)
            d.ellipse((wx - ww / 2, top, wx + ww / 2, top + ww), fill=window)
        d.rectangle((x - 22 * s, base - 70 * s, x + 22 * s, base), fill=window)
        d.ellipse((x - 22 * s, base - 92 * s, x + 22 * s, base - 48 * s), fill=window)
        # 첨탑 둥근 창
        d.ellipse((tx - 16 * s, base - th + 40 * s, tx + 16 * s, base - th + 72 * s), fill=window)


def make_background(path):
    """해 질 녘 언덕 위 교회 실루엣 배경 (1920x1080)."""
    random.seed(3)
    img = _gradient(W, H, (28, 26, 58), (232, 150, 90)).convert("RGBA")
    # 별
    d = ImageDraw.Draw(img)
    for _ in range(160):
        x, y = random.randint(0, W), random.randint(0, int(H * 0.45))
        r = random.choice((1, 1, 1, 2))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 250, 230, random.randint(90, 220)))
    sun = (W * 0.5, H * 0.74)
    img = Image.alpha_composite(img, _glow((W, H), sun, 420, (255, 196, 120), 170))
    img = Image.alpha_composite(img, _rays((W, H), (sun[0], sun[1] - 300), (255, 230, 170), alpha=55))
    img = Image.alpha_composite(img, _glow((W, H), sun, 160, (255, 236, 190), 230))

    sil = (24, 16, 30, 255)
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(far)
    pts = [(0, H)] + [(x, H * 0.80 - 40 * math.sin(x / 260) - 25 * math.sin(x / 97)) for x in range(0, W + 20, 20)] + [(W, H)]
    fd.polygon(pts, fill=(70, 40, 60, 200))
    img = Image.alpha_composite(img, far.filter(ImageFilter.GaussianBlur(2)))

    near = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    nd = ImageDraw.Draw(near)
    hill = lambda x: H * 0.86 + 70 * ((x - W * 0.5) / (W * 0.5)) ** 2
    nd.polygon([(0, H)] + [(x, hill(x)) for x in range(0, W + 20, 20)] + [(W, H)], fill=sil)
    # 좌우 패널에 각각 교회 (가운데는 쇼츠가 가리므로)
    _church(nd, PANEL_W * 0.55, hill(PANEL_W * 0.55) + 6, 1.05, sil, window=(255, 196, 110, 255))
    _church(nd, W - PANEL_W * 0.45, hill(W - PANEL_W * 0.45) + 6, 0.8, sil, window=(255, 196, 110, 255))
    # 나무
    for tx, ts in ((90, 1.0), (W - 120, 1.2), (W - 40, 0.8)):
        ty = hill(tx)
        nd.rectangle((tx - 6 * ts, ty - 70 * ts, tx + 6 * ts, ty + 5), fill=sil)
        nd.ellipse((tx - 50 * ts, ty - 190 * ts, tx + 50 * ts, ty - 50 * ts), fill=sil)
    img = Image.alpha_composite(img, near)
    # 창문 불빛 번짐
    img = Image.alpha_composite(img, _glow((W, H), (PANEL_W * 0.55, hill(PANEL_W * 0.55) - 90), 90, (255, 180, 90), 70))
    img.convert("RGB").save(path, quality=95)
    return path


def load_background(bg_path):
    """사용자 배경(교회·기도하는 손 사진 등)을 1920x1080으로 꽉 차게 자른다."""
    img = Image.open(bg_path).convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


# ---------------------------------------------------------------- 텍스트

def _wrap(draw, text, fnt, max_w):
    """한글은 어절 단위로, 너무 긴 어절은 글자 단위로 줄바꿈."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = (cur + " " + word).strip()
            if draw.textlength(cand, font=fnt) <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in word:
                if draw.textlength(cur + ch, font=fnt) > max_w and cur:
                    lines.append(cur)
                    cur = ""
                cur += ch
        lines.append(cur)
    return [l for l in lines if l is not None]


def _fit(draw, text, kind, max_w, max_h, start, minimum, spacing=1.35, max_lines=None):
    size = start
    while size > minimum:
        f = font(kind, size)
        lines = _wrap(draw, text, f, max_w)
        if len(lines) * size * spacing <= max_h and (max_lines is None or len(lines) <= max_lines):
            return f, lines, size
        size -= 2
    f = font(kind, minimum)
    return f, _wrap(draw, text, f, max_w), minimum


def _text_block(draw, lines, fnt, size, cx, y, fill, spacing=1.35, shadow=True):
    for line in lines:
        w = draw.textlength(line, font=fnt)
        if shadow:
            draw.text((cx - w / 2 + 3, y + 3), line, font=fnt, fill=(0, 0, 0, 170))
        draw.text((cx - w / 2, y), line, font=fnt, fill=fill)
        y += size * spacing
    return y


def _panel_box(img, x0, x1, y0, y1):
    box = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((x0, y0, x1, y1), radius=28, fill=(12, 8, 24, 150), outline=GOLD + (140,), width=2)
    return Image.alpha_composite(img, box)


def make_frame(bg, out_path, series, index, title, reference, verse_text):
    """쇼츠가 들어갈 가운데를 비워 둔 1920x1080 프레임(배경+좌우 글씨) 생성."""
    img = bg.convert("RGBA")
    # 패널 쪽을 살짝 어둡게 해 글씨 가독성 확보
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.rectangle((0, 0, PANEL_W, H), fill=(0, 0, 0, 60))
    sd.rectangle((W - PANEL_W, 0, W, H), fill=(0, 0, 0, 60))
    img = Image.alpha_composite(img, shade)

    pad = 48
    lx0, lx1 = pad, PANEL_W - pad
    rx0, rx1 = W - PANEL_W + pad, W - pad
    box_b = 540  # 글씨 상자 아래 끝 (그 아래는 배경이 보이도록)
    img = _panel_box(img, lx0, lx1, 70, box_b)
    img = _panel_box(img, rx0, rx1, 70, box_b)
    d = ImageDraw.Draw(img)
    inner = lx1 - lx0 - 64

    # ---- 왼쪽: 시리즈명 · 번호 · 제목
    lcx = (lx0 + lx1) / 2
    f = font("serif_bold", 32)
    y = _text_block(d, [series], f, 32, lcx, 110, GOLD)
    d.line((lcx - 120, y + 8, lcx + 120, y + 8), fill=GOLD, width=2)
    f = font("title", 44)
    y = _text_block(d, [f"No. {index:02d}"], f, 44, lcx, y + 32, CREAM)
    f, lines, size = _fit(d, title, "title", inner, box_b - (y + 32) - 40, 60, 38, spacing=1.3, max_lines=4)
    _text_block(d, lines, f, size, lcx, y + 32, (255, 255, 255), spacing=1.25)

    # ---- 오른쪽: 성경 구절
    rcx = (rx0 + rx1) / 2
    f = font("serif_bold", 32)
    y = _text_block(d, ["오늘의 말씀"], f, 32, rcx, 110, GOLD)
    d.line((rcx - 120, y + 8, rcx + 120, y + 8), fill=GOLD, width=2)
    ref = reference or "말씀 묵상"
    f, lines, size = _fit(d, ref, "title", inner, 160, 64, 42, spacing=1.2, max_lines=2)
    y = _text_block(d, lines, f, size, rcx, y + 32, CREAM, spacing=1.15)
    if verse_text:
        quoted = f"“{verse_text}”"
        f, lines, size = _fit(d, quoted, "serif", inner, box_b - (y + 36) - 36, 36, 24, spacing=1.55)
        _text_block(d, lines, f, size, rcx, y + 36, (255, 255, 255), spacing=1.5)
    else:
        f = font("serif", 30)
        lines = ["말씀을 천천히 따라 읽으며", "마음에 새겨 보세요"]
        _text_block(d, lines, f, 30, rcx, y + 44, (255, 255, 255), spacing=1.6)

    # 쇼츠 자리 테두리 빛
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle((PANEL_W - 6, -10, W - PANEL_W + 6, H + 10), fill=(255, 220, 150, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img, glow)
    img.convert("RGB").save(out_path)
    return out_path


def make_intro(bg, out_path, main_title, sub_title, count):
    img = bg.convert("RGBA")
    img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 110)))
    d = ImageDraw.Draw(img)
    f = font("serif_bold", 52)
    _text_block(d, [sub_title], f, 52, W / 2, 300, GOLD)
    f, lines, size = _fit(d, main_title, "title", W - 300, 330, 150, 80, spacing=1.2, max_lines=2)
    y = _text_block(d, lines, f, size, W / 2, 400, CREAM, spacing=1.2)
    f = font("serif", 48)
    _text_block(d, [f"말씀 묵상 {count}편 연속 듣기"], f, 48, W / 2, y + 40, (255, 255, 255))
    img.convert("RGB").save(out_path)
    return out_path


def make_thumbnail(bg, out_path, big_lines, badge, small, sample_frame=None):
    """1280x720 썸네일. big_lines: 큰 글씨 줄 목록, badge: 노란 띠 문구."""
    tw, th = 1280, 720
    base = bg.resize((tw, th), Image.LANCZOS).convert("RGBA")
    base = Image.alpha_composite(base, Image.new("RGBA", (tw, th), (10, 6, 20, 30)))
    # 왼쪽에 어두운 그라데이션으로 글자 강조
    grad = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for x in range(int(tw * 0.75)):
        gd.line((x, 0, x, th), fill=(0, 0, 0, int(160 * (1 - x / (tw * 0.75)))))
    base = Image.alpha_composite(base, grad)
    if sample_frame is not None:
        fr = Image.open(sample_frame).convert("RGB")
        fr = fr.resize((int(th * 0.86 * fr.width / fr.height), int(th * 0.86)), Image.LANCZOS)
        fx, fy = tw - fr.width - 50, (th - fr.height) // 2
        g = _glow((tw, th), (fx + fr.width / 2, th / 2), fr.width * 0.8, (255, 210, 140), 180)
        base = Image.alpha_composite(base, g)
        ImageDraw.Draw(base).rectangle((fx - 6, fy - 6, fx + fr.width + 5, fy + fr.height + 5), fill=GOLD)
        base.paste(fr, (fx, fy))
    d = ImageDraw.Draw(base)
    f = font("serif_bold", 40)
    bw = d.textlength(badge, font=f) + 50
    d.rounded_rectangle((56, 60, 56 + bw, 124), radius=12, fill=(250, 204, 21))
    d.text((81, 70), badge, font=f, fill=(30, 20, 10))
    y = 160
    max_w = tw * (0.56 if sample_frame else 0.88)
    for i, line in enumerate(big_lines):
        size = 128
        while size > 60 and d.textlength(line, font=font("title", size)) > max_w:
            size -= 4
        f = font("title", size)
        color = GOLD if i == len(big_lines) - 1 else (255, 255, 255)
        for ox, oy in ((-4, 0), (4, 0), (0, -4), (0, 4), (6, 6)):
            d.text((60 + ox, y + oy), line, font=f, fill=(20, 10, 10))
        d.text((60, y), line, font=f, fill=color)
        y += size * 1.12
    f = font("serif_bold", 42)
    d.text((62, th - 100), small, font=f, fill=CREAM, stroke_width=3, stroke_fill=(20, 10, 10))
    base.convert("RGB").save(out_path, quality=95)
    return out_path
