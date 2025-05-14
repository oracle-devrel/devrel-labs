# AI RAG in a BOX Demo 

AI RAG in a BOX Demo using Internal LLM Engine could be deployed in PODMAN/DOCKER in your PC or OCI VM.


## AI RAG in a BOX Deployment Using LLAMA3 Engine in PODMAN

1. If you must install podman in your MAC OSX M1, Click the next link:

    [Deploy Podman in your MAC](./install_podman_macosx.md)

2. If you must deploy in your MAC OSX M1 some container with architecture x86_64, Click the next link:

    [Deploy container x86_64 in your MAC](./install_colima_docker_macosx.md)


3. Deploy **AI RAG in a BOX Demo Docker** page. 
    
You must download the docker image in your podman, use next command:

```Code

podman pull docker.io/operard/airaginbox:1.0.0.0.0

```

If you must download the docker image in your docker with colima, use next command:

```Code

docker pull docker.io/operard/airaginbox:1.0.0.0.0

```


## Executing The **AI RAG in a BOX Demo Docker** using internal LLM Engine like LLAMA3


You must execute the docker image in your podman or docker in order to use your OCI Config File like this:

```Code

podman run -d -p 8501:8501 -p 11434:11434  --name airaginbox docker.io/operard/airaginbox:1.0.0.0.0


or 

docker run -d -p 8501:8501 -p 11434:11434  --name airaginbox docker.io/operard/airaginbox:1.0.0.0.0

```


## Starting The Web Application

To see the results of the container, you'll need to start the web server using your browser Google Chrome, Firefox or Safari.

1. In the menu at the top of the page, select **your browser**.
2. Open a web browser to localhost or the public IP of your AI RAG Demo, but use port 8501:

        http://localhost:8501 or http://<IP>:8501

    The Public IP is the one at which you're currently accessing Chatbot, which we copied from the Running Instances step above.

3. Check the tutorial

    [Tutorial](./tutorial_llama3.md)

