import streamlit as st
from langchain_community.chat_models import ChatZhipuAI
import uuid
import socket
import json
import redis
import os

# Redis 客户端配置（用于即时更新历史）
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# LangChain LLM 初始化
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

# LangChain LLM 初始化
llm = ChatZhipuAI(
    api_key=ZHIPU_API_KEY,
    temperature=0.5,
    model="glm-4-flash",
)


def get_history():
    try:
        keys = redis_client.keys("conversation:*")
        history = []
        for key in keys:
            convo = redis_client.hgetall(key)
            history.append(
                {
                    "conversation_id": key.decode().split(":")[1],
                    "user_query": convo.get(b"user_query", b"").decode(),
                    "ai_response": convo.get(b"ai_response", b"").decode(),
                }
            )
        # 按时间排序或其他逻辑
        return history
    except Exception as e:
        st.sidebar.error(f"Error fetching history: {e}")
        return []


def publish_message(message, host="localhost", port=9999):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        client.sendall("PUBLISHER".encode())
        # Send the message as JSON string
        client.sendall(json.dumps(message).encode())
        client.close()
    except Exception as e:
        st.error(f"Error publishing message: {e}")


st.title("AI 问答系统")

# 侧边栏显示历史对话
st.sidebar.header("历史对话")
history = get_history()
for convo in history:
    with st.sidebar.expander(f"对话 {convo['conversation_id']}"):
        st.write(f"**用户**: {convo['user_query']}")
        st.write(f"**AI**: {convo['ai_response']}")

# 用户输入
user_input = st.text_input("请输入您的问题：", "")

if st.button("发送") and user_input:
    # 生成唯一的 conversation_id
    conversation_id = str(uuid.uuid4())

    # 调用 LLM 获取响应
    try:
        response = llm.invoke(user_input)
    except Exception as e:
        st.error(f"AI 生成响应失败: {e}")
        response = "抱歉，我无法生成响应。"
    content = response.content
    # 显示 AI 响应
    st.write("**AI**:", content)

    # 计算 token 使用量（示例，需根据实际情况调整）
    tokens_used = int(response.response_metadata['token_usage']['total_tokens'])

    # 创建消息
    message = {
        "conversation_id": conversation_id,
        "user_query": user_input,
        "ai_response": content,
        "tokens_used": tokens_used,
    }

    # 发布消息到中间件
    publish_message(message)

    # 更新 Redis 立即显示
    try:
        redis_key = f"conversation:{conversation_id}"
        redis_client.hmset(
            redis_key, {"user_query": user_input, "ai_response": content}
        )
    except Exception as e:
        st.error(f"Error updating history: {e}")
