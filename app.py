import os
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# --- 화면 기본 설정 ---
st.set_page_config(page_title="나의 투자 시그널 봇", page_icon="📈", layout="wide")

# --- 데이터 저장 함수 (구글 시트 연동) ---
SHEET_WORKSHEET_1 = "Session_1"
SHEET_WORKSHEET_2 = "Session_2"

def load_history(worksheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=worksheet_name, ttl=0) # ttl=0: 항상 드라이브에서 최신 데이터 로드
        if df.empty or "날짜" not in df.columns:
            return pd.DataFrame(columns=["날짜", "종목", "종류", "수량", "가격", "총액", "메모"])
        return df.dropna(how="all") # 빈 줄 제거
    except Exception:
        # 시트가 없거나 연동 전일 경우 빈 데이터프레임 반환
        return pd.DataFrame(columns=["날짜", "종목", "종류", "수량", "가격", "총액", "메모"])

def save_history(df, worksheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    conn.update(worksheet=worksheet_name, data=df)


def render_record_ui(session_id, worksheet_name, history_df, calc_shares, calc_avg, profits_list, cum_profits_list):
    st.subheader(f"📝 세션 {session_id} 매매 기록 남기기")
            if len(records_to_add) > 0:
                new_record = pd.DataFrame(records_to_add)
                curr_df = load_history(worksheet_name)
                curr_df = pd.concat([curr_df, new_record], ignore_index=True)
                save_history(curr_df, worksheet_name)
                st.success(f"✅ 세션 {session_id} 매매 기록이 성공적으로 저장되었습니다.")
    st.divider()
    
    c_title, c_btn = st.columns([3, 1])
    with c_title:
        st.subheader(f"📋 세션 {session_id} 전체 매매 내역")
    with c_btn:
        if st.button("🔄 드라이브에서 로드", key=f"reload_{session_id}"):
            st.rerun() # ttl=0 설정으로 인해 rerun 시 즉시 시트 데이터를 다시 읽어옵니다.
    
        with st.expander(f"세션 {session_id} 위험 구역 (Danger Zone)"):
            if st.button("모든 기록 영구 삭제", type="primary", key=f"del_{session_id}"):
                # 빈 데이터프레임으로 시트를 덮어씌워 삭제 효과
                empty_df = pd.DataFrame(columns=["날짜", "종목", "종류", "수량", "가격", "총액", "메모"])
                save_history(empty_df, worksheet_name)
                st.success("모든 기록이 삭제되었습니다.")
# --- 데이터 불러오기 및 현재 상태 계산 ---
hist_df1 = load_history(SHEET_WORKSHEET_1)
sh1, avg1, day1, p_list1, cum_p1 = calculate_portfolio_state(hist_df1)

hist_df2 = load_history(SHEET_WORKSHEET_2)
sh2, avg2, day2, p_list2, cum_p2 = calculate_portfolio_state(hist_df2)
    with col_r1:
        render_record_ui(1, SHEET_WORKSHEET_1, hist_df1, sh1, avg1, p_list1, cum_p1)
    with col_r2:
        render_record_ui(2, SHEET_WORKSHEET_2, hist_df2, sh2, avg2, p_list2, cum_p2)
