import streamlit as st
from pptx import Presentation
import io

st.title("Finance PPT AI Analyst")

# 1. 添加文件上传组件
uploaded_file = st.file_uploader("请上传您的财务 PPT 文件", type=["pptx"])

def extract_text_from_pptx(file):
    """从 PPTX 中提取所有文本"""
    prs = Presentation(file)
    full_text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                full_text.append(shape.text)
    return "\n".join(full_text)

# 2. 修改逻辑，先检查文件是否上传
if uploaded_file is not None:
    st.success("文件上传成功！正在处理中...")
    
    # 提取文本
    ppt_content = extract_text_from_pptx(uploaded_file)
    
    # 这里你可以将 ppt_content 发送给 AI
    st.write("已提取的 PPT 内容预览 (前 500 字):")
    st.text(ppt_content[:500])

    # 3. 如果需要针对性提问，添加聊天窗口
    st.subheader("针对该 PPT 提问")
    question = st.text_input("请输入你想了解的问题：")
    
    if st.button("开始分析并回答"):
        if question:
            # 此处调用你的 AI 模型 (如 OpenAI 或 LangChain)
            st.write(f"正在基于 PPT 内容分析问题: '{question}'...")
            # st.write(ai_response) # 你的 AI 回答逻辑
        else:
            st.warning("请输入问题后再点击分析。")
else:
    st.info("请在上方上传一个财务 PPT 文件以开始分析。")
