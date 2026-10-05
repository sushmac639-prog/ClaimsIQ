# ClaimIQ

ClaimIQ is a FastAPI-based insurance claims and policy knowledge platform. It provides PostgreSQL persistence, SQLAlchemy 2.0, Alembic migrations, OAuth2 password login with JWT access/refresh tokens, logout/revocation, Argon2 password hashing, RBAC, policy and claim CRUD, claim workflow/audit logging, Docker, automated tests, and an AI-powered RAG assistant for uploaded insurance/policy documents.

## Capstone requirement coverage

| Requirement | Implementation |
|---|---|
| FastAPI | `app/main.py` and API routers |
| Login API | `POST /api/v1/auth/login` |
| OAuth2 + JWT | FastAPI OAuth2 password flow + PyJWT |
| Logout API | `POST /api/v1/auth/logout` with DB-backed token revocation |
| Pydantic | Request/response validation in `app/schemas` |
| SQLAlchemy ORM | `app/db/models.py` |
| PostgreSQL | PostgreSQL 16 + Alembic |
| Password hashing | Argon2 via `pwdlib` |
| REST/service packages | Modular routers, services, RAG and LLM layers |
| LLM | Microsoft Foundry/Azure OpenAI through LangChain |
| Embeddings | Foundry/Azure OpenAI embedding deployment through LangChain |
| Vector DB | ChromaDB |
| RAG | PDF -> chunks -> embeddings -> similarity retrieval -> LLM |
| Insurance documents | PDF upload, policy association, region access control |
| Swagger | `/docs` |
| ReDoc | `/redoc` |
| Testing | `tests/` with security, workflow, RAG and API-contract tests |
| Docker | Dockerfile + Docker Compose |
| GitHub Actions | `.github/workflows/ci.yml` and `deploy-aks.yml` |
| Jenkins | `Jenkinsfile` |
| Azure Pipelines | `azure-pipelines.yml` |
| Kubernetes | `k8s/` manifests |
| Azure deployment | AKS + ACR + Azure PostgreSQL deployment path |

MySQL is intentionally not included because this implementation uses PostgreSQL as the capstone database.

## Architecture

```text
                    ClaimIQ FastAPI
                         |
        +----------------+----------------+
        |                |                |
   Auth / RBAC       Policies/Claims   Documents
        |                |                |
        |                |          PDF extraction
        |                |                |
        |                |          LangChain chunks
        |                |                |
        |                |          Embeddings
        |                |                |
        |                |             ChromaDB
        |                |                |
        +----------------+-------- RAG retrieval
                                  |
                           approved context
                                  |
                           Microsoft Foundry
                           Chat model / LLM
                                  |
                              Answer + [S1]
                                  |
                              PostgreSQL
                         audit/query metadata
```

## AI provider

The recommended capstone configuration is **Microsoft Foundry** using its OpenAI-v1-compatible endpoint. The application keeps a direct OpenAI provider as an optional fallback.

Set:

```text
AI_PROVIDER=azure_foundry
AZURE_OPENAI_API_KEY=<Foundry API key>
AZURE_OPENAI_BASE_URL=https://<resource-name>.services.ai.azure.com/openai/v1/
AZURE_OPENAI_CHAT_MODEL=<your chat deployment name>
AZURE_OPENAI_EMBEDDING_MODEL=<your embedding deployment name>
```

The model values should be the **deployment names configured in your Azure Foundry project**, not necessarily the underlying model's catalog name.

The current LangChain integration uses the OpenAI-compatible route, so no separate Azure-specific LangChain package is required.

## Azure resources

Required for the full Azure capstone deployment:

1. **Microsoft Foundry** resource/project
   - Deploy one chat model.
   - Deploy one embedding model.
   - Grant the developer/CI identity the appropriate Foundry access.

2. **Azure Database for PostgreSQL Flexible Server**
   - Production PostgreSQL database.
   - Use SSL in the connection string.

3. **Azure Container Registry (ACR)**
   - Stores `claimiq-api` images.

4. **Azure Kubernetes Service (AKS)**
   - Runs the FastAPI container.

5. **Azure Monitor / Log Analytics**
   - Container and cluster diagnostics.

6. **Azure Key Vault** (recommended)
   - JWT secret, DB secret and AI credentials.

### Optional AI service: Azure AI Document Intelligence

It is **not required** for normal text PDFs because the current implementation uses `pypdf`.

Use Document Intelligence if your capstone must support scanned policy documents, OCR, tables or complex forms:

```text
Scanned PDF
   -> Azure AI Document Intelligence
   -> extracted text/layout
   -> LangChain chunking
   -> Foundry embeddings
   -> ChromaDB
   -> Foundry chat model
```

## Local development

### Prerequisites

- Python 3.11+
- Docker Desktop + Docker Compose
- PostgreSQL is supplied by Docker Compose
- Microsoft Foundry API key/model deployments for AI features

### Setup

1. Copy `.env.example` to `.env`.
2. Set `JWT_SECRET_KEY`.
3. Set the Foundry variables shown above.
4. Run:

```powershell
docker compose up --build
```

The API container automatically runs:

```text
alembic upgrade head
```

Open Swagger:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

## Seed the Admin user

```powershell
docker compose exec api python -m scripts.seed_admin
```

Use `python -m scripts.seed_admin`, not `python scripts/seed_admin.py`, so the project root remains on the Python import path.

## RAG flow

### 1. Upload a policy PDF

Admin only:

```http
POST /api/v1/documents
Content-Type: multipart/form-data
```

Fields:

