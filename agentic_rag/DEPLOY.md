# Deploy with Terraform and Kustomize

## TODOS

- Multiple containers for different functions
  - Gradio
  - Agents / Inference
  - Database Access
- Hugging face token should be a secret
- Liveness and Readiness
- Use Load balancer instead of Gradio Live
- Autoscaling

## Deploy Infrastructure

Install scripts dependencies

```bash
cd scripts/ && npm install && cd ..
```

Set environment (answer questions) and generate Terraform `tfvars` file.

```bash
zx scripts/setenv.mjs
```

> Alternative: One liner for the yellow commands (for easy copy paste)
>
> ```bash
> cd tf && terraform init && terraform apply -auto-approve
> ```

Come back to root folder

```bash
cd ..
```

Prepare Kubeconfig and namespace:

```bash
zx scripts/kustom.mjs
```

## Deploy Application

Export kubeconfig to get access to the Kubernetes Cluster

```bash
export KUBECONFIG="$(pwd)/tf/generated/kubeconfig"
```

Check everything works

```bash
kubectl cluster-info
```

Deploy the production overlay

```bash
kubectl apply -k k8s/kustom/overlays/prod
```

Check all pods are Ready:

```bash
kubectl get po --namespace=agentic-rag
```

Get Gradio Live URL:

```bash
kubectl logs $(kubectl get po -n agentic-rag -l app=agentic-rag -o name) -n agentic-rag | grep "Running on public URL"
```

Open the URL from the command before in your browser.

Also, you could get the Load Balancer Public IP address:

```bash
echo "http://$(kubectl get service \
  -n agentic-rag \
  -o jsonpath='{.items[?(@.spec.type=="LoadBalancer")].status.loadBalancer.ingress[0].ip}')"
```

To troubleshoot connect to the container

```bash
kubectl exec -it $(kubectl get po -n agentic-rag -l app=agentic-rag -o name) -n agentic-rag -- sh
```

## Clean up

Delete the production overlay

```bash
kubectl delete -k k8s/kustom/overlays/prod
```

Destroy infrastructure with Terraform.

```bash
cd tf
```

```bash
terraform destroy -auto-approve
```

```bash
cd ..
```

Clean up the artifacts and config files

```bash
zx scripts/clean.mjs
```
