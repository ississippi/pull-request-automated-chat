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

The Automated Pull Request Reviewer Bot leverages Large Language Models (LLMs) to  automate the review of pull requests (PRs) . The purpose is to  enhance the efficiency and accuracy of code reviews by providing detailed feedback,  identifying potential issues, and suggesting improvements to streamline the code review process.

**See /CloudFormation for all CF templates for this project.**  
** See /docs/Deployments.docx for notes on build and deployments of all related components including CF for the infrastructure.**  
** See pull-request-automated-review/docs for all project documentation.

** Repos included as part of this project: **  
pull-request-automated-review: Main project repo. Code review orchestration and github integration. Lamdas.  
pull-request-automated-chat: Chat conversation inteface. Python running in ECS.  
pull-request-automated-notifications. Push PR service. C# running in ECS.  
pull-request-automated-git-provider. Not implemented. REST API for git services. This functionality currently part of pull-request-automated-review.  
pull-request-automated-experiments: project for prototyping API interfaces.  
pull-request-test-repo: Early repo used to create PRs for testing.   



