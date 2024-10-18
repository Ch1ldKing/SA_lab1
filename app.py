import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
import uuid
import json
import redis
import os
import time
import requests  # 使用 requests 代替 socket
from dotenv import load_dotenv
from chain import build_app, generate, generate_title

load_dotenv()

# Redis 客户端配置（用于即时更新历史）
redis_client = redis.Redis(host="localhost", port=6379, db=0)

def get_history():
    """获取 Redis 中存储的对话历史。"""
    try:
        keys = redis_client.keys("conversation:*")
        history = []
        for key in keys:
            convo = redis_client.hgetall(key)
            history.append(
                {
                    "conversation_id": key.decode().split(":")[1],
                    "messages": json.loads(convo.get(b"messages", b"[]").decode()),
                    "title": convo.get(b"title", b"").decode()
                }
            )
        return history
    except Exception as e:
        st.sidebar.error(f"Error fetching history: {e}")
        return []

def publish_message(platform, message):
    """通过 HTTP 请求将消息发布到 Broker。"""
    url = "http://localhost:9999/publish"
    payload = {
        "platform": platform,
        "message": message
    }

    print(payload)
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Published message to {platform}")
        else:
            st.error(f"Failed to publish message: {response.json()}")
    except Exception as e:
        st.error(f"Error publishing message: {e}")

# 初始化 Streamlit 界面
st.title("AI 问答系统")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "logs" not in st.session_state:
    st.session_state.logs = []
if "title" not in st.session_state:
    st.session_state.title = ""
# 侧边栏显示历史对话
st.sidebar.header("历史对话")

history = get_history()
for convo in history:
    if st.sidebar.button(f"{convo['title']}", key=convo['conversation_id'], use_container_width=True):
        st.session_state.conversation_id = convo['conversation_id']
        st.session_state.messages = convo['messages']
        st.session_state.title = convo['title']

if st.sidebar.button("新建对话", use_container_width=True):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.title = ""

messages_history = []

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message(message["role"], avatar="☺️"):
            st.markdown(message["content"])
            messages_history.append(HumanMessage(message["content"]))
    else:
        with st.chat_message(message["role"], avatar="🤖"):
            st.markdown(message["content"])
            messages_history.append(AIMessage(message["content"]))

if prompt := st.chat_input("输入你的问题"):
    with st.chat_message("user", avatar="☺️"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        app = build_app()
        response = generate(app, st.session_state.conversation_id, messages_history, prompt)


    except Exception as e:
        st.error(f"AI 生成响应失败: {e}")

    with st.chat_message('assistant', avatar='🤖'):
        st.markdown(response['answer'])
    st.session_state.messages.append({'role': 'assistant', 'content': response['answer']})

    # 计算 token 使用量（示例，需根据实际情况调整）
    tokens_used = int(response['metadata']['token_usage']['total_tokens'])

    if st.session_state.title == "":
        st.session_state.title = generate_title(st.session_state.messages)

    # 创建消息
    conversation = {
        "conversation_id": st.session_state.conversation_id,
        "messages": st.session_state.messages,
        "tokens_used": tokens_used,
        "logs": st.session_state.logs,
        "title": st.session_state.title
    }

    # 发布消息到中间件
    publish_message(platform="log", message=conversation)
    
    # 延迟五秒
    time.sleep(5)
    st.rerun()
