# Naver Blog Crawler

네이버 블로그 게시글, 댓글, 공감 정보를 수집하는 GUI 기반 크롤러입니다.

## 주요 기능

- 블로그 정보 수집 (블로그명, 작성자, 게시글 수)
- 게시글 목록 및 내용 크롤링
- 공감(좋아요) 정보 수집
- 댓글 및 대댓글 수집 (페이지네이션 지원)
- SQLite 데이터베이스 저장
- JSON/CSV 형식 내보내기
- 크롤링 진행 상황 저장 및 재개

## 스크린샷

```
┌─────────────────────────────────────────┐
│  네이버 블로그 크롤러                      │
├─────────────────────────────────────────┤
│  블로그 URL: [________________] [추가]    │
├─────────────────────────────────────────┤
│  블로그 목록:                             │
│  ☑ 블로그1 - 완료                        │
│  ☑ 블로그2 - 진행중 (50%)                │
├─────────────────────────────────────────┤
│  [시작] [중지] [내보내기]                  │
└─────────────────────────────────────────┘
```

## 설치

### 요구사항

- Python 3.9+
- Chrome 브라우저 (댓글 수집용)

### 설치 방법

```bash
# 저장소 클론
git clone https://github.com/kate-05/Claude_NaverBlogExtractor.git
cd Claude_NaverBlogExtractor

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

## 사용법

### 실행

```bash
python main.py
```

### 블로그 추가

1. 블로그 URL 입력 (예: `https://blog.naver.com/blogid`)
2. "추가" 버튼 클릭
3. 블로그 정보가 자동으로 수집됨

### 크롤링

1. 수집할 블로그 선택 (체크박스)
2. "시작" 버튼 클릭
3. 진행 상황이 실시간으로 표시됨

### 내보내기

1. 크롤링 완료 후 "내보내기" 버튼 클릭
2. JSON 또는 CSV 형식 선택
3. `exports/` 폴더에 파일 저장됨

## 프로젝트 구조

```
naver_blog_crawler/
├── main.py              # GUI 메인 애플리케이션
├── config.py            # 설정 파일
├── requirements.txt     # 의존성 목록
├── crawler/
│   ├── blog.py          # 블로그 정보 크롤러
│   ├── post.py          # 게시글 크롤러
│   ├── comment.py       # 댓글 크롤러
│   ├── reaction.py      # 공감 크롤러
│   └── selenium_helper.py
├── database/
│   ├── manager.py       # DB 관리자
│   └── models.py        # 데이터 모델
├── utils/
│   └── helpers.py       # 유틸리티 함수
└── exports/             # 내보내기 파일 저장 폴더
```

## 내보내기 형식

### JSON

```json
{
  "blog": {
    "id": "blogid",
    "blog_name": "블로그 이름",
    "author_name": "작성자",
    "url": "https://blog.naver.com/blogid"
  },
  "posts": [
    {
      "title": "게시글 제목",
      "content": "게시글 내용",
      "post_date": "2025.01.01",
      "comments": [
        {
          "author": "댓글 작성자",
          "content": "댓글 내용",
          "written_at": "2025.01.02"
        }
      ]
    }
  ]
}
```

### CSV

- `블로그명_posts_날짜.csv`: 게시글 목록
- `블로그명_comments_날짜.csv`: 댓글 목록

## 주의사항

- 네이버 서버에 부담을 주지 않도록 요청 간 딜레이가 설정되어 있습니다
- 대량 크롤링 시 IP 차단될 수 있으니 주의하세요
- 수집한 데이터는 개인 용도로만 사용하세요

## 라이선스

MIT License
