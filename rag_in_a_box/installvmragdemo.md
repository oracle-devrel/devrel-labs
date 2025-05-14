# AI RAG Demo for Beginners Hands-On Lab

AI RAG Demo with Cohere and Oracle Generative AI 

## Prerequisites

You'll need an OCI free trial account (<a href="https://signup.cloud.oracle.com/?sourceType=_ref_coc-asset-opcSignIn&language=en_US" target="_blank" title="Sign up for free trial">click here to sign up</a>). We're going to use a ready-to-go image to install the required resources, so all you need to start is a free account.

Registered lab participants should have received $300 in credits to use for AI RAG VM operations.

### SSH Key

You'll also need an SSH key pair to access the OCI Stack we're going to create.
- For Mac/Linux systems, you can [use `ssh-keygen`](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/managingkeypairs.htm#ariaid-title4).
- On Windows, you'll [use PuTTY Key Generator](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/managingkeypairs.htm#ariaid-title5). 

To summarize, for Mac/Linux, you can use the following command:

    ```bash
    ssh-keygen -t rsa -N "" -b 2048 -C "<key_name>" -f <path/root_name> 
    ```

For Windows, and step-by-step instructions for Mac/Linux, please see the [Oracle Docs on Managing Key Pairs](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/managingkeypairs.htm#Managing_Key_Pairs_on_Linux_Instances).

## Getting Started

1. Click the button below to begin the deploy of the AI RAG Demo stack and custom image:

    [![Deploy to Oracle Cloud](https://oci-resourcemanager-plugin.plugins.oci.oraclecloud.com/latest/deploy-to-oracle-cloud.svg)](https://cloud.oracle.com/resourcemanager/stacks/create?zipUrl=https://github.com/operard/airagdemo/releases/download/v1.0.0/demoai.zip)

2. If needed, log into your account. You should then be presented with the **Create Stack** page. 
    
    These next few steps will deploy a stack to your OCI tenancy. This will include a Compute instance and the necessary tools to deploy and run the AI RAG Demo from within your OCI account.

    Under *Stack Information* (the first screen), check the box *I have reviewed and accept the Oracle Terms of Use*. Once that box is checked, the information for the stack will be populated automatically.
    
3. See the video.

## Starting The Web Application

To see the results of the lab, you'll need to start the web server using Google Chrome, Safari or Firefox.

1. In the menu at the top of the page, select **your browser**.
2. Open a web browser to the public IP of your Chatbot RAG Demo AI, but use port 8501:

    ```bash
    http://xxx.xxx.xxx.xxx:8501
    ```

    The Public IP is the one at which you're currently accessing the AI RAG Demo.