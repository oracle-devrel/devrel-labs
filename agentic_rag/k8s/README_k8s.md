# Kubernetes Deployment for Agentic RAG

This directory contains Kubernetes manifests for deploying the Agentic RAG system.

## Prerequisites

- Kubernetes cluster (e.g., Oracle Kubernetes Engine, Minikube, or any other Kubernetes cluster)
- `kubectl` configured to access your cluster
- At least 8GB of RAM and 4 CPU cores available for the deployment

## Deployment

This deployment includes both Hugging Face models and Ollama for inference. The Hugging Face token is optional but recommended for using Mistral models.

1. **Update the ConfigMap with your Hugging Face token** (optional but recommended):

   ```bash
   # Edit the configmap.yaml file
   nano local-deployment/configmap.yaml
   
   # Replace "your-huggingface-token" with your actual token
   ```

2. **Deploy the application**:

   ```bash
   kubectl apply -f local-deployment/configmap.yaml
   kubectl apply -f local-deployment/deployment.yaml
   kubectl apply -f local-deployment/service.yaml
   ```

3. **Access the application**:

   If using LoadBalancer:
   ```bash
   kubectl get service agentic-rag
   ```
   
   If using NodePort:
   ```bash
   # Get the NodePort
   kubectl get service agentic-rag
   
   # Access the application at http://<node-ip>:<node-port>
   ```

## Model Selection

The deployment includes both Hugging Face models and Ollama models:

- **Hugging Face Models**: Mistral-7B models (requires token in config.yaml)
- **Ollama Models**: llama3, phi3, and qwen2 (automatically downloaded during deployment)

You can select which model to use from the Gradio interface after deployment.

## Monitoring and Troubleshooting

### Check pod status:

```bash
kubectl get pods
```

### View logs:

```bash
kubectl logs -f deployment/agentic-rag
```

### Shell into the pod:

```bash
kubectl exec -it deployment/agentic-rag -- /bin/bash
```

## Scaling

For production deployments, consider:

1. Using persistent volumes for data storage
2. Adjusting resource requests and limits based on your workload
3. Setting up proper monitoring and logging
4. Implementing horizontal pod autoscaling

## Cleanup

To remove the deployment:

```bash
kubectl delete -f local-deployment/
```

## Future Work

A distributed system deployment that separates the LLM inference system into its own service is planned for future releases. This will allow for better resource allocation and scaling in production environments. 