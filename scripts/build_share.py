#!/usr/bin/env python3
"""RELEASE 뷰어를 외부 공유용(GitHub Pages) 정적 사이트로 빌드한다.

RELEASE/{pkg}/index.html 은 조립 산출물이라 그대로 두고, 공유본만 따로 만든다.
  · 패널 PNG → JPEG 압축본 (호스팅 대역폭 + 모바일 로딩)
  · PANELS 배열의 .png 참조를 .jpg 로 치환
  · 카카오톡·슬랙 링크 미리보기용 og:image 표지 생성
  · 작품 소개(프롤로그) + 피드백 요청(에필로그) 블록 주입
  · noindex — 링크를 아는 사람만. 검색 노출은 막는다.

사용:
    python3 scripts/build_share.py            # 기본값(요셉 EP01)으로 빌드
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

# ── 빌드 대상 ────────────────────────────────────────────────────────────────
SRC_PKG = ROOT / "RELEASE" / "joseph_ep01"
OUT_DIR = ROOT / "docs" / "ep01"
SITE_BASE = "https://rainbow85213.github.io/webtoon-harness/ep01/"

MAX_EDGE = 1100          # 패널 최대 변 — 모바일 2x 판독에 충분
JPEG_Q = 82

COVER_PANEL = "panel_001.png"     # 표지로 쓸 패널
COVER_CROP_TOP = 0.352            # 위에서부터 이 비율만큼을 잘라 씀 (구덩이 입구 + 형들 실루엣)

MYUNGJO = "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"
GOTHIC = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

META = {
    "title": "꿈 꾸는 자",
    "episode": "제1화 「채색옷」",
    "eyebrow": "창세기 37장 · 성경 웹툰",
    "logline": (
        "아버지가 지어 준 채색옷과 두 번의 꿈 자랑이 형들의 증오를 채우고, "
        "맏형이 자리를 비운 사이 요셉은 물 없는 구덩이에서 은 스무 냥에 팔린다 "
        "— 그리고 그를 구하려 놓아둔 밧줄만이 손대지 않은 채 남는다."
    ),
    "source": "창세기 37장 1~32절",
    "length": "52칸 · 약 5분",
    "audience": "청소년·청년부",
}


# ── 1. 패널 압축 ─────────────────────────────────────────────────────────────
def build_panels() -> int:
    src = SRC_PKG / "panels"
    dst = OUT_DIR / "panels"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(src.glob("panel_*.png")):
        out = dst / (f.stem + ".jpg")
        subprocess.run(
            ["sips", "--resampleHeightWidthMax", str(MAX_EDGE),
             "-s", "format", "jpeg", "-s", "formatOptions", str(JPEG_Q),
             str(f), "--out", str(out)],
            check=True, capture_output=True,
        )
        n += 1
    return n


# ── 2. 링크 미리보기 표지 ────────────────────────────────────────────────────
def build_cover() -> Path:
    """og:image 규격(1200x630) 표지. 패널 상단을 잘라 쓰고 제목을 얹는다."""
    W, H = 1200, 630
    base = Image.open(SRC_PKG / "panels" / COVER_PANEL).convert("RGB")
    crop_h = int(base.height * COVER_CROP_TOP)
    # 가로를 꽉 채우되 1200:630 비율이 되도록 높이를 맞춘다
    need_h = int(base.width * H / W)
    crop_h = min(max(crop_h, need_h), base.height)
    top = 0
    box_h = need_h
    img = base.crop((0, top, base.width, top + box_h)).resize((W, H), Image.LANCZOS)

    # 하단 그라데이션 — 제목이 앉을 자리를 어둡게
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        t = max(0.0, (y - H * 0.34) / (H * 0.66))
        grad.putpixel((0, y), int(238 * (t ** 1.35)))
    shade = Image.new("RGB", (W, H), (18, 16, 13))
    img = Image.composite(shade, img, grad.resize((W, H)))

    d = ImageDraw.Draw(img)
    f_eyebrow = ImageFont.truetype(GOTHIC, 27)
    f_title = ImageFont.truetype(MYUNGJO, 96)
    f_ep = ImageFont.truetype(MYUNGJO, 40)

    x, ivory, dim = 72, (239, 231, 210), (198, 186, 160)
    d.text((x, H - 250), META["eyebrow"], font=f_eyebrow, fill=dim)
    d.text((x, H - 205), META["title"], font=f_title, fill=ivory)
    d.text((x, H - 84), META["episode"], font=f_ep, fill=dim)
    # 좌측 강조 괘선
    d.rectangle([x - 22, H - 246, x - 17, H - 40], fill=(178, 122, 58))

    out = OUT_DIR / "cover.jpg"
    img.save(out, "JPEG", quality=88, optimize=True)
    return out


# ── 3. HTML 주입 ─────────────────────────────────────────────────────────────
HEAD_INJECT = f"""<meta name="robots" content="noindex, nofollow" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{META['title']} — {META['episode']}" />
<meta property="og:description" content="{META['eyebrow']} · {META['length']}. 위에서 아래로 넘기며 읽습니다." />
<meta property="og:image" content="{SITE_BASE}cover.jpg" />
<meta property="og:url" content="{SITE_BASE}" />
<meta name="twitter:card" content="summary_large_image" />
"""

EXTRA_CSS = """
/* ===== 공유본 전용 — 프롤로그 / 에필로그 ===== */
.sh-wrap { max-width: 720px; margin: 0 auto; padding: 0 20px; }
.sh-card {
  background: var(--strip-bg); color: var(--ink);
  border-radius: 3px; padding: 40px 34px 34px;
  box-shadow: 0 18px 44px rgba(0,0,0,.34);
}
.prologue { padding: 46px 0 34px; }
.epilogue { padding: 34px 0 72px; }

