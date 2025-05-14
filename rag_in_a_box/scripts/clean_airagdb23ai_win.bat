@echo off
rem *************************************************************************************************
rem   usage:
rem      clean_airagdb23ai_win.bat 
rem
rem   2024/09/30 olivier.perard@oracle.com
rem *************************************************************************************************

set "AIRAG_BUILD_ARGS_LIST=%*"
call :EnvSetting
call :Clean_Containers
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

:Clean_Containers
  podman stop airagdb23aiinbox
  podman stop 23aidb

  podman rm airagdb23aiinbox
  podman rm 23aidb
  echo "--> All containers deleted"

  REM Delete all Images
  podman system prune --all --force && podman rmi --all --force
  echo "--> All images deleted"

  REM Delete Network
  podman network rm airag
  echo "--> Network deleted"
goto :EOF

:ErrorReturn
  endlocal
exit /b 2

:End
  endlocal
exit /b %ReturnCode%
