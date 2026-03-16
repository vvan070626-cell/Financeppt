import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pptx import Presentation
import fitz  # PyMuPDF
import io

# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI 学习助手",
    page_icon="[AI]",
    layout="wide"
)

st.title("AI 学习助手 - 多文件对话")
st.caption("上传多个 PPT / PDF 文件，每个文件将生成独立的对话窗口")

# ─────────────────────────────────────────────
# 初始化 LLM
# ─────────────────────────────────────────────
api_key = st.secrets["DEEPSEEK_API_KEY"]

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=api_key,
    base_url="https://api.deepseek.com",
    max_retries=2
)

# ─────────────────────────────────────────────
# 文本提取函数
# ─────────────────────────────────────────────
def extract_pptx(file_bytes):
    prs = Presentation(io.BytesIO(file_bytes))
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = " ".join([run.text for run in para.runs]).strip()
                    if line:
                        texts.append(line)
    return "\n".join(texts)

def extract_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texts = []
    for page in doc:
        texts.append(page.get_text())
    return "\n".join(texts)

def extract_content(uploaded_file):
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pptx"):
        return extract_pptx(file_bytes)
    elif name.endswith(".pdf"):
        return extract_pdf(file_bytes)
    else:
        return None

# ─────────────────────────────────────────────
# 初始化 session_state
# ─────────────────────────────────────────────
# chat_histories: { filename: [{"role": "user/assistant", "content": "..."}, ...] }
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}

# file_contents: { filename: "extracted text..." }
if "file_contents" not in st.session_state:
    st.session_state.file_contents = {}

# ─────────────────────────────────────────────
# 文件上传区
# ─────────────────────────────────────────────
uploaded_files = st.file_uploader(
    "上传文件（支持 .pptx / .pdf，可同时上传多个）",
    type=["pptx", "pdf"],
    accept_multiple_files=True   # 关键：允许多文件
)

# 处理新上传的文件，提取内容并初始化对话历史
if uploaded_files:
    for file in uploaded_files:
        fname = file.name
        # 只处理没有被提取过的文件（避免重复提取）
        if fname not in st.session_state.file_contents:
            with st.spinner(f"正在提取 {fname} 的内容..."):
                content = extract_content(file)
                if content:
                    st.session_state.file_contents[fname] = content
                    # 初始化聊天记录，加入系统级摘要作为第一条 AI 消息
                    st.session_state.chat_histories[fname] = []
                    st.success(f"{fname} 提取成功！")
                else:
                    st.error(f"{fname} 内容提取失败，请检查文件格式。")

# ─────────────────────────────────────────────
# 为每个已处理的文件生成独立聊天标签页
# ─────────────────────────────────────────────
if st.session_state.file_contents:
    file_names = list(st.session_state.file_contents.keys())
    tabs = st.tabs(file_names)  # 每个文件一个 tab

    for i, tab in enumerate(tabs):
        fname = file_names[i]
        content = st.session_state.file_contents[fname]
        history = st.session_state.chat_histories[fname]

        with tab:
            st.markdown(f"**文件：{fname}**")
            st.divider()

            # ── 显示历史对话 ──────────────────────────────────
            for msg in history:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        st.write(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg["content"])

            # ── 用户输入框（每个 tab 独立）────────────────────
            # 用 key 区分不同 tab 的输入框
            user_input = st.chat_input(
                placeholder="请输入你的问题...",
                key=f"chat_input_{fname}"
            )

            if user_input:
                # 把用户消息追加进历史
                history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.write(user_input)

                # 构建发送给 LLM 的完整消息列表
                # SystemMessage 包含文档内容作为背景知识
                messages = [
                    SystemMessage(content=(
                        f"你是一位专业的学习助手，擅长分析学科知识点。\n"
                        f"以下是用户上传的文档内容，请基于这份文档回答用户的所有问题：\n\n"
                        f"【文档内容】\n{content}\n\n"
                        f"请用中文回答，回答要清晰、结构化。"
                    ))
                ]

                # 将历史对话也一并带入，实现多轮对话记忆
                for msg in history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    else:
                        messages.append(AIMessage(content=msg["content"]))

                # 调用 AI
                with st.chat_message("assistant"):
                    with st.spinner("AI 思考中..."):
                        try:
                            response = llm.invoke(messages)
                            reply = response.content
                            st.write(reply)
                            # 把 AI 回复追加进历史，保持记忆
                            history.append({"role": "assistant", "content": reply})
                            # 写回 session_state
                            st.session_state.chat_histories[fname] = history
                        except Exception as e:
                            st.error(f"API 调用失败: {str(e)}")

            # ── 清空对话按钮 ──────────────────────────────────
            if history:
                if st.button("清空对话记录", key=f"clear_{fname}"):
                    st.session_state.chat_histories[fname] = []
                    st.rerun()

else:
    st.info("请先上传至少一个 .pptx 或 .pdf 文件以开始对话。")



