#!/bin/bash


if [ "$1" = "start" ];
then
  podman machine start
  podman start 23aidb
  podman start airagdb23aiinbox
  echo "airagdb23aiinbox started ..."
elif [ "$1" = "stop" ];
then
  podman stop airagdb23aiinbox
  podman stop 23aidb
  podman machine stop
  echo "airagdb23aiinbox stopped ..."
else
  echo "Command not valid: Use start or stop ..."
fi
