import os

from autogen import ConversableAgent

from langchain_ollama.llms import OllamaLLM
from prefect_data_getters.stores.rag_man import MultiSourceSearcher
import asyncio
llm_config = {
    "config_list": [{
        "model": "llama3.1:8b",
        "api_type": "ollama",
        # "num_predict": -1,
        # # "repeat_penalty": 1.1,
        # # "seed": 42,
        "cache_seed": None,  # if set it will allow for cached messages without call to llm
        # "stream": False,
        # "temperature": 0.5, 
        "client_host": "http://127.0.0.1:11434",
        # # "top_k": 50,
        # # "top_p": 0.8,
        # "native_tool_calls": True,
        # "num_ctx": 127000
        },]
    }
# llm = OllamaLLM(model="llama3.2")
student_agent = ConversableAgent(
    name="Student_Agent",
    system_message="You are a student willing to learn. Reply with the word TERMINATE when you have answered the original question. reply with only the word TERMINATE",
    llm_config=llm_config,
    is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
)
teacher_agent = ConversableAgent(
    name="Teacher_Agent",
    system_message="You are a math teacher.",
    llm_config=llm_config,
    is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),

)

chat_result = student_agent.initiate_chat(
    teacher_agent,
    message="What is triangle inequality?",
    summary_method="reflection_with_llm",
    max_turns=10,
    
)
i=0