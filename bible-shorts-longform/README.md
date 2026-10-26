# 성경 말씀 묵상 쇼츠 → 유튜브 롱폼 자동 제작

채널의 말씀·묵상 쇼츠를 모아 1920x1080 롱폼 영상 1개로 만듭니다.
- 가운데: 쇼츠 원본(9:16)
- 좌우 여백: 교회 실루엣 배경(또는 직접 넣은 교회·기도하는 손 사진) + 큰 글씨 제목·성경 구절·본문
- 함께 생성: 썸네일 2종, 유튜브 제목 후보·설명(챕터 포함)·고정댓글·태그

## 준비
```
pip install yt-dlp pillow
# ffmpeg 설치 필요 (https://ffmpeg.org)
```

## 사용법
```
python make_longform.py plan            # 쇼츠 목록 수집 → clips.json
#   clips.json 에서 제목·reference(구절)·verse_text(본문) 확인/수정, 뺄 영상은 "use": false
python make_longform.py build           # 영상 제작 → output/
python make_longform.py build --bg 기도하는손.jpg   # 배경 사진 직접 지정
```
`settings.json`(첫 실행 시 생성)에서 시리즈명·메인 제목·필터 키워드를 바꿀 수 있습니다.

## 결과물 (output/)
- `longform.mp4` 롱폼 영상
- `thumbnail.jpg`, `thumbnail_text_only.jpg` 썸네일(1280x720)
- `youtube_texts.txt` 제목 후보·설명·고정댓글·태그

※ 본인 채널 영상이거나 권리자의 허락을 받은 영상만 사용하세요.

## 나노바나나 배경 만들기 (선택)
```
set GEMINI_API_KEY=발급받은키        # Windows (macOS/Linux: export GEMINI_API_KEY=...)
python nanobanana.py                # backgrounds/church.png, hands.png, chapel.png 생성
python make_longform.py build --bg backgrounds/hands.png
```
