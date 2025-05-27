# chat_api.py

from fastapi import FastAPI
from pydantic import BaseModel
import redis
import json
from langchain.chat_models import ChatAnthropic
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

app = FastAPI()

# Redis client (adjust host for production)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Claude setup
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0.7)

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str
    repo: str
    pr_number: int

@app.post("/chat/send")
async def chat_send(req: ChatRequest):
    print(f"Received request: {req}")
    session_key = f"chat:{req.session_id}"

    # Load existing conversation from Redis
    history_json = r.get(session_key)
    history = json.loads(history_json) if history_json else []

    if not any(turn.get("user") == "diffs" for turn in history):
        diffs = git_provider.get_supported_diffs(req.repo, req.pr_number)
        if diffs is None:
            return {"reply": "Error fetching diffs."}
        history.append({"user": "diffs", "ai": diffs})


    # Add diffs to the conversation
    history.append({"user": "diffs", "ai": diffs})
    # Load into LangChain memory
    memory = ConversationBufferMemory(return_messages=True)
    for turn in history:
        memory.chat_memory.add_user_message(turn["user"])
        memory.chat_memory.add_ai_message(turn["ai"])

    # Run the chain
    chain = ConversationChain(llm=llm, memory=memory)
    response = chain.run(req.message)

    # Save updated conversation
    history.append({"user": req.message, "ai": response})
    r.set(session_key, json.dumps(history), ex=3600)  # TTL 1 hour

    return {"reply": response}
