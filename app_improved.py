import streamlit as st
from pptx import Presentation
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 1. 页面配置
st.title("Document AI Analyst")

# 2. 从 Secrets 读取 API Key (请在 Streamlit Dashboard 设置)
api_key = st.secrets["DEEPSEEK_API_KEY"]

# 3. 初始化 LLM 模型 (使用 DeepSeek)
# 确保 base_url 和 api_key 参数传递正确
llm = ChatOpenAI(
    model="deepseek-chat", 
    openai_api_key=api_key,       # 这里显式指定参数名
    openai_api_base="https://api.deepseek.com", # 部分旧版本或特定环境使用这个参数
    base_url="https://api.deepseek.com",        # 新版本使用这个
    max_retries=2
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
                SystemMessage(content="你是一位通用的学习助力，擅长识别学科关键知识点并把它们整理成一条线，然后分析解释知识点。"),
                HumanMessage(content=f"文档内容：{content}\n\n问题：{question}")
            ]
            try:
                    response = llm.invoke(messages)
                    st.markdown("### 分析结果：")
                    st.write(response.content)
                except Exception as e:
                    # 这会把原本隐藏的详细错误打印在页面上，帮你定位到底是余额不足还是 Key 错误
                    st.error(f"API 调用失败: {str(e)}")
 


