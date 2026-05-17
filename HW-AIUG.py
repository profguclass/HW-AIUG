import streamlit as st
import pandas as pd
import gspread

st.set_page_config(page_title="최후통첩 게임 데이터 입력 시스템", layout="wide")

st.title("🎮 AIUG 최후통첩 게임 데이터 제출 시스템")
st.markdown("""
**💡 데이터 입력 팁 (엑셀 호환)**
엑셀 파일에서 숫자 영역(16행 2열)만 복사(Ctrl+C)한 뒤, 아래 표의 첫 번째 빈칸을 클릭하고 붙여넣기(Ctrl+V) 하세요.
입력값은 반드시 **0.0000에서 1.0000 사이**여야 합니다.
""")

# 가장 안전한 표준 gspread 방식으로 구글 시트 직접 연결
@st.cache_resource
def get_gspread_client():
    # Secrets에 저장된 기존 구글 서비스 계정 정보를 토대로 인증 진행
    credentials = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    gc = gspread.service_account_from_dict(credentials)
    return gc

try:
    gc = get_gspread_client()
    # URL 주소에서 스프레드시트 열기
    sh = gc.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    worksheet = sh.get_worksheet(0) # 첫 번째 시트 선택
    
    # 기존 데이터 로드
    records = worksheet.get_all_records()
    if records:
        existing_data = pd.DataFrame(records)
    else:
        existing_data = pd.DataFrame()
except Exception as e:
    st.error(f"구글 시트 연동 중 오류 발생: {e}")
    existing_data = pd.DataFrame()

if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False

MODELS = ["ChatGPT", "Gemini", "Copilot", "Claude"]
STAKES = ["1만원", "10만원", "100만원", "1000만원"]
SCENARIOS = {"1HH": ("H", "H"), "2AA": ("A", "A"), "3AH": ("A", "H"), "4HA": ("H", "A")}

st.subheader("✍️ 1. 학생 정보 및 에세이 입력")
col_id, _ = st.columns([1, 2])
with col_id:
    student_id = st.text_input("학번 (10자리)", max_chars=10)
essay = st.text_area("실험 분석 짧은 에세이", placeholder="데이터를 바탕으로 관찰된 행동 패턴을 분석해 주세요...")

st.divider()
st.subheader("📊 2. 시나리오별 데이터 입력")

tabs = st.tabs(["📄 1HH 탭", "📄 2AA 탭", "📄 3AH 탭", "📄 4HA 탭"])
all_edited_data = {}

for tab, (sheet_name, (prop_type, resp_type)) in zip(tabs, SCENARIOS.items()):
    with tab:
        prop_base_label = f"{'Human' if prop_type == 'H' else 'AI'}제안"
        resp_base_label = f"{'Human' if resp_type == 'H' else 'AI'}수용"
        prop_display_label = f"{prop_base_label} (0~1)"
        resp_display_label = f"{resp_base_label} (0~1)"
        
        template_data = []
        for stake in STAKES:
            for model in MODELS:
                template_data.append({
                    "금액": stake, 
                    "AI모델": model, 
                    prop_base_label: None, 
                    resp_base_label: None
                })
        
        df_template = pd.DataFrame(template_data)
        
        edited_df = st.data_editor(
            df_template,
            disabled=["금액", "AI모델"],
            hide_index=True,
            use_container_width=True,
            column_config={
                prop_base_label: st.column_config.NumberColumn(prop_display_label, min_value=0.0, max_value=1.0, format="%.4f", required=True),
                resp_base_label: st.column_config.NumberColumn(resp_display_label, min_value=0.0, max_value=1.0, format="%.4f", required=True)
            },
            key=f"editor_{sheet_name}"
        )
        all_edited_data[sheet_name] = edited_df

st.divider()

if st.button("🚀 모든 데이터 최종 제출하기", use_container_width=True):
    if not student_id or not essay:
        st.error("❌ 학번과 에세이를 모두 입력해 주세요.")
    else:
        has_empty_cells = False
        has_invalid_values = False
        
        for sheet_name, (prop_type, resp_type) in SCENARIOS.items():
            df = all_edited_data[sheet_name]
            prop_base_label = f"{'Human' if prop_type == 'H' else 'AI'}제안"
            resp_base_label = f"{'Human' if resp_type == 'H' else 'AI'}수용"
            
            for _, row in df.iterrows():
                if pd.isna(row[prop_base_label]) or pd.isna(row[resp_base_label]):
                    has_empty_cells = True
                else:
                    try:
                        offer_val = float(row[prop_base_label])
                        mao_val = float(row[resp_base_label])
                        if not (0.0 <= offer_val <= 1.0) or not (0.0 <= mao_val <= 1.0):
                            has_invalid_values = True
                    except:
                        has_empty_cells = True
        
        if has_empty_cells:
            st.error("❌ 빈칸이 있거나 숫자가 아닌 값이 포함되어 있습니다. 모든 표를 올바르게 채워주세요.")
        elif has_invalid_values:
            st.error("❌ 입력된 값 중에 **0.0000 ~ 1.0000 범위를 벗어난 값**이 있습니다. 다시 확인해 주세요.")
        else:
            new_rows = []
            for sheet_name, (prop_type, resp_type) in SCENARIOS.items():
                df = all_edited_data[sheet_name]
                prop_base_label = f"{'Human' if prop_type == 'H' else 'AI'}제안"
                resp_base_label = f"{'Human' if resp_type == 'H' else 'AI'}수용"
                
                for _, row in df.iterrows():
                    offer_val = float(row[prop_base_label])
                    mao_val = float(row[resp_base_label])
                    
                    new_rows.append([
                        student_id,
                        row["AI모델"],
                        sheet_name[1:],
                        prop_type,
                        resp_type,
                        row["금액"],
                        offer_val,
                        mao_val,
                        "성사" if offer_val >= mao_val else "파기",
                        essay
                    ])
            
            try:
                # 만약 구글 시트가 완전히 비어있다면 제목 행 먼저 생성
                if not worksheet.get_all_values():
                    headers = ["student_id", "model", "scenario", "proposer_type", "responder_type", "stake", "offer_ratio", "mao_ratio", "deal_status", "essay"]
                    worksheet.append_row(headers)
                
                # 데이터 행 일괄 추가
                worksheet.append_rows(new_rows)
                st.session_state['submitted'] = True
                st.success("🎉 모든 데이터가 완벽하게 검증 및 저장되었습니다! 집계 현황판이 잠금 해제됩니다.")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"데이터 저장 실패: {e}")

# 4. 집계 결과 (조건부 잠금)
st.subheader("📈 3. 실시간 클래스 집계 현황판")
if st.session_state['submitted']:
    try:
        records = worksheet.get_all_records()
        updated_data = pd.DataFrame(records)
        
        if not updated_data.empty:
            st.metric(label="현재 클래스 전체 누적 데이터 수", value=f"{len(updated_data)} 건")
            chart_data = updated_data.groupby("model")[["offer_ratio", "mao_ratio"]].mean().reset_index()
            melted_chart = chart_data.melt(id_vars=["model"], var_name="비율 종류", value_name="평균 비율")
            st.bar_chart(data=melted_chart, x="model", y="평균 비율", color="비율 종류", use_container_width=True)
        else:
            st.info("데이터베이스에 축적된 데이터가 없습니다.")
    except Exception as e:
        st.info("실시간 차트를 불러오는 중입니다...")
else:
    st.warning("🔒 본인의 데이터 입력을 모두 마치고 [최종 제출하기] 버튼을 누르시면, 클래스 전체 학생들의 실시간 집계 그래프를 볼 수 있습니다.")