.sh-eyebrow { margin: 0 0 14px; font-size: 12.5px; letter-spacing: .16em;
              color: #8A7A5E; font-weight: 700; }
.sh-title { margin: 0; font-family: var(--font-serif); font-size: 46px;
            line-height: 1.12; letter-spacing: .02em; font-weight: 400; }
.sh-ep { margin: 8px 0 0; font-family: var(--font-serif); font-size: 20px; color: #6B5F4A; }
.sh-rule { border: 0; border-top: 1px solid rgba(34,32,28,.16); margin: 24px 0 22px; }
.sh-log { margin: 0; font-size: 15.5px; line-height: 1.78; color: #3A3428;
          word-break: keep-all; }

.sh-facts { list-style: none; margin: 24px 0 0; padding: 0;
            display: grid; gap: 9px; }
.sh-facts li { display: flex; gap: 14px; font-size: 14px; color: #4A4234; align-items: baseline; }
.sh-facts li b { flex: none; width: 54px; font-size: 11.5px; font-weight: 700;
                 letter-spacing: .1em; color: #8A7A5E; }

.sh-how { margin: 26px 0 0; padding: 15px 17px; background: rgba(34,32,28,.055);
          border-left: 3px solid #B27A3A; font-size: 13.5px; line-height: 1.72;
          color: #4A4234; word-break: keep-all; }
.sh-down { margin: 30px 0 0; text-align: center; font-size: 22px; color: #A8987A;
           animation: shBob 1.9s ease-in-out infinite; }
@keyframes shBob { 0%,100% { transform: translateY(0); opacity:.55 }
                   50% { transform: translateY(6px); opacity:1 } }
@media (prefers-reduced-motion: reduce) { .sh-down { animation: none } }

.sh-h2 { margin: 0 0 6px; font-family: var(--font-serif); font-size: 26px; font-weight: 400; }
.sh-sub { margin: 0 0 24px; font-size: 13.5px; color: #6B5F4A; line-height: 1.7;
          word-break: keep-all; }
.sh-ask { margin: 0; padding: 0; list-style: none; display: grid; gap: 16px;
          counter-reset: shq; }
.sh-ask li { position: relative; padding-left: 40px; font-size: 14.5px;
             line-height: 1.72; color: #3A3428; word-break: keep-all; counter-increment: shq; }
.sh-ask li::before {
  content: counter(shq); position: absolute; left: 0; top: 1px;
  width: 26px; height: 26px; border-radius: 50%;
  background: #22201C; color: #E5DFD0;
  font-size: 12.5px; font-weight: 700; display: grid; place-items: center;
}
.sh-ask li b { display: block; margin-bottom: 3px; font-size: 15px; }
.sh-tip { margin: 26px 0 0; padding: 15px 17px; background: rgba(34,32,28,.055);
          border-left: 3px solid #22201C; font-size: 13.5px; line-height: 1.72;
          color: #4A4234; word-break: keep-all; }

.sh-det { margin: 22px 0 0; border-top: 1px solid rgba(34,32,28,.16); padding-top: 20px; }
.sh-det > summary { cursor: pointer; font-size: 14px; font-weight: 700; color: #4A4234;
                    list-style: none; display: flex; gap: 9px; align-items: center; }
.sh-det > summary::-webkit-details-marker { display: none; }
.sh-det > summary::before { content: "▸"; color: #B27A3A; transition: transform .18s; }
.sh-det[open] > summary::before { transform: rotate(90deg); }
.sh-det .sh-body { margin-top: 16px; font-size: 13.5px; line-height: 1.78;
                   color: #4A4234; word-break: keep-all; }
.sh-det .sh-body p { margin: 0 0 13px; }
.sh-det .sh-body b { color: #22201C; }

@media (max-width: 560px) {
  .sh-card { padding: 32px 22px 28px; }
  .sh-title { font-size: 38px; }
  .prologue { padding: 30px 0 24px; }
}
"""

PROLOGUE = f"""
<section class="prologue"><div class="sh-wrap"><div class="sh-card">
  <p class="sh-eyebrow">{META['eyebrow']}</p>
  <h1 class="sh-title">{META['title']}</h1>
  <p class="sh-ep">{META['episode']}</p>
  <hr class="sh-rule" />
  <p class="sh-log">{META['logline']}</p>
  <ul class="sh-facts">
    <li><b>본문</b>{META['source']}</li>
    <li><b>분량</b>{META['length']}</li>
    <li><b>대상</b>{META['audience']}</li>
  </ul>
  <p class="sh-how">위에서 아래로 넘기며 읽습니다. 인물이 하는 말 중
    <b>성경에 있는 문장 35개는 개역개정에서 한 글자도 고치지 않고</b> 그대로 옮겼고,
    「이것은 하나님의 뜻이었다」 같은 해설 자막은 한 줄도 넣지 않았습니다.</p>
  <p class="sh-down" aria-hidden="true">↓</p>
</div></div></section>
"""

EPILOGUE = """
<section class="epilogue"><div class="sh-wrap"><div class="sh-card">
  <h2 class="sh-h2">보고 나서, 이런 점을 알려 주세요</h2>
  <p class="sh-sub">아직 시험판입니다. 좋았다는 말보다 걸렸던 지점이 훨씬 도움이 됩니다.</p>
  <ol class="sh-ask">
    <li><b>이야기가 이해되나요?</b>성경을 잘 모르는 사람이 봐도 지금 무슨 일이 벌어지는지 따라갈 수 있는지 알려 주세요.</li>
    <li><b>그림과 글이 따로 놀지 않나요?</b>말풍선 위치, 글자 크기, 읽는 순서가 자연스러운지 봐 주세요.</li>
    <li><b>속도감이 있나요?</b>지루하게 늘어지는 구간, 반대로 너무 훅 지나가 버리는 구간이 있는지가 특히 궁금합니다.</li>
    <li><b>성경과 어긋나 보이는 곳이 있나요?</b>알고 계신 내용과 다르게 그려진 부분이 있다면 꼭 짚어 주세요.</li>
  </ol>
  <p class="sh-tip">알려 주실 때 <b>맨 위에서부터 몇 번째 칸인지</b> 함께 적어 주시면
    그 칸만 다시 그릴 수 있어 훨씬 빠르게 고쳐집니다.</p>

  <details class="sh-det"><summary>만든 쪽에서 미리 밝히는 점 — 성경과 다르게 그려진 두 곳</summary>
  <div class="sh-body">
    <p>둘 다 요셉이 꾼 <b>꿈 장면</b>이고, 둘 다 「개수」 문제입니다.
      그림을 그리는 데 쓴 도구가 「정확히 열한 개를 그려라」 같은 개수 지시를 안정적으로 따르지 못합니다.
      일곱 차례 다시 그렸지만 끝내 정확한 개수에 이르지 못했고, 도구의 한계로 확인해 현재 상태로 확정했습니다.</p>
    <p><b>15번째 칸 — 곡식 단(창세기 37장 7절).</b>
      단의 개수가 세는 방법에 따라 여덟에서 열셋 사이로 달라집니다. 서로 겹치고 화면 아래에서 잘리기 때문입니다.
      다만 「하나가 서고 나머지가 둘러서서 절한다」는 장면의 뜻은 그대로 읽히고,
      이 칸의 대사는 개수를 말하지 않습니다(37장 7절 원문에도 숫자가 없습니다).</p>
    <p><b>19번째 칸 — 해와 달과 별(창세기 37장 9절).</b>
      하늘의 빛점이 <b>약 열두 개</b>로, 본문의 열한 개보다 하나 많습니다.
      바로 앞 18번째 칸에서 요셉이 「해와 달과 열한 별이 내게 절하더이다」라고 말한 직후라
      세어 보시는 분이 계실 수 있는 구간입니다. 빛점들은 활 모양이고 양 끝은 화면 밖으로 잘려 있습니다.
      해(주황빛 원반)와 달(은색 초승달)의 구분, 그리고 절하는 자세는 바르게 그려졌습니다.</p>
    <p>이 두 칸은 <b>숫자를 확인하는 그림이 아니라 「누가 누구에게 절하는가」를 보는 그림</b>으로 봐 주시면 됩니다.</p>
    <p>그 밖에 성경에 없지만 더한 것으로 <b>요셉 이마의 흉터</b>(36번째 칸부터 — 13년에 걸쳐 얼굴이 변하는 인물을
      계속 알아볼 수 있게 하는 표시이며, 어떤 인물도 이를 입에 올리지 않습니다)와
      <b>르우벤이 놓아둔 밧줄</b>(창세기 37장 22절 뒷부분의 「구원하여 돌려보내려 함이었더라」는 속마음을,
      해설 자막을 쓰지 않기로 했기에 물건으로 옮긴 것)이 있습니다.
      「르우벤은 막으려 했고 유다가 팔자고 했다」는 성경의 역할 배분은 그대로 지켰습니다.</p>
  </div></details>
</div></div></section>
"""


def build_html() -> Path:
    src = (SRC_PKG / "index.html").read_text(encoding="utf-8")
    n_png = len(re.findall(r'panels/panel_\d+\.png', src))
    html = re.sub(r'(panels/panel_\d+)\.png', r'\1.jpg', src)

    # head 주입 — </title> 바로 뒤
    html = html.replace("</title>", "</title>\n" + HEAD_INJECT, 1)
    # CSS 주입 — 마지막 </style> 앞
    idx = html.rindex("</style>")
    html = html[:idx] + EXTRA_CSS + html[idx:]
    # 프롤로그 / 에필로그
    html = html.replace('<main class="strip"', PROLOGUE + '<main class="strip"', 1)
    html = html.replace('</footer>', '</footer>\n' + EPILOGUE, 1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  · 패널 참조 .png→.jpg 치환: {n_png}건")
    return out


def main() -> int:
    if not (SRC_PKG / "index.html").is_file():
        print(f"소스 없음: {SRC_PKG}/index.html", file=sys.stderr)
        return 1
    print("공유본 빌드")
    n = build_panels()
    print(f"  · 패널 압축: {n}장 → {OUT_DIR/'panels'}")
    cov = build_cover()
    print(f"  · 표지: {cov.name} ({cov.stat().st_size//1024}KB)")
    out = build_html()
    total = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"  · HTML: {out} ({out.stat().st_size//1024}KB)")
    print(f"  · 합계: {total/1024/1024:.1f}MB")
    print(f"  · 배포 후 주소: {SITE_BASE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
