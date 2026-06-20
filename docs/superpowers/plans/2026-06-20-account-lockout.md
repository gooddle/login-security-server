# Account Lockout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로그인 5회 연속 실패 시 계정을 30분 잠금하고, 잠금 중 남은 시간을 에러 메시지로 반환한다.

**Architecture:** User 모델에 `failed_attempts` / `locked_until` 컬럼을 추가하고, `auth_service`에서 잠금 여부 확인 → 실패 횟수 증가 → 초기화 로직을 처리한다. Strawberry GraphQL은 `auth_service`에서 발생한 `ValueError`를 그대로 GraphQL error로 반환하므로 `mutations.py`는 수정하지 않는다.

**Tech Stack:** Python 3.13, FastAPI, Strawberry GraphQL, SQLAlchemy (SQLite), bcrypt, pytest

## Global Constraints

- DB는 SQLite — `locked_until` 저장 시 naive UTC datetime 사용 (SQLite가 timezone 미지원)
- `datetime.utcnow()`는 deprecated → `datetime.now(timezone.utc).replace(tzinfo=None)` 사용
- 비즈니스 로직은 `services/` 레이어에만 위치
- 외부 API 호출(`send_new_ip_alert`)은 mock 처리
- TDD: 실패 테스트 먼저 작성 → 구현 → 통과 확인 순서 엄수
- 테스트 실행: `.venv/bin/pytest -v`

---

## File Structure

| 파일 | 역할 |
|---|---|
| `app/models/user.py` | `failed_attempts`, `locked_until` 컬럼 추가 |
| `app/services/auth_service.py` | `is_account_locked`, `record_failed_attempt`, `reset_failed_attempts` 함수 추가; `authenticate_user` 수정 |
| `tests/test_graphql.py` | 잠금 관련 통합 테스트 5개 추가 |
| `docs/2026-06-20.md` | 기능 변경 기록 추가 |

---

### Task 1: User 모델에 계정 잠금 컬럼 추가

**Files:**
- Modify: `app/models/user.py`

**Interfaces:**
- Produces: `User.failed_attempts: int` (default 0), `User.locked_until: datetime | None`

- [ ] **Step 1: `app/models/user.py` 수정**

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    failed_attempts = Column(Integer, default=0, nullable=False, server_default="0")
    locked_until = Column(DateTime, nullable=True)

    known_ips = relationship("KnownIP", back_populates="user")


class KnownIP(Base):
    __tablename__ = "known_ips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="known_ips")
```

- [ ] **Step 2: 기존 테스트로 회귀 없음 확인**

```bash
.venv/bin/pytest -v
```

Expected: 기존 테스트 8개 모두 PASSED

- [ ] **Step 3: 커밋**

```bash
git add app/models/user.py
git commit -m "feat: User 모델에 failed_attempts, locked_until 컬럼 추가"
```

---

### Task 2: 계정 잠금 로직 TDD 구현

**Files:**
- Modify: `app/services/auth_service.py`
- Modify: `tests/test_graphql.py`
- Modify: `docs/2026-06-20.md`

**Interfaces:**
- Consumes: `User.failed_attempts: int`, `User.locked_until: datetime | None` (Task 1에서 추가)
- Produces:
  - `is_account_locked(user: User) -> tuple[bool, int]` — `(잠금여부, 남은초)`
  - `record_failed_attempt(db: Session, user: User) -> None`
  - `reset_failed_attempts(db: Session, user: User) -> None`
  - `authenticate_user` — 잠금 시 `ValueError("계정이 잠겼습니다. N분 N초 후 다시 시도하세요")` 발생

- [ ] **Step 1: `tests/test_graphql.py`에 실패 테스트 5개 추가**

파일 상단 import 추가:

```python
from datetime import datetime, timedelta, timezone
```

파일 끝에 테스트 5개 추가:

```python
def test_failed_attempts_increments_on_wrong_password(client, db):
    user = make_user(db)
    gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    db.refresh(user)
    assert user.failed_attempts == 1


def test_account_locks_after_5_failures(client, db):
    make_user(db)
    for _ in range(5):
        gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    res = gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    errors = res.json()["errors"]
    assert errors is not None
    assert "잠겼습니다" in errors[0]["message"]


def test_lockout_error_contains_remaining_time(client, db):
    make_user(db)
    for _ in range(5):
        gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    res = gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    errors = res.json()["errors"]
    assert errors is not None
    assert "분" in errors[0]["message"]


def test_locked_account_auto_unlocks_after_expiry(client, db):
    user = make_user(db)
    user.failed_attempts = 5
    user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()
    with patch("app.services.auth_service.send_new_ip_alert"):
        res = gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
    assert res.json()["data"]["login"]["message"] == "로그인 성공"


