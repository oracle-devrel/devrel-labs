# Run Oracle Database 23ai Free on Mac computers with Apple silicon


But what about Oracle 23ai and the newer M1/M2/M3 ARM based Apple silicon Macs I hear you ask, so here you go.

See the following blog to understand the complexity [Here](https://ronekins.com/2024/07/02/run-oracle-database-23ai-free-on-mac-computers-with-apple-silicon/)

## Preinstallation

You need to install Rosetta2 if it is not already installed (Open Terminal in your MAC OSX Mx):

```bash
softwareupdate --install-rosetta
```

You should see the following result:

```bash
I have read and agree to the terms of the software license agreement. A list of Apple SLAs may be found here: https://www.apple.com/legal/sla/
Type A and press return to agree: A
2024-08-14 17:58:43.771 softwareupdate[67564:9084300] Package Authoring Error: 062-01890: Package reference com.apple.pkg.RosettaUpdateAuto is missing installKBytes attribute
Install of Rosetta 2 finished successfully
```

Start by installing the `Homebrew` package manager, if not already installed.

Now, install Colima container runtime and Docker if not already installed on your Mac.

```bash
# Check the version of Homebrew 
brew --version

# Install Colima container runtime and Docker
brew install colima docker
brew install docker-compose
brew reinstall qemu
```

You could see next results:

```bash
zsh completions have been installed to:
  /opt/homebrew/share/zsh/site-functions

To start colima now and restart at login:
  brew services start colima
Or, if you don't want/need a background service you can just run:
  /opt/homebrew/opt/colima/bin/colima start -f

```

Restart colima

```bash
# Restart colima
brew services restart colima
```

Check the installation:

```bash
# Check the version of Colima
colima --version
colima version 0.7.3

# Check the version of Docker
docker --version
Docker version 27.1.2, build d01f264bcc
```

If we now try `docker ps` to check for processes, we see a docker daemon error message:

```bash
docker ps

Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?
```

This happens because the Docker daemon is not running.

## Start Colima Container Runtime

If you want to deploy containers created in x86_64 architecture, we must start Colima Container Runtime like this: 

```bash
# Start Colima Container Runtime
colima start  --arch x86_64 --memory 8 --cpu 4
```

We can confirm the Colima Container Runtime configuration with colima status and colima list, for example.

```bash
# Check the status of Colima
colima status

# List the containers
colima list
```

Before we try and start any container, let’s check for Docker processes using docker ps.

We now no longer see the Docker daemon error message.

```bash
# Check for Docker processes
docker ps
```

We can check for existing docker images with docker images, for example.

```bash
# Check for existing docker images
docker images
```

The `docker context show` command should return `colima`, which means Docker runs under Colima and you can therefore use docker commands as usual.

```bash
# Check the docker context
docker context show
```

## Clean the colima and docker deployment in MAC OSX

If you must clean your environment in order to reset it, use the next commands:

```bash
# Stop Colima
colima stop
```

You should see the following result:

```bash
INFO[0000] stopping colima                              
INFO[0000] stopping ...                                  context=docker
INFO[0004] stopping ...                                  context=vm
INFO[0007] done                                         
```

```bash
# Delete Colima
colima delete
```

You should see the following result:

```bash
are you sure you want to delete colima and all settings? [y/N] y
INFO[0001] deleting colima                              
INFO[0002] done                                         
```
