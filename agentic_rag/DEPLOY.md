# Deploy with Terraform and Kustomize

## TODOS

- Hugging face token should be a secret
- PVCs and deployments in separate files
- multiple deployments/pods for different functions
- Consider include installation of driver on Kustomize https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
- Hugging Face Token optional
- Autonomous for Vector Search

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
kubectl wait pod --all --for=condition=Ready --namespace=agentic-rag
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
