#!/bin/bash

# Comprobación si Homebrew está instalado
if [[ -f /usr/local/bin/brew || -f /opt/homebrew/bin/brew ]]; then
  echo "Homebrew is already installed. We can continue with installation of other softwares..."
else
  # Instalación de Homebrew
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

brew install podman

# Start podman Machine
podman machine init --cpus 4 --memory=4096
podman machine start

# Test podman
podman ps

# Install Images
#podman pull container-registry.oracle.com/database/free:latest
#podman pull docker.io/operard/database:23.5.0-free-arm64
CONTAINERNAME=""
CONTAINERAIRAG=""

# Install llama-cpp-python
# Comprobación del sistema operativo y arquitectura
if [[ "$(uname -m)" == "arm64" ]]; then
  echo "The Mac OSX is ARM (Apple Silicon)."
  CONTAINERNAME="fra.ocir.io/frg6v9xlrkul/database:23.5.0-free-arm64"
  CONTAINERAIRAG="fra.ocir.io/frg6v9xlrkul/airagdb23aiinbox:1.0.0-arm64"
else
  echo "The Mac OSX is x86_64."
  CONTAINERNAME="container-registry.oracle.com/database/free:latest"
  CONTAINERAIRAG="fra.ocir.io/frg6v9xlrkul/airagdb23aiinbox:1.0.0.0.0"
fi

podman pull $CONTAINERNAME
podman pull $CONTAINERAIRAG

podman network create --driver bridge --subnet 10.22.1.0/24 airag

podman run -d --name 23aidb --network airag --ip 10.22.1.12 -p 1522:1521 $CONTAINERNAME


podman logs 23aidb -f | while read LINE; 
do 
echo ${LINE}; 
echo "${LINE}" | grep -Fq 'ALTER DATABASE OPEN' && pkill -P $$; 
done; 

echo "Oracle Database 23ai started"

# Execute Script to update pwd
podman exec 23aidb ./setPassword.sh "Oracle4U"

# Execute Script to create user
podman exec -it 23aidb sqlplus / as SYSDBA <<EOF
ALTER SESSION SET CONTAINER=FREEPDB1;
CREATE USER VECDEMO IDENTIFIED BY "Oracle4U" DEFAULT TABLESPACE users TEMPORARY TABLESPACE temp QUOTA UNLIMITED ON users;
GRANT CONNECT, RESOURCE TO VECDEMO;
GRANT DB_DEVELOPER_ROLE to VECDEMO;
EXIT
EOF

# Execute Script to test new Vector User
podman exec -it 23aidb sqlplus VECDEMO/Oracle4U@FREEPDB1 <<EOF
select * from dual;
exit
EOF

#ENV llmmodel=llama3.2
#ENV ollamaurl=http://localhost:11434
#ENV embeddingname=intfloat/multilingual-e5-large

# Script to launch AIRAGBOX
podman run -d --name airagdb23aiinbox --network airag --ip 10.22.1.11  -p 8501:8501  -e dbuser=VECDEMO -e dbpassword=Oracle4U -e dbservice="10.22.1.12:1521/FREEPDB1" -e dbtablename=AIRAGINBOX $CONTAINERAIRAG

