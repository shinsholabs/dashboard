# 비공개 방문자 대시보드

버전: **v1.0**

공개 Streamlit 페이지의 일일·기간별·누적 고유 방문자를 확인하는 별도의 관리자용 웹앱입니다. 기존 기사 앱과 독립적으로 배포하며, 대시보드는 Streamlit 비공개 접근 설정과 자체 비밀번호로 보호합니다.

## 중요한 제한

- 통계는 추적 코드를 연결한 날부터 기록됩니다. 2026년 9월 30일부터의 과거 일일 방문자는 복원할 수 없습니다.
- IP 주소와 브라우저 정보는 저장하지 않고 비밀값을 섞은 SHA-256 식별용 해시만 저장합니다.
- 같은 사람이 네트워크 또는 브라우저를 바꾸면 다른 방문자로 계산될 수 있습니다.
- 서로 다른 사람이 같은 네트워크와 같은 브라우저 환경을 사용하면 한 명으로 합쳐질 수 있습니다.
- Supabase 무료 플랜 범위에서 사용할 수 있으며, 별도 유료 API는 사용하지 않습니다. 서비스별 무료 한도와 정책은 변경될 수 있습니다.

## 파일 구성

- `app.py`: 새로 배포할 비공개 방문자 대시보드
- `supabase_setup.sql`: 방문 기록 테이블과 안전한 기록 함수 생성
- `integration/visitor_tracker.py`: 기존 공개 기사 앱에 복사할 가벼운 추적 모듈
- `.streamlit/secrets.toml.example`: 대시보드용 Secrets 예시

## 1. Supabase 준비

1. [Supabase](https://supabase.com/)에서 무료 프로젝트를 만듭니다.
2. **SQL Editor**에서 `supabase_setup.sql` 전체를 실행합니다.
3. **Project Settings → API Keys**에서 다음 값을 확인합니다.
   - Project URL
   - Publishable key (`sb_publishable_...`)
   - Secret key (`sb_secret_...`)

Secret key는 서버 전용이며 GitHub나 공개 앱 화면에 노출하면 안 됩니다.

## 2. 기존 공개 기사 앱에 추적 연결

`integration/visitor_tracker.py`를 기존 기사 앱의 `app.py`와 같은 폴더에 복사합니다.

기존 `app.py`의 import 부분에 다음 한 줄을 추가합니다.

```python
from visitor_tracker import record_visit_once
```

`st.set_page_config(...)` 바로 다음 줄에 다음 코드를 추가합니다.

```python
record_visit_once()
```

기존 공개 앱의 Streamlit **Settings → Secrets**에 다음 내용을 입력합니다.

```toml
[visitor_tracking]
supabase_url = "https://YOUR_PROJECT.supabase.co"
supabase_publishable_key = "sb_publishable_YOUR_KEY"
visitor_salt = "길고-추측하기-어려운-임의문자열"
```

방문 기록은 백그라운드에서 전송되므로 기사 화면 표시를 기다리게 하지 않습니다. 설정이 없거나 통계 서버에 문제가 생겨도 기존 기사 앱은 그대로 작동합니다.

## 3. 새 대시보드 배포

이 `visitor_dashboard` 폴더를 기존 기사 앱과 다른 GitHub 저장소에 올리는 것을 권장합니다.

1. Streamlit Community Cloud에서 새 앱을 만듭니다.
2. 새 저장소를 선택하고 메인 파일을 `app.py`로 지정합니다.
3. **Settings → Sharing → Only specific people can view this app**을 선택합니다.
4. 다른 사용자를 Viewer나 Developer로 초대하지 않습니다.
5. 대시보드 앱의 **Settings → Secrets**에 아래 내용을 입력합니다.

```toml
[dashboard]
supabase_url = "https://YOUR_PROJECT.supabase.co"
supabase_secret_key = "sb_secret_YOUR_KEY"
visitor_salt = "공개 앱과 동일한 임의문자열"
dashboard_password = "대시보드에서 사용할 별도 비밀번호"
```

6. 앱을 재부팅한 뒤 설정한 비밀번호로 로그인합니다.

공개 앱과 대시보드의 `visitor_salt`는 반드시 같아야 현재 브라우저의 본인 방문을 제외할 수 있습니다. 실제 `secrets.toml` 파일은 GitHub에 올리지 마세요.

## 표시되는 통계

- 오늘의 고유 방문자
- 선택 기간의 중복 제거 고유 방문자
- 기록 시작 후 누적 고유 방문자
- 날짜별 고유 방문자 막대그래프
- 날짜별 방문자 표
- 현재 브라우저에서 발생한 본인 방문 제외 옵션

대시보드에는 방문자 식별용 해시나 접속 원문 정보가 표시되지 않으며 집계 숫자만 표시됩니다.
