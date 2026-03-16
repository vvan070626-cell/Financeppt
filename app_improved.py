import streamlit as st
from pptx import Presentation
from pypdf import PdfReader
import io

st.title("Finance Document AI Analyst")

# 1. 修改上传组件，支持 pptx 和 pdf
uploaded_file = st.file_uploader("请上传您的财务文件 (PPTX 或 PDF)", type=["pptx", "pdf"])

def extract_text_from_pptx(file):
    prs = Presentation(file)
    full_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                full_text.append(shape.text)
    return "\n".join(full_text)

def extract_text_from_pdf(file):
    reader = PdfReader(file)
    full_text = []
    for page in reader.pages:
        full_text.append(page.extract_text())
    return "\n".join(full_text)

# 2. 修改逻辑，根据后缀名处理
if uploaded_file is not None:
    st.success(f"已上传: {uploaded_file.name}")
    
    # 根据文件类型选择解析函数
    if uploaded_file.name.endswith('.pptx'):
        content = extract_text_from_pptx(uploaded_file)
    elif uploaded_file.name.endswith('.pdf'):
        content = extract_text_from_pdf(uploaded_file)
    else:
        content = "不支持的文件格式"
    
    st.write("文件内容提取预览:")
    st.text(content[:500] + "...")

    # 3. 针对该内容的提问
    st.subheader("针对该文档提问")
    question = st.text_input("请输入你想了解的问题：")
    
    if st.button("开始分析"):
        if question:
            st.write(f"正在分析文件内容...")
            # 在此处集成你的 LLM 分析逻辑
        else:
            st.warning("请输入问题后再点击分析。")
else:
    st.info("请上传财务文档以开始分析。")

