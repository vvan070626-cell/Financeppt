import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pptx import Presentation
import fitz  # PyMuPDF
import io

# 页面配置
st.set_page_config(page_title="AI 学习助手", layout="wide")

# 初始化 LLM
api_key = st.secrets["DEEPSEEK_API_KEY"]
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=api_key,
    base_url="https://api.deepseek.com",
    max_retries=2
)

# 文本提取函数
def extract_pptx(file_bytes):
    prs = Presentation(io.BytesIO(file_bytes))
    texts = [shape.text_frame.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame]
    return "\n".join(texts)

def extract_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join([page.get_text() for page in doc])

# 状态初始化
if "chat_histories" not in st.session_state: st.session_state.chat_histories = {}
if "file_contents" not in st.session_state: st.session_state.file_contents = {}
if "active_file" not in st.session_state: st.session_state.active_file = None

# --- 侧边栏：对话目录 ---
with st.sidebar:
    st.title("📂 对话目录")
    uploaded_files = st.file_uploader("上传 PPT/PDF", type=["pptx", "pdf"], accept_multiple_files=True)
    
    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state.file_contents:
                with st.spinner(f"正在分析 {file.name}..."):
                    content = extract_pptx(file.read()) if file.name.endswith(".pptx") else extract_pdf(file.read())
                    st.session_state.file_contents[file.name] = content
                    st.session_state.chat_histories[file.name] = []
        
        st.divider()
        st.subheader("历史对话")
        for fname in st.session_state.file_contents.keys():
            if st.button(fname, use_container_width=True):
                st.session_state.active_file = fname

# --- 主区域：聊天窗口 ---
if st.session_state.active_file:
    fname = st.session_state.active_file
    st.header(f"💬 当前对话: {fname}")
    
    # 显示历史记录
    for msg in st.session_state.chat_histories[fname]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # 用户输入
    if prompt := st.chat_input("输入问题..."):
        st.session_state.chat_histories[fname].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # 调用 AI
        with st.chat_message("assistant"):
            messages = [SystemMessage(content=f"基于文档回答：{st.session_state.file_contents[fname]}")]
            messages += [HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"]) 
                         for m in st.session_state.chat_histories[fname]]
            
            with st.spinner("思考中..."):
                try:
                    response = llm.invoke(messages).content
                    st.write(response)
                    st.session_state.chat_histories[fname].append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"发生错误: {e}")
    
    if st.button("清空当前对话"):
        st.session_state.chat_histories[fname] = []
        st.rerun()
else:
    st.info("请从左侧栏上传文件或选择一个已有的文件开始对话。")




