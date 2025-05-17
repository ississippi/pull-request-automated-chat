# pull-request-automated-chat
Websockets client chat with LLM

client connection:
ws://<your-host>:8080/ws/chat/<user_id>/<session_id>

Local testing:
Use the test client for local testing:
1. Build: docker build -t chat-ws-app .
1. Start the container: 
    docker run -p 8080:8080 chat-ws-app
2. Open pull-request-automated-chat\test_client\chat_client.html from a browser.

