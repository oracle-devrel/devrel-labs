#!/bin/bash

podman stop airagdb23aiinbox
podman stop 23aidb

podman rm airagdb23aiinbox
podman rm 23aidb

# Delete all Images
podman system prune --all --force && podman rmi --all --force

# Delete Network
podman network rm airag

# Stop podman Machine
podman machine stop
podman machine reset

# Uninstall podman
brew uninstall podman
