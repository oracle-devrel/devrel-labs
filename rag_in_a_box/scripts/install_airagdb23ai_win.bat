@echo off
rem *************************************************************************************************
rem   usage:
rem      install_airagdb23ai_win.bat 
rem
rem   2024/09/30 olivier.perarf@oracle.com
rem *************************************************************************************************

set "AIRAG_BUILD_ARGS_LIST=%*"
call :EnvSetting
call :Install_Container_Db23ai
call :Config_Network
call :Install_Db23ai
call :Install_Container_Airag
call :Config_Db23ai
call :Install_Airag
cd %WorkingDir%
goto :End

:EnvSetting
  if "%vArcType%" =="arm64"  (
    echo "The Windows is ARM64."
    set CONTAINERNAME="fra.ocir.io/frg6v9xlrkul/database:23.5.0-free-arm64"
    set CONTAINERAIRAG="fra.ocir.io/frg6v9xlrkul/airagdb23aiinbox:1.0.0-arm64"
  ) else (
    echo "The Windows is x86_64 or i386."
    set CONTAINERNAME="container-registry.oracle.com/database/free:latest"
    set CONTAINERAIRAG="fra.ocir.io/frg6v9xlrkul/airagdb23aiinbox:1.0.0.0.0"
  )
  echo vArcType is           %vArcType%
  echo vOSType  is           %vOSType%

  echo PATH is %PATH%
  echo LIB  is %LIB%
goto :EOF

:Install_Container_Db23ai
  podman pull %CONTAINERNAME%
  echo "--> DB23ai Downloaded"
goto :EOF

:Install_Container_Airag
  podman pull %CONTAINERAIRAG%
  echo "--> AIRAG Downloaded"
goto :EOF

:Config_Network
  podman network create --driver bridge --subnet 10.22.1.0/24 airag
goto :EOF

:Install_Db23ai
  podman run -d --name 23aidb --network airag --ip 10.22.1.12 -p 1522:1521 %CONTAINERNAME%
  echo "--> DB23ai Installed"
goto :EOF

:Config_Db23ai
  echo "--> configure DB23ai"
  REM podman logs -f 23aidb > ./23aidb.log 2>&1

  echo "Oracle Database 23ai started"

  podman exec 23aidb ./setPassword.sh "Oracle4U"

  (
  ALTER SESSION SET CONTAINER=FREEPDB1;
  CREATE USER VECDEMO IDENTIFIED BY "Oracle4U" DEFAULT TABLESPACE users TEMPORARY TABLESPACE temp QUOTA UNLIMITED ON users;
  GRANT CONNECT, RESOURCE TO VECDEMO;
  GRANT DB_DEVELOPER_ROLE to VECDEMO;
  EXIT
  ) > ./createuser.sql
  
  podman exec -it 23aidb sqlplus / as SYSDBA < ./createuser.sql

  (
  select * from dual;
  EXIT
  ) > ./checkconn.sql

  podman exec -it 23aidb sqlplus VECDEMO/Oracle4U@FREEPDB1 < ./checkconn.sql
  echo "--> DB23ai configured"
goto :EOF


:Install_Airag
  podman run -d --name airagdb23aiinbox --network airag --ip 10.22.1.11  -p 8501:8501  -e dbuser=VECDEMO -e dbpassword=Oracle4U -e dbservice="10.22.1.12:1521/FREEPDB1" -e dbtablename=AIRAGINBOX %CONTAINERAIRAG%
  echo "--> AIRAG executed"
goto :EOF

:ErrorReturn
  endlocal
exit /b 2

:End
  endlocal
exit /b %ReturnCode%
