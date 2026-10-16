# ClaimIQ Kubernetes deployment

These manifests target **AKS**. PostgreSQL should be Azure Database for PostgreSQL Flexible Server rather than a PostgreSQL pod for the Azure deployment. Local development remains Docker Compose with PostgreSQL.

## Before deployment

1. Create an AKS cluster and Azure Container Registry.
2. Create Azure Database for PostgreSQL Flexible Server and a `claimiq` database.
3. Create the Microsoft Foundry resource/project and deploy the chat and embedding models.
4. Replace `REPLACE_FOUNDRY_RESOURCE` in `configmap.yaml`.
5. Replace `REPLACE_ACR_LOGIN_SERVER` in `deployment.yaml`, or let the CI/CD pipeline set the image after applying the manifests.
6. Create the `claimiq-secrets` Kubernetes secret:

```bash
kubectl create secret generic claimiq-secrets \
  --from-literal=DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/claimiq?sslmode=require' \
  --from-literal=JWT_SECRET_KEY='GENERATE-A-LONG-RANDOM-VALUE' \
  --from-literal=AZURE_OPENAI_API_KEY='YOUR-FOUNDRY-API-KEY'
```

7. Apply:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
```

For CI/CD, use the included GitHub Actions or Azure Pipelines workflow so secrets are injected from the CI/CD secret store rather than committed to Git.
