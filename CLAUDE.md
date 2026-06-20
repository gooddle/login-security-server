# Login Security Server

FastAPI 기반 보안 감사 로그 시스템. 새로운 IP에서 로그인 시 이메일 알림 발송.

## 스택
- Python 3.13 + FastAPI
- SQLite (SQLAlchemy)
- bcrypt (패스워드 해싱)
- Resend (이메일 발송)
- pytest (테스트)

## 핵심 비즈니스 로직
- 로그인 성공 시 IP 확인
- 새 IP → 이메일 알림 발송 + IP 저장
- 기존 IP → 그냥 통과 (이메일 없음)

## 테스트 실행
```bash
.venv/bin/pytest -v
```

## TDD 규칙
- 기능 추가 전 반드시 실패하는 테스트 먼저 작성 (RED)
- 최소한의 코드로 테스트 통과 (GREEN)
- 리팩토링 (REFACTOR)
- 테스트 없는 코드는 머지 금지

## 문서화 규칙
- 기능 추가/변경 시 `docs/YYYY-MM-DD.md` 파일에 항상 기록
- 파일이 없으면 오늘 날짜로 새로 생성
- 형식: `## feat|fix|refactor: 기능명` + 변경 내용 bullet

## 코드 품질 규칙

### 쿼리
- N+1 방지: 관계 데이터는 `joinedload` / `selectinload` 사용
- 페이지네이션 없는 전체 조회 금지
- 인덱스 없는 컬럼 조회 지양

### 코드 구조
- 함수 하나는 하나의 역할만
- 비즈니스 로직은 `services/` 레이어에만
- 환경변수 하드코딩 금지

### 보안
- SQL 직접 쿼리 금지, ORM 사용
- 입력값 Pydantic으로 검증 필수
- 민감 정보 로그 출력 금지
- AWS 키 등 시크릿 절대 커밋 금지 (gitleaks가 차단)

### 테스트
- 새 기능은 테스트 먼저 작성 (TDD)
- 외부 API 호출은 mock 처리
- 테스트 없는 코드 머지 금지

## 환경 변수 (.env)
- `DATABASE_URL` - SQLite DB 경로
- `SECRET_KEY` - JWT 서명 키
- `RESEND_API_KEY` - Resend 이메일 API 키
- `EMAIL_FROM` - 발신 이메일 주소

## 디렉토리 구조
```
app/
├── api/routes/    # FastAPI 라우터
├── core/          # config, database
├── models/        # SQLAlchemy 모델
└── services/      # 비즈니스 로직
tests/             # pytest 테스트
```
