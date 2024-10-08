from langchain_community.chat_models import ChatZhipuAI
import os
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
TEMPLATE="""
过去的聊天记录:
{chat_history}
对话：
{question}
你的回答：
"""
def build_chain(memory):

    ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

    # LangChain LLM 初始化
    llm = ChatZhipuAI(
        api_key=ZHIPU_API_KEY,
        temperature=0.5,
        model="glm-4-flash",
    )

    # prompt = ChatPromptTemplate(
    #     [
    #         MessagesPlaceholder(variable_name="chat_history"),
    #         HumanMessagePromptTemplate.from_template("{text}"),
    #     ]
    # )
    prompt = PromptTemplate.from_template(TEMPLATE)
    conversation = LLMChain(
        llm=llm,
        verbose=True,
        prompt=prompt,
        memory=memory,
    )

    return conversation


def generate_response(chain, input_text):
    response = chain.invoke(input_text)
    print(response)
    return response
