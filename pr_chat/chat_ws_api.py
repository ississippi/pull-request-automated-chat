# chat_ws_api.py
import os
import json
import redis
import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain.memory.chat_message_histories import RedisChatMessageHistory

# FastAPI app
app = FastAPI()

# Parameter Store (SSM) for API key
ssm = boto3.client('ssm', region_name='us-east-1')
ANTHROPIC_API_KEY = ssm.get_parameter(
    Name="/prreview/ANTHROPIC_API_KEY",
    WithDecryption=True
)['Parameter']['Value']
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Claude setup
llm = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0.7)

# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You're a helpful assistant."),
    ("human", "{input}")
])

# Redis config
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", "6379"))

# Chain with memory
def get_history(session_id: str):
    return RedisChatMessageHistory(session_id=session_id, url=f"redis://{redis_host}:{redis_port}")

chat_chain = RunnableWithMessageHistory(
    prompt | llm | StrOutputParser(),
    get_session_history=get_history,
    input_messages_key="input",
    history_messages_key="messages"
)

# WebSocket chat endpoint
@app.websocket("/ws/chat/{user_id}/{session_id}")
async def websocket_chat(websocket: WebSocket, user_id: str, session_id: str):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            print(f"Received message from {user_id}/{session_id}: {message}")

            response = chat_chain.invoke(
                {"input": message},
                config={"configurable": {"session_id": session_id}}
            )

            await websocket.send_text(response)

    except WebSocketDisconnect:
        print(f"Client disconnected: {user_id}/{session_id}")

# Serve static chat client
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")
