# Deploy NVIDIA Holoscan on Oracle Linux A10 Instance

## Introduction
This Oracle Cloud Infrastructure (OCI) Terraform stack deploys an A10 (VM.GPU.A10.1) instance running Oracle Linux, installs NVIDIA Holoscan, and configures all required dependencies, including Docker and the NVIDIA container toolkit. The deployment occurs within an existing Virtual Cloud Network (VCN) and allows SSH access to the deployed VM for administration and troubleshooting. Additionally, a Jupyter Notebook service is set up to facilitate Holoscan usage.

## Getting Started
This code is created to run as a stack in the OCI Resource Manager(ORM). Upload the code as a folder or .zip file to the ORM to create a stack and configure the required parameters.

### Prerequisites
Before deploying, ensure you have the following:

1. **OCI Account**: A valid Oracle Cloud Infrastructure (OCI) account with access to GPU instances.
2. **NVIDIA NGC API Key**: Required to pull the Holoscan container image from NVIDIA's NGC Catalog. You can generate an API key by following the instructions in NVIDIA's documentation: [Generate Your NGC Keys](https://docs.nvidia.com/nemo/retriever/extraction/ngc-api-key/).
3. **SSH Key Pair**: A public SSH key for accessing the deployed instance.
4. **Existing VCN and Public Subnet**: The deployment requires an existing VCN and a public subnet in OCI.

### Required Inputs

The following variables are visible and need to be configured in the deployment UI of the OCI ORM:

| Parameter               | Description                                                           |
| ----------------------- | --------------------------------------------------------------------- |
| **Compartment OCID**    | OCI Compartment where the GPU VM will be deployed.                    |
| **VCN ID**              | ID of the Virtual Cloud Network where resources will be provisioned.  |
| **Subnet ID**           | The public subnet within the VCN for deployment.                      |
| **VM Display Name**     | Custom display name for the VM instance.                              |
| **SSH Public Key**      | Your public SSH key for remote access.                                |
| **Availability Domain** | The availability domain where the instance will be deployed.          |
| **NVIDIA API Key**      | Required to authenticate with NVIDIA NGC and pull the Holoscan image. |

## Notes/Issues

### Deployment Time
- The apply job itself will complete in a few minutes in the ORM, meaning the VM will be successfully created. The output will include both a public IP and a private IP. Nevertheless the depoyment is not complete at that time, because a *cloudinit.sh* script will run after that on the VM. Running the *cloudinit.sh* script **takes approximately 10 minutes**, as it includes pulling the Holoscan container image and setting up the environment. During this time, the **Jupyter Notebook link will not be immediately available**.

- To **monitor the progress** of the *cloudinit.sh* script, SSH into the VM and run:
    ```
    tail -f /var/log/cloud-init-output.log
    ```

### CloudInit Script Automation

The *cloudinit.sh* script does the following:

1. **Install required packages** (Docker, NVIDIA container toolkit, and Python dependencies).

2. **Configure Docker** to use NVIDIA's runtime.

3. **Authenticate to NVIDIA NGC** and pull the Holoscan container.

4. **Run the Holoscan container** with GPU support, mounting required volumes.

5. **Start a Jupyter Notebook service**, accessible on port **8888**, to facilitate interactive exploration of Holoscan.

6. **Configure firewall rules** to allow access to Jupyter Notebook.

## Jupyter Notebooks Folder

**Note:** The Jupyter notebooks folder is initially empty.

After the *cloudinit.sh* script completes, you can access the Jupyter Notebook by navigating to:
`http://<public_ip>:8888`

Once inside, browse to the `holoscan_jupyter_notebooks` directory to create and manage your notebooks.

For example notebooks and detailed guidance, refer to the official NVIDIA Holoscan documentation:
[Holoscan by Example](https://docs.nvidia.com/holoscan/sdk-user-guide/holoscan_by_example.html)

## URLs
[NVIDIA Holoscan](https://developer.nvidia.com/holoscan-sdk)
[Holoscan by Example](https://docs.nvidia.com/holoscan/sdk-user-guide/holoscan_by_example.html)


## Contributing
<!-- If your project has specific contribution requirements, update the
    CONTRIBUTING.md file to ensure those requirements are clearly explained. -->

This project welcomes contributions from the community. Before submitting a pull
request, please [review our contribution guide](./CONTRIBUTING.md).

## Security

Please consult the [security guide](./SECURITY.md) for our responsible security
vulnerability disclosure process.

## License
Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE.txt) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE.  FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.