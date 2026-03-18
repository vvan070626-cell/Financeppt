import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pptx import Presentation
import fitz  # PyMuPDF
import io
import sqlite3
from datetime import datetime
import threading

# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI 学习助手",
    page_icon="🤖",
    layout="wide"
)

# ─────────────────────────────────────────────
# 全局锁
db_lock = threading.Lock()

# ─────────────────────────────────────────────
# 初始化 LLM
# ─────────────────────────────────────────────
@st.cache_resource
def init_llm():
    api_key = st.secrets["DEEPSEEK_API_KEY"]
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=api_key,
        base_url="https://api.deepseek.com",
        max_retries=3,
        temperature=0.1
    )

llm = init_llm()

# ─────────────────────────────────────────────
# 文本提取函数（✅ 修复：单\n）
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
    return "\n".join(texts)  # ✅ 修复

def extract_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join([page.get_text() for page in doc])  # ✅ 修复

def extract_content(uploaded_file):
    file_bytes = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pptx"):
        return extract_pptx(file_bytes)
    elif name.endswith(".pdf"):
        return extract_pdf(file_bytes)
    return None

# ─────────────────────────────────────────────
# SQLite 工具函数
# ─────────────────────────────────────────────
DB_PATH = "ai_study_assistant.sqlite3"

def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def db_init():
    with db_lock:
        con = db_conn()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS files (
                filename   TEXT PRIMARY KEY,
                content    TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                filename   TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        con.commit()
        con.close()

def db_upsert_file(filename: str, content: str):
    with db_lock:
        con = db_conn()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO files(filename, content, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                content=excluded.content,
                updated_at=excluded.updated_at
        """, (filename, content, datetime.utcnow().isoformat()))
        con.commit()
        con.close()

def db_add_message(filename: str, role: str, content: str):
    with db_lock:
        con = db_conn()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO messages(filename, role, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (filename, role, content, datetime.utcnow().isoformat()))
        con.commit()
        con.close()

def db_load_all():
    con = db_conn()
    cur = con.cursor()
    cur.execute("SELECT filename, content FROM files ORDER BY updated_at DESC")
    file_contents = {fn: ct for fn, ct in cur.fetchall()}

    chat_histories = {fn: [] for fn in file_contents.keys()}
    cur.execute("SELECT filename, role, content FROM messages ORDER BY id ASC")
    for fn, role, content in cur.fetchall():
        if fn in chat_histories:
            chat_histories[fn].append({"role": role, "content": content})
    con.close()
    return file_contents, chat_histories

def db_clear_chat(filename: str):
    with db_lock:
        con = db_conn()
        cur = con.cursor()
        cur.execute("DELETE FROM messages WHERE filename=?", (filename,))
        con.commit()
        con.close()

def db_delete_file(filename: str):
    with db_lock:
        con = db_conn()
        cur = con.cursor()
        cur.execute("DELETE FROM messages WHERE filename=?", (filename,))
        cur.execute("DELETE FROM files WHERE filename=?", (filename,))
        con.commit()
        con.close()

# ─────────────────────────────────────────────
# 初始化
# ─────────────────────────────────────────────
db_init()

if "file_contents" not in st.session_state:
    st.session_state.file_contents = {}
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {}

if not st.session_state.file_contents:
    fc, ch = db_load_all()
    st.session_state.file_contents = fc
    st.session_state.chat_histories = ch

# ─────────────────────────────────────────────
# 侧边栏：文件上传
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 AI 学习助手")
    st.caption("📄 上传PPT/PDF，Tab间**独立**对话")

    st.divider()

    uploaded_files = st.file_uploader(
        "上传文件（.pptx / .pdf）",
        type=["pptx", "pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            fname = file.name
            if fname not in st.session_state.file_contents:
                with st.spinner(f"提取 {fname}..."):
                    content = extract_content(file)
                    if content:
                        st.session_state.file_contents[fname] = content
                        st.session_state.chat_histories[fname] = []
                        db_upsert_file(fname, content)
                        st.success(f"✅ {fname} 就绪")

# ─────────────────────────────────────────────
# 主界面：多Tab独立聊天（✅ 去掉并发，去掉time.sleep）
# ─────────────────────────────────────────────
if st.session_state.file_contents:
    filenames = list(st.session_state.file_contents.keys())
    tabs = st.tabs(filenames)
    
    for tab, fname in zip(tabs, filenames):
        with tab:
            content = st.session_state.file_contents[fname]
            history = st.session_state.chat_histories.get(fname, [])
            
            # 标题+按钮
            col1, col2 = st.columns([6, 3])
            with col1:
                st.markdown(f"### 📄 {fname}")
                st.caption(f"💬 {len([m for m in history if m['role']=='user'])} 轮对话")
            with col2:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ 清空", key=f"clear_{fname}"):
                        db_clear_chat(fname)
                        st.session_state.chat_histories[fname] = []
                        st.rerun()
                with col_btn2:
                    if st.button("🗑️ 删除文件", key=f"del_{fname}"):
                        db_delete_file(fname)
                        del st.session_state.file_contents[fname]
                        if fname in st.session_state.chat_histories:
                            del st.session_state.chat_histories[fname]
                        st.rerun()
            
            st.divider()
            
            # 聊天历史
            chat_container = st.container(height=500)
            with chat_container:
                for msg in history:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
            
            # 输入框（✅ 同步处理，稳定）
            user_input = st.chat_input(f"💭 问 {fname} 相关问题...", key=f"input_{fname}")
            
            if user_input:
                # 保存用户消息
                user_msg = {"role": "user", "content": user_input}
                history.append(user_msg)
                db_add_message(fname, "user", user_input)
                
                # 显示用户消息
                with st.chat_message("user"):
                    st.write(user_input)
                
                # ✅ 同步调用AI（稳定，无线程问题）
                with st.chat_message("assistant"):
                    with st.spinner("🤔 AI 思考中..."):
                        try:
                            messages = [
                                SystemMessage(content=f"""你是一位专业的学习助手，擅长分析学科知识点。
以下是用户上传的文档内容，请基于这份文档回答用户的所有问题：
【文档内容】
{content}
请用中文回答，回答要清晰、结构化、专业。""")
                            ]
                            
                            # 添加历史对话
                            for msg in history:
                                if msg["role"] == "user":
                                    messages.append(HumanMessage(content=msg["content"]))
                                elif msg["role"] == "assistant":
                                    messages.append(AIMessage(content=msg["content"]))
                            
                            response = llm.invoke(messages)
                            reply = response.content
                            st.write(reply)
                            
                            # 保存AI回复
                            history.append({"role": "assistant", "content": reply})
                            db_add_message(fname, "assistant", reply)
                            st.session_state.chat_histories[fname] = history
                            
                        except Exception as e:
                            st.error(f"AI出错：{str(e)}")
                            history.append({"role": "assistant", "content": f"AI出错：{str(e)}"})
                            st.session_state.chat_histories[fname] = history
else:
    st.title("🤖 AI 学习助手")
    st.info("👈 从侧边栏上传 PPTX/PDF 开始多文档学习")
