from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
from langchain_core.output_parsers.string import StrOutputParser
from typing import Sequence
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages
from typing import Dict, Any

class State(TypedDict):
    input: str
    chat_history: Annotated[Sequence[BaseMessage], add_messages]
    answer: str
    metadata: Dict[str, Any]

load_dotenv()
ZHIPU_API_KEY = os.getenv("SECRET_KEY")

llm = ChatZhipuAI(
    api_key=ZHIPU_API_KEY,
    temperature=0.5,
    model="glm-4-flash",
)
def build_app():
    system_prompt = "你是一个为了软件架构而生的AI助手，辅助进行软件架构设计，你的名字是HIT软件架构小助手"
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    chain = prompt | llm

    def call_model(state: State):
        # print("state", state)
        response = chain.invoke(state)
        return {
            "chat_history": [
                HumanMessage(state["input"]),
                AIMessage(response.content),
            ],
            "answer": response.content,
            "metadata": response.response_metadata,
        }

    workflow = StateGraph(state_schema=State)
    workflow.add_edge(START, "llm")
    workflow.add_node("llm", call_model)
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app

def generate(app, conversation_id, messages_history, input):
    config = {"configurable": {"thread_id": conversation_id}}
    # print(config)
    response = app.invoke(
        {"input": input, "chat_history": messages_history},
        config=config
    )
    # print("response", response)
    return response

def generate_title(chat_history):
    parser = StrOutputParser()
    title_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "把以下对话总结为一个简短标题"),
            ("human", "{input}"),
        ]
    )
    chain = title_prompt | llm | parser
    response = chain.invoke({"input": chat_history})
    print(response)
    return response
