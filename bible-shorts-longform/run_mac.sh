#!/bin/bash
# 맥에서 성경 말씀 묵상 롱폼 영상을 한 번에 만드는 스크립트
# 사용법: 터미널에 아래 한 줄 붙여넣기
#   curl -fsSL https://raw.githubusercontent.com/backdraft96/nono/claude/peaceful-galileo-uhfu6y/bible-shorts-longform/run_mac.sh | bash
set -e
BRANCH="claude/peaceful-galileo-uhfu6y"
DIR="$HOME/bible-longform"
BG="${BG:-hands}"   # hands(기도하는 손) / church(교회) / chapel(예배당)

say_step() { printf "\n\033[1;33m▶ %s\033[0m\n" "$1"; }

say_step "1/5 필요한 프로그램 확인 (처음에는 몇 분 걸립니다)"
if ! command -v brew >/dev/null 2>&1; then
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$($p shellenv)"; done
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew 설치를 시작합니다. 맥 로그인 비밀번호를 물으면 입력하세요(화면에 안 보여도 입력됩니다)."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/tty
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$p" ] && eval "$($p shellenv)"; done
  grep -q "brew shellenv" "$HOME/.zprofile" 2>/dev/null || echo "eval \"\$($(command -v brew) shellenv)\"" >> "$HOME/.zprofile"
fi
command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list python >/dev/null 2>&1 || brew install python
PY="$(brew --prefix)/bin/python3"

say_step "2/5 스크립트 내려받기 → $DIR"
mkdir -p "$DIR"
TMP="$(mktemp -d)"
curl -fsSL "https://codeload.github.com/backdraft96/nono/zip/refs/heads/$BRANCH" -o "$TMP/src.zip"
unzip -q "$TMP/src.zip" -d "$TMP"
cp -R "$TMP"/nono-*/bible-shorts-longform/. "$DIR/"
rm -rf "$TMP"
cd "$DIR"

say_step "3/5 파이썬 도구 설치"
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip yt-dlp pillow

say_step "4/5 채널에서 말씀 묵상 쇼츠 고르기"
[ -f clips.json ] && echo "기존 clips.json 을 그대로 사용합니다 (새로 고르려면 삭제 후 다시 실행)" || python make_longform.py plan

say_step "5/5 영상 만들기 (10~20분 정도 걸립니다)"
if ! python make_longform.py build --bg "bg/$BG.jpg"; then
  echo "다운로드가 막혀 브라우저 로그인 정보로 다시 시도합니다. (크롬은 완전히 종료(⌘Q)해 두세요)"
  python make_longform.py build --bg "bg/$BG.jpg" --cookies-from-browser chrome \
  || python make_longform.py build --bg "bg/$BG.jpg" --cookies-from-browser safari
fi

printf "\n\033[1;32m✔ 완성! Finder에서 결과 폴더를 엽니다: %s/output\033[0m\n" "$DIR"
open "$DIR/output"