- `file`: PDF
- `policy_id`: optional ClaimIQ policy ID
- `region`: optional region

Processing:

```text
PDF
 -> SHA-256 duplicate check
 -> pypdf page extraction
 -> LangChain RecursiveCharacterTextSplitter
 -> embeddings
 -> ChromaDB
 -> PostgreSQL document/chunk metadata
```

### 2. Ask a question

```http
POST /api/v1/ai/query
```

Example:

```json
{
  "question": "What hospitalization expenses are covered?",
  "policy_id": 1,
  "top_k": 5
}
```

The answer contains document/page citations such as `[S1]` and source metadata.

The model is explicitly instructed to answer only from approved retrieved context. When there is insufficient context, the API returns:

```text
No relevant information was found in the approved documents.
```

## Authentication

### Login

```http
POST /api/v1/auth/login
```

OAuth2 form fields:

```text
username=<email>
password=<password>
```

### Refresh

```http
POST /api/v1/auth/refresh
```

Refresh-token rotation is enabled. The old refresh token is revoked when a new pair is issued.

### Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <access-token>
```

Optional body:

```json
{
  "refresh_token": "<refresh-token>"
}
```

The access token and supplied refresh token are stored in the PostgreSQL revocation table until their expiry. This makes logout effective across API instances instead of relying on in-memory state.

## PostgreSQL / pgAdmin

Docker PostgreSQL:

```text
Host: localhost
Port: 5432
Database: claimiq
Username: claimiq
Password: claimiq_password
```

From the API container, the host is `db`:

```text
postgresql+psycopg://claimiq:claimiq_password@db:5432/claimiq
```

## Tests

Run locally:

```powershell
pytest -q
```

The test suite includes:

- JWT/JTI security tests
- logout contract tests
- claim workflow/edge tests
- enum persistence tests
- RAG chunk/page behavior
- RAG source/no-match contract tests
- health endpoint test

CI also performs Python compilation and Docker image build.

## DevOps / CI-CD

### GitHub Actions

`/.github/workflows/ci.yml`

Runs on pull requests and pushes to `main`/`develop`:

```text
checkout
 -> Python setup
 -> pip install
 -> compile
 -> pytest
 -> Docker build
```

`/.github/workflows/deploy-aks.yml`

Deploys `main` to AKS:

```text
GitHub
 -> Azure login
 -> ACR login
 -> Docker build
 -> ACR push
 -> AKS context
 -> Kubernetes secrets
 -> kubectl apply
 -> rollout status
```

Required GitHub secrets:

```text
AZURE_CREDENTIALS
ACR_NAME
ACR_LOGIN_SERVER
AKS_RESOURCE_GROUP
AKS_CLUSTER_NAME
DATABASE_URL
JWT_SECRET_KEY
AZURE_OPENAI_API_KEY
```

### Jenkins

`Jenkinsfile` provides the Jenkins path:

```text
Checkout
 -> Python tests
 -> Docker build
 -> optional ACR push
```

Configure the Jenkins credential:

```text
claimiq-acr-credentials
```

and replace the placeholder ACR login server in `Jenkinsfile`.

### Azure Pipelines

`azure-pipelines.yml` provides the Azure DevOps path:

```text
Test stage
   -> Build/Deploy stage
   -> ACR
   -> AKS
```

Create an Azure DevOps variable group named:

```text
ClaimIQ-Production
```

with secret variables:

```text
JWT_SECRET_KEY
DATABASE_URL
AZURE_OPENAI_API_KEY
```

and non-secret variables:

```text
ACR_NAME
ACR_LOGIN_SERVER
AKS_RESOURCE_GROUP
AKS_CLUSTER_NAME
```

Create an Azure service connection named:

```text
ClaimIQ-Azure-ServiceConnection
```

with permission to deploy to the required Azure resources.

## Kubernetes

The `k8s/` folder contains:

- `configmap.yaml`
- `pvc.yaml`
- `deployment.yaml`
- `README.md`

For Azure, PostgreSQL is intentionally externalized to Azure Database for PostgreSQL. ChromaDB and uploaded documents use persistent volumes in AKS.

The deployment is one replica because the current Chroma implementation uses persistent local vector storage. For horizontal scaling, move the vector layer to a shared/managed vector service such as Azure AI Search.

## Reindexing

If the embedding model or chunking configuration changes:

```powershell
docker compose exec api python -m scripts.reindex_documents
```

## Migration reset for disposable development data

If a development database is corrupted or contains an incompatible old schema:

```powershell
docker compose down -v
docker compose up --build
```

**Warning:** `docker compose down -v` deletes the PostgreSQL Docker volume and all database data.

## Main API endpoints

### Authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Users

- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET /api/v1/users/{id}`
- `PATCH /api/v1/users/{id}`
- `DELETE /api/v1/users/{id}`

### Policies

- `POST /api/v1/policies`
- `GET /api/v1/policies`
- `GET /api/v1/policies/{id}`
- `PATCH /api/v1/policies/{id}`
- `DELETE /api/v1/policies/{id}`

### Claims

- `POST /api/v1/claims`
- `GET /api/v1/claims`
- `GET /api/v1/claims/{id}`
- `PATCH /api/v1/claims/{id}`
- `PATCH /api/v1/claims/{id}/status`
- `POST /api/v1/claims/{id}/notes`
- `GET /api/v1/claims/{id}/notes`
- `DELETE /api/v1/claims/{id}`

### Documents / RAG

- `POST /api/v1/documents`
- `GET /api/v1/documents`
- `PATCH /api/v1/documents/{id}/status`
- `POST /api/v1/ai/query`
