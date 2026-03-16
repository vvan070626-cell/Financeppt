import streamlit as st
from pptx import Presentation
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# 1. 页面配置
st.title("Document AI Analyst")

# 2. 从 Secrets 读取 API Key (请在 Streamlit Dashboard 设置)
api_key = st.secrets["DEEPSEEK_API_KEY"]

# 3. 初始化 LLM 模型 (使用 DeepSeek)
llm = ChatOpenAI(
    model="deepseek-chat", 
    api_key=api_key, 
    base_url="https://api.deepseek.com"
)

# 4. 定义提取函数
def extract_text_from_pptx(file):
    prs = Presentation(file)
    return "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    return "\n".join([page.extract_text() for page in reader.pages])

# 5. 主逻辑
uploaded_file = st.file_uploader("请上传您的文件 (PPTX 或 PDF)", type=["pptx", "pdf"])

if uploaded_file:
    content = extract_text_from_pptx(uploaded_file) if uploaded_file.name.endswith('.pptx') else extract_text_from_pdf(uploaded_file)
    st.write("文件内容提取预览 (前 500 字):")
    st.text(content[:500] + "...")

    question = st.text_input("请输入你想了解的问题：")
    if st.button("开始 AI 分析"):
        with st.spinner("AI 正在分析中..."):
            messages = [
                SystemMessage(content="你是一位专业分析师。"),
                HumanMessage(content=f"文档内容：{content}\n\n问题：{question}")
            ]
            response = llm.invoke(messages)
            st.markdown("### 分析结果：")
            st.write(response.content)


