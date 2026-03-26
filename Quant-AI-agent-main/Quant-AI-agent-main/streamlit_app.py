from pathlib import Path

import streamlit as st

from main import DEFAULT_OUTPUT_PATH, generate_and_save_strategy

st.set_page_config(
    page_title="多策略量化代码生成器",
    layout="wide",
)

if "generated_code" not in st.session_state:
    st.session_state.generated_code = ""

if "error_message" not in st.session_state:
    st.session_state.error_message = ""

st.title("多策略量化代码生成器")
st.caption("输入自然语言策略描述，自动生成量化策略代码。")

with st.form("strategy_generator_form"):
    api_key = st.text_input("DeepSeek API Key", type="password")
    strategy_text = st.text_area(
        "策略描述",
        height=180,
        placeholder="例如：我要做一份十只股票的 kdj 策略",
    )
    submitted = st.form_submit_button("生成代码", use_container_width=True)

if submitted:
    st.session_state.generated_code = ""
    st.session_state.error_message = ""

    if not api_key.strip():
        st.session_state.error_message = "请输入 API key。"
    elif not strategy_text.strip():
        st.session_state.error_message = "请输入策略描述。"
    else:
        try:
            with st.spinner("正在生成代码..."):
                st.session_state.generated_code = generate_and_save_strategy(
                    strategy_text,
                    api_key=api_key.strip(),
                )
        except Exception as exc:
            st.session_state.error_message = f"生成失败：{exc}"

st.subheader("生成结果")

if st.session_state.error_message:
    st.error(st.session_state.error_message)

if st.session_state.generated_code:
    st.success(f"代码已写入：{Path(DEFAULT_OUTPUT_PATH).name}")
    st.code(st.session_state.generated_code, language="python")
else:
    st.info("生成后的量化代码会显示在这里。")
