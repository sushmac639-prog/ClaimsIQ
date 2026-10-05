# Azure resources required for ClaimIQ

## Required Azure resources

### 1. Microsoft Foundry
Create one Microsoft Foundry resource and project.

Deploy these two model deployments in the project:

- **Chat model**: the model selected for the capstone, configured through `AZURE_OPENAI_CHAT_MODEL`.
- **Embedding model**: `text-embedding-3-small` (or an approved embedding model available in your Azure region), configured through `AZURE_OPENAI_EMBEDDING_MODEL`.

For the OpenAI-v1 compatible integration used by this project, configure:

```text
AI_PROVIDER=azure_foundry
AZURE_OPENAI_BASE_URL=https://<resource-name>.services.ai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_CHAT_MODEL=<your-chat-deployment-name>
AZURE_OPENAI_EMBEDDING_MODEL=<your-embedding-deployment-name>
```

The application uses LangChain's OpenAI-compatible integrations against the Foundry OpenAI-v1 endpoint. Microsoft documents this endpoint as the OpenAI-compatible route for Foundry Models.

### 2. Azure Database for PostgreSQL Flexible Server
Use this for the Azure environment. Do not put production PostgreSQL in the AKS cluster.

Create:

- PostgreSQL Flexible Server
- `claimiq` database
- Application database user
- SSL-required connection string

Set it as `DATABASE_URL` in the deployment secret.

### 3. Azure Container Registry (ACR)
Stores the ClaimIQ Docker image.

Example naming:

```text
claimiqacr.azurecr.io/claimiq-api:<build-id>
```

### 4. Azure Kubernetes Service (AKS)
Runs the FastAPI container.

The included manifests use one replica because ChromaDB is local persistent storage. If the application is later scaled horizontally, move the vector layer to a managed/shared vector service such as Azure AI Search.

### 5. Azure Monitor / Log Analytics
Connect AKS/Container Apps to Log Analytics for application and deployment diagnostics.

### 6. Azure Key Vault (recommended)
Store production secrets such as:

- database password / connection string
- Foundry API key if API-key authentication is used
- JWT secret

For a production-grade deployment, prefer Microsoft Entra ID / managed identity where supported instead of long-lived API keys.

## Optional AI service

### Azure AI Document Intelligence
Not required for normal text-based PDFs because ClaimIQ currently extracts PDF text with `pypdf`.

Add Document Intelligence if the project must support scanned/image-only policy documents, OCR, tables, forms, or complex layouts. The RAG flow can then become:

```text
PDF / scanned policy
       ↓
Document Intelligence
       ↓
Extracted text/layout
       ↓
LangChain chunking
       ↓
Foundry embeddings
       ↓
ChromaDB
       ↓
Foundry chat model
```
