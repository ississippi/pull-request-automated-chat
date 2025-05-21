# chat_ws_api.py
import os
import json
import boto3
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
import traceback
import git_provider

class PatchedDynamoDBChatMessageHistory(DynamoDBChatMessageHistory):
    @property
    def key(self):
        return {"id": self.session_id}
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    repo: str
    pr_number: int

# FastAPI app
app = FastAPI()
llm = None
ANTHROPIC_API_KEY = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ANTHROPIC_API_KEY
    ssm = boto3.client('ssm', region_name='us-east-1')
    ANTHROPIC_API_KEY = ssm.get_parameter(
        Name="/prreview/ANTHROPIC_API_KEY",
        WithDecryption=True
    )['Parameter']['Value']
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    os.environ["AWS_REGION"] = "us-east-1"
    global llm
    llm = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0.7)

    yield  # app is now running

app = FastAPI(lifespan=lifespan)
session = boto3.Session(region_name="us-east-1")

# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You're a helpful assistant."),
    ("human", "{input}")
])

def get_pr_diffs(repo, pr_number):
    print(f"get_pr_diffs(): repo: {repo}, pr_number: {pr_number}")
    diffs = git_provider.get_supported_diffs(repo, pr_number)
    if diffs is None:
        return "Error fetching diffs."
    print("Fetched diffs successfully.")
    return diffs  

# DDB for chat history
def get_history(session_id: str):
    print(f"get_history(): Using session_id={session_id}")
    return DynamoDBChatMessageHistory(
        table_name="ChatMemory",
        session_id=session_id,
        key={"id": session_id}
    )

def get_chat_chain():
    if llm is None:
        raise RuntimeError("LLM not initialized yet")
    return RunnableWithMessageHistory(
        prompt | llm | StrOutputParser(),
        get_session_history=get_history,
        input_messages_key="input",
        history_messages_key="messages"
    )

def save_to_dynamodb(session_id: str, history: list):
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    table_name = "ChatMemory"
    for turn in history:
        ddb.put_item(
            TableName=table_name,
            Item={
                "session_id": {"S": session_id},
                "user": {"S": turn["user"]},
                "ai": {"S": turn["ai"]}
            }
        )

# WebSocket chat endpoint
@app.websocket("/ws/chat/{user_id}/{session_id}")
async def websocket_chat(websocket: WebSocket, user_id: str, session_id: str):
    await websocket.accept()
    try:
        if ANTHROPIC_API_KEY is None:
            print("🔑 ANTHROPIC_API_KEY not set. Cannot connect to Claude.")
        else:
            print(f"🔑 ANTHROPIC_API_KEY length is: {len(ANTHROPIC_API_KEY)}. Connected to Claude.")
        while True:
            message = await websocket.receive_text()
            print(f"Received message from {user_id}/{session_id}")
            print(f"Message: {message}")
            chatMessage = json.loads(message)
            repo = chatMessage.get("repo")
            pr_number = chatMessage.get("pr_number")
            diffs = get_pr_diffs(repo, pr_number)

            # Augment the message with diffs
            augmented_message = f"PR DIFFS:\n{diffs}\n\nUser Message:\n{chatMessage.get('message')}"

            try:
                response = get_chat_chain().invoke(
                    {"input": augmented_message},
                    config={"configurable": {"session_id": session_id}},
                )
                await websocket.send_text(response)

            except Exception as e:
                print("🔥 LLM invocation failed:")
                traceback.print_exc()
                await websocket.send_text(f"[Server Error] {str(e)}")

    except WebSocketDisconnect:
        print(f"Client disconnected: {user_id}/{session_id}")

# Serve static chat client
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static", html=True), name="static")
