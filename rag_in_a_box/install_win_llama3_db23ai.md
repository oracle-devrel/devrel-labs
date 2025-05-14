# Podman Installation in Windows 

Here you can see the tutorial to install **Podman Desktop** in Windows.

## Steps

1. Podman Desktop Installation

    ![Step 1](./images/win_slide1.png)

2. Click on SETUP

    ![Step 2](./images/win_slide2.png)

3. Execute DISM

    ![Step 3](./images/win_slide3.png)

    ```bash
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    ```

4. Execute PODMAN Setup

    ![Step 4](./images/win_slide4.png)

5. Check if containers are running

    ![Step 5](./images/win_slide5.png)

6. PODMAN Setup in execution

    ![Step 6](./images/win_slide6.png)

7. Check PODMAN Setup 

    ![Step 7](./images/win_slide7.png)

8. Check PODMAN Installation.

    ![Step 9](./images/win_slide9.png)

9. Execute podman commands 

    ```bash
    # Check if containers are running
    podman ps

    # Check if images are downloaded
    podman images
    ```

10. Download the images from OCI Repository for x86:

    ```bash
    # Pull the images from OCI Repository
    podman pull container-registry.oracle.com/database/free:latest

    # Pull the images from OCI Repository
    podman pull fra.ocir.io/frg6v9xlrkul/airagdb23aiinbox:1.0.0.0.0
    ```

    ![Step 10](./images/win_slide10.png)

11. Check log of container installation.

    You can check the log during the DB23ai Container Installation:

    ```bash
    podman logs -f 23aidb
    ```

    ![Step 11](./images/win_slide11.png)

12. Check both containers

    After executing the BAT script, you could check in Podman Desktop the installation of the 2 containers:

    ![Step 12](./images/win_slide12.png)

13. Check both containers: after executing the BAT script, you could check in Podman Desktop the installation of the 2 containers:

    ![Step 13](./images/win_slide13.png)