def test_login_success_resets_failed_attempts(client, db):
    user = make_user(db)
    gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    with patch("app.services.auth_service.send_new_ip_alert"):
        res = gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
    assert res.json()["data"]["login"]["message"] == "로그인 성공"
    db.refresh(user)
    assert user.failed_attempts == 0
    assert user.locked_until is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/pytest tests/test_graphql.py::test_failed_attempts_increments_on_wrong_password tests/test_graphql.py::test_account_locks_after_5_failures tests/test_graphql.py::test_lockout_error_contains_remaining_time tests/test_graphql.py::test_locked_account_auto_unlocks_after_expiry tests/test_graphql.py::test_login_success_resets_failed_attempts -v
```

Expected: 5개 모두 FAILED (AttributeError: 'User' object has no attribute 'failed_attempts' 또는 AssertionError)

- [ ] **Step 3: `app/services/auth_service.py` 전체 교체**

```python
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.email_service import send_new_ip_alert
from app.services.ip_service import is_known_ip, register_ip


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_user(db: Session, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def is_account_locked(user: User) -> tuple[bool, int]:
    """잠금 여부와 남은 초를 반환. locked_until이 지났으면 자동 해제."""
    if user.locked_until is None:
        return False, 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now >= user.locked_until:
        return False, 0
    remaining = int((user.locked_until - now).total_seconds())
    return True, remaining


def record_failed_attempt(db: Session, user: User) -> None:
    user.failed_attempts = int(user.failed_attempts) + 1
    if int(user.failed_attempts) >= 5:
        user.locked_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    db.commit()


def reset_failed_attempts(db: Session, user: User) -> None:
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()


def authenticate_user(db: Session, email: str, password: str, ip_address: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None

    locked, remaining = is_account_locked(user)
    if locked:
        minutes = remaining // 60
        seconds = remaining % 60
        raise ValueError(f"계정이 잠겼습니다. {minutes}분 {seconds}초 후 다시 시도하세요")

    if not verify_password(password, str(user.hashed_password)):
        record_failed_attempt(db, user)
        return None

    reset_failed_attempts(db, user)

    if not is_known_ip(db, int(user.id), ip_address):
        send_new_ip_alert(str(user.email), ip_address)
        register_ip(db, int(user.id), ip_address)

    return user
```

- [ ] **Step 4: 새 테스트 5개 통과 확인**

```bash
.venv/bin/pytest tests/test_graphql.py::test_failed_attempts_increments_on_wrong_password tests/test_graphql.py::test_account_locks_after_5_failures tests/test_graphql.py::test_lockout_error_contains_remaining_time tests/test_graphql.py::test_locked_account_auto_unlocks_after_expiry tests/test_graphql.py::test_login_success_resets_failed_attempts -v
```

Expected: 5개 모두 PASSED

- [ ] **Step 5: 전체 테스트 회귀 없음 확인**

```bash
.venv/bin/pytest -v
```

Expected: 13개 모두 PASSED (기존 8개 + 신규 5개)

- [ ] **Step 6: `docs/2026-06-20.md`에 변경 이력 추가**

파일 끝에 추가:

```markdown

## feat: 5회 로그인 실패 시 계정 잠금
- User 모델에 `failed_attempts` (int, default 0), `locked_until` (datetime, nullable) 추가
- `auth_service`: `is_account_locked`, `record_failed_attempt`, `reset_failed_attempts` 함수 추가
- 5회 실패 → 30분 잠금, 잠금 만료 시 자동 해제
- 잠금 중 남은 시간(N분 N초) 에러 메시지 반환
- 테스트: 5개 추가 (카운터 증가, 잠금 발생, 남은 시간, 자동 해제, 성공 시 초기화)
```

- [ ] **Step 7: 커밋**

```bash
git add app/services/auth_service.py tests/test_graphql.py docs/2026-06-20.md
git commit -m "feat: 5회 로그인 실패 시 30분 계정 잠금 구현"
```

---

## Self-Review

**1. Spec coverage:**
- [x] `failed_attempts`, `locked_until` 컬럼 추가 → Task 1
- [x] 로그인 실패 시 `failed_attempts + 1` → `record_failed_attempt`
- [x] 5회 도달 시 `locked_until = now + 30분` → `record_failed_attempt` 내 `if >= 5`
- [x] 잠금 확인 → 에러 반환 → `is_account_locked` + `authenticate_user` ValueError
- [x] 성공 시 초기화 → `reset_failed_attempts`
- [x] 잠금 만료 후 자동 해제 → `is_account_locked`의 `now >= locked_until` 분기
- [x] 남은 시간 메시지 → `{minutes}분 {seconds}초 후 다시 시도하세요`

**2. Placeholder scan:** 없음 — 모든 단계에 실제 코드 포함

**3. Type consistency:**
- `is_account_locked(user: User) -> tuple[bool, int]` — Task 2 Step 1 테스트와 Step 3 구현 일치
- `record_failed_attempt(db: Session, user: User) -> None` — 일관성 확인
- `reset_failed_attempts(db: Session, user: User) -> None` — 일관성 확인
- `User.failed_attempts`, `User.locked_until` — Task 1과 Task 2 전반에서 동일 명칭 사용
