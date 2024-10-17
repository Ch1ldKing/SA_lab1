import streamlit as st
from langchain_community.chat_models import ChatZhipuAI
import uuid
import socket
import json
import redis
import os
from dotenv import load_dotenv

load_dotenv()
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
                    "messages": json.loads(convo.get(b"messages", b"[]").decode()),
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
        client.sendall("PUBLISHER\n".encode())
        # Send the message as JSON string
        client.sendall((json.dumps(message)+'\n').encode())
        client.close()
        print("Published message to Message Broker.")
    except Exception as e:
        st.error(f"Error publishing message: {e}")

def page_control(conversation_id):
    if conversation_id:
        # 从 Redis 获取对话
        try:
            redis_key = f"conversation:{conversation_id}"
            convo = redis_client.hgetall(redis_key)
            user_query = convo.get(b"user_query", b"").decode()
            ai_response = convo.get(b"ai_response", b"").decode()
            return user_query, ai_response
        except Exception as e:
            st.error(f"Error fetching conversation: {e}")
            st.session_state.logs.append(f"Error fetching conversation: {e}")
    else:
        st.session_state.conversation_id = str(uuid.uuid4())
        return None, None

st.title("AI 问答系统")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "logs" not in st.session_state:
    st.session_state.logs = []

# 侧边栏显示历史对话
st.sidebar.header("历史对话")

history = get_history()
for convo in history:
    if st.sidebar.button(f"对话 {convo['conversation_id']}", key=convo['conversation_id'],use_container_width=True):
        st.session_state.conversation_id = convo['conversation_id']
        st.session_state.messages = []
        for messages in convo['messages']:
            st.session_state.messages.append(messages)

if st.sidebar.button("新建对话", use_container_width=True):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []

for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message(message["role"], avatar="☺️"):
            st.markdown(message["content"])
    else:
        with st.chat_message(message["role"], avatar="🤖"):
            st.markdown(message["content"])

if prompt := st.chat_input("输入你的问题"):
    with st.chat_message("user", avatar="☺️"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    try:
        response = llm.invoke(prompt)
    except Exception as e:
        st.error(f"AI 生成响应失败: {e}")
        
    with st.chat_message('assistant', avatar='🤖'):
        st.markdown(response.content)
    st.session_state.messages.append({'role': 'assistant', 'content': response.content})

# # 用户输入
# user_input = st.text_input(f"{st.session_state.conversation_id}", "")

# if st.button("发送") and user_input:
#     # 生成唯一的 conversation_id
#     conversation_id = str(uuid.uuid4())

#     # 调用 LLM 获取响应
#     try:
#         response = llm.invoke(user_input)
#     except Exception as e:
#         st.error(f"AI 生成响应失败: {e}")
#         response = "抱歉，我无法生成响应。"
#     content = response.content
#     # 显示 AI 响应
#     st.write("**AI**:", content)

    # 计算 token 使用量（示例，需根据实际情况调整）
    tokens_used = int(response.response_metadata['token_usage']['total_tokens'])

    #TODO 消息追加的时候出现重复
    # 创建消息
    conversation = {
        "conversation_id": st.session_state.conversation_id,
        "messages": st.session_state.messages,
        "tokens_used": tokens_used,
        "logs":st.session_state.logs
    }

    # 发布消息到中间件
    publish_message(conversation)

    # # 更新 Redis 立即显示
    # try:
    #     redis_key = f"conversation:{conversation_id}"
    #     redis_client.hmset(
    #         redis_key, {"user_query": user_input, "ai_response": content}
    #     )
    # except Exception as e:
    #     st.error(f"Error updating history: {e}")
