# AI RAG in a BOX Demo using DB23ai

AI RAG in a BOX Demo using Internal LLM Engine could be deployed in PODMAN/DOCKER in your PC.


## AI RAG in a BOX Deployment Using LLAMA3 Engine in PODMAN

1. If you must install podman in your MAC OSX INTEL, Click the next link:

    [Deploy Podman in your MAC](./install_podman_macosx.md)

2. If you must deploy in your MAC OSX M1 some container with architecture x86_64, Click the next link:

    [Deploy container x86_64 in your MAC](./install_colima_docker_macosx.md)


3. Deploy Oracle DB23ai 


You must create an internal network:

```Code

docker network create --driver bridge --subnet 10.22.1.0/24 airag

```

Deploy the database

```Code

docker run -d --name 23aidb --network airag --ip 10.22.1.12 -p 1522:1521 \
container-registry.oracle.com/database/free:latest
```
 
Check when the database is deployed:

```Code
docker logs -f 23aidb
```


Configure your USER / PWD to access from AIRAGINBOX 

```Code

docker exec 23aidb ./setPassword.sh <pwd>

docker exec -it 23aidb sqlplus / as SYSDBA

ALTER SESSION SET CONTAINER=FREEPDB1;
CREATE USER VECDEMO IDENTIFIED BY "<pwd>" DEFAULT TABLESPACE users TEMPORARY TABLESPACE temp QUOTA UNLIMITED ON users;
GRANT CONNECT, RESOURCE TO VECDEMO;
GRANT DB_DEVELOPER_ROLE to VECDEMO;

```

Test Your Environment

```Code

docker exec -it 23aidb sqlplus VECDEMO/<pwd>@FREEPDB1
=> ok


docker exec -it 23aidb sqlplus PDBADMIN/<pwd>@FREEPDB1
=> ok
```





4. Deploy **AI RAG in a BOX Demo Docker** page. 
    
You must download the docker image in your podman in MAC OSX INTEL, use next command:

```Code

podman pull docker.io/operard/airagdb23aiinbox:1.0.0.0.0

```

If you must download the docker image in your docker with colima in MAC OSX Ma/M2/M3, use next command:

```Code

docker pull docker.io/operard/airagdb23aiinbox:1.0.0.0.0

```


## Executing The **AI RAG in a BOX Demo Docker** using internal LLM Engine like OLLAMA

You must create a directory "database", for example (/home/cloud-user/database) and create a file "config.env" with the database configuration:

```Code 
mkdir $HOME/database

vi $HOME/database/config.env

```



```Code

# this is the .env file 
[DATABASE]
USERNAME=VECDEMO
PASSWORD=<PWD>
HOST=10.22.1.12
PORT=1521
SERVICE_NAME=FREEPDB1
TABLE_NAME=AIRAGINBOX

```


You must execute the docker image in your podman or docker in order to use your OCI Config File like this:

In MAC OSX INTEL:

```Code

podman run -d --network airag --ip 10.22.1.11  -p 8501:8501 -p 11434:11434 -v $HOME/database:/config --name airagdb23aiinbox  docker.io/operard/airagdb23aiinbox:1.0.0.0.0

```

In MAC OSX M1/M2/M3:

```Code

docker run -d --network airag --ip 10.22.1.11  -p 8501:8501 -p 11434:11434 -v $HOME/database:/config --name airagdb23aiinbox  docker.io/operard/airagdb23aiinbox:1.0.0.0.0

```


Check when your AIRAGINBOX is ready:

```Code

docker logs -f airagdb23aiinbox  

```



## Starting The Web Application

To see the results of the container, you'll need to start the web server using your browser Google Chrome, Firefox or Safari.

1. In the menu at the top of the page, select **your browser**.
2. Open a web browser to localhost or the public IP of your AI RAG Demo, but use port 8501:

        http://localhost:8501 or http://<IP>:8501

    The Public IP is the one at which you're currently accessing Chatbot, which we copied from the Running Instances step above.

3. Check the tutorial

    [Tutorial](./tutorial_llama3.md)



## how to stop the containers 


Stop docker containers
```Code

docker stop airagdb23aiinbox

docker stop 23aidb

docker ps -a

```

Check

Stop colima

```Code

colima stop

```


## ReStarting the containers after a reboot of your pc

Start colima

```Code

colima start

```

check docker images

```Code

docker images

docker ps

docker ps -a

docker start 23aidb

docker logs -f 23aidb

docker start airagdb23aiinbox

```


