from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


KST = ZoneInfo("Asia/Seoul")


def dashboard_config() -> dict[str, str] | None:
    try:
        section = st.secrets["dashboard"]
        names = (
            "supabase_url",
            "supabase_secret_key",
            "visitor_salt",
            "dashboard_password",
        )
        values = {name: str(section[name]).strip() for name in names}
    except Exception:
        return None

    if any(not value for value in values.values()):
        return None
    return values


def current_visitor_id(visitor_salt: str) -> str:
    ip_address = str(st.context.ip_address or "unknown-ip")
    user_agent = str(st.context.headers.get("User-Agent", "unknown-agent"))
    source = f"{visitor_salt}|{ip_address}|{user_agent}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()


@st.cache_data(ttl=300, show_spinner=False)
def load_visits(supabase_url: str, secret_key: str) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    page_size = 1000

    for offset in range(0, 100_000, page_size):
        response = requests.get(
            f"{supabase_url.rstrip('/')}/rest/v1/daily_visitors",
            headers={
                "apikey": secret_key,
                "Range": f"{offset}-{offset + page_size - 1}",
            },
            params={
                "select": "visit_date,visitor_id,created_at",
                "order": "visit_date.asc,created_at.asc",
            },
            timeout=(3, 10),
        )
        response.raise_for_status()
        page = response.json()
        if not isinstance(page, list):
            raise ValueError("방문 기록 응답 형식이 올바르지 않습니다.")
        rows.extend(page)
        if len(page) < page_size:
            break

    frame = pd.DataFrame(rows, columns=["visit_date", "visitor_id", "created_at"])
    if frame.empty:
        return frame

    frame["visit_date"] = pd.to_datetime(frame["visit_date"], errors="coerce").dt.date
    frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce", utc=True)
    return frame.dropna(subset=["visit_date", "visitor_id"])


def authenticate(expected_password: str) -> None:
    if st.session_state.get("dashboard_authenticated"):
        return

    with st.form("dashboard_login"):
        password = st.text_input("비밀번호", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("확인", use_container_width=True)

    if submitted:
        if hmac.compare_digest(password.encode(), expected_password.encode()):
            st.session_state["dashboard_authenticated"] = True
            st.rerun()
        st.error("비밀번호가 맞지 않습니다.")
    st.stop()


st.set_page_config(page_title="방문자 대시보드", page_icon="📊", layout="centered")

st.markdown(
    """<style>
    .block-container {max-width: 820px; padding-top: 2.4rem; padding-bottom: 4rem;}
    h1 {font-size: 1.75rem !important; letter-spacing: -.04em;}
    div[data-testid="stMetric"] {
        background: #fffaf8;
        border: 1px solid #eee2dc;
        border-radius: 12px;
        padding: .9rem 1rem;
    }
    </style>""",
    unsafe_allow_html=True,
)

st.title("방문자 대시보드")

config = dashboard_config()
if config is None:
    st.error("대시보드 연결 정보가 없습니다. README의 Secrets 설정을 확인해 주세요.")
    st.stop()

authenticate(config["dashboard_password"])

top_left, top_right = st.columns([4, 1])
with top_right:
    if st.button("로그아웃", use_container_width=True):
        st.session_state["dashboard_authenticated"] = False
        st.rerun()

try:
    visits = load_visits(config["supabase_url"], config["supabase_secret_key"])
except (requests.RequestException, ValueError) as exc:
    st.error(f"방문 기록을 불러오지 못했습니다: {exc}")
    st.stop()

today = datetime.now(KST).date()
exclude_owner = st.checkbox(
    "현재 브라우저에서 발생한 내 방문 제외",
    value=True,
    help="같은 네트워크와 브라우저로 공개 페이지에 접속한 기록만 제외할 수 있습니다.",
)
if exclude_owner and not visits.empty:
    own_id = current_visitor_id(config["visitor_salt"])
    visits = visits[visits["visitor_id"] != own_id].copy()

if visits.empty:
    st.info("아직 기록된 방문자가 없습니다. 추적 코드를 공개 앱에 연결한 뒤부터 기록됩니다.")
    st.stop()

first_date = visits["visit_date"].min()
default_start = max(first_date, today - timedelta(days=29))
date_range = st.date_input(
    "조회 기간",
    value=(default_start, today),
    min_value=first_date,
    max_value=today,
    format="YYYY/MM/DD",
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("시작일과 종료일을 모두 선택해 주세요.")
    st.stop()

start_date, end_date = date_range
filtered = visits[
    (visits["visit_date"] >= start_date)
    & (visits["visit_date"] <= end_date)
].copy()

today_unique = visits.loc[visits["visit_date"] == today, "visitor_id"].nunique()
period_unique = filtered["visitor_id"].nunique()
lifetime_unique = visits["visitor_id"].nunique()

metric_today, metric_period, metric_total = st.columns(3)
metric_today.metric("오늘", f"{today_unique:,}명")
metric_period.metric("선택 기간", f"{period_unique:,}명")
metric_total.metric("누적", f"{lifetime_unique:,}명")

calendar_days = pd.date_range(start=start_date, end=end_date, freq="D").date
daily = (
    filtered.groupby("visit_date")["visitor_id"]
    .nunique()
    .reindex(calendar_days, fill_value=0)
    .rename("고유 방문자")
)
daily.index = pd.to_datetime(daily.index)

st.subheader("일일 고유 방문자")
st.bar_chart(daily, height=320, color="#d88973")

daily_table = daily.rename_axis("날짜").reset_index()
daily_table["날짜"] = daily_table["날짜"].dt.strftime("%Y-%m-%d")
daily_table = daily_table.sort_values("날짜", ascending=False)
st.dataframe(daily_table, hide_index=True, use_container_width=True)

st.caption(
    "IP 주소와 브라우저 정보는 저장하지 않고 식별용 해시만 저장합니다. "
    "네트워크나 브라우저가 바뀌면 같은 사람도 다른 방문자로 계산될 수 있습니다."
)
