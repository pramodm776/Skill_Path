# Azure deployment: SkillPath AI

## Decision

Deploy the complete product to Azure as one same-origin FastAPI container application. The frontend is served by FastAPI, so there is no Firebase hosting project, cross-cloud CORS setup, duplicate deployment, or browser-side secret boundary to manage.

```text
Browser
  -> Azure Container Apps (one SkillPath AI container)
       -> GitHub / JSearch / OpenAI / xAI / Telegram over HTTPS
       -> Azure Files mount at /app/data (SQLite snapshots)
       -> Log Analytics
  -> Azure Container Registry (private image, pulled using user-assigned identity)
```

`infra/foundation.bicep` creates the environment, Azure Container Registry, Azure Files share, Log Analytics workspace, and a user-assigned identity with `AcrPull`. `infra/app.bicep` deploys the container, mounts `/app/data`, and constrains it to one always-on replica.

This is deliberately a hackathon deployment profile. SQLite on an Azure Files mount is acceptable only with **one replica** and no concurrent writer process. The template uses `SQLITE_JOURNAL_MODE=DELETE` to avoid WAL files on the SMB mount. For a real multi-replica product, move snapshot/history storage to Azure Database for PostgreSQL before scaling.

## Prerequisites

- Azure CLI signed in to the subscription with permission to create resources and role assignments.
- Docker is optional locally. The commands below use Azure Container Registry Build, so they build the Dockerfile remotely.
- A globally unique lowercase resource prefix. It becomes part of the Registry and Storage account names.

## Deploy from Windows PowerShell

Run these commands from the repository root. They create cloud resources and therefore incur Azure usage; choose an approved subscription and set a budget alert first.

```powershell
cd "C:\Users\HP\OneDrive\Desktop\hackathon-project"

az login
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

$resourceGroup = "skillpath-rg"
$location = "centralindia"
$prefix = "spai$(Get-Random -Minimum 100000 -Maximum 999999)"
$appName = "$prefix-app"
$imageTag = "v1"

az group create --name $resourceGroup --location $location

$foundation = az deployment group create `
  --resource-group $resourceGroup `
  --template-file .\infra\foundation.bicep `
  --parameters prefix=$prefix location=$location `
  --query properties.outputs --output json | ConvertFrom-Json

$acrName = $foundation.registryName.value
$registryLoginServer = $foundation.registryLoginServer.value
$environmentName = $foundation.environmentName.value
$identityResourceId = $foundation.identityResourceId.value
$storageAccountName = $foundation.storageAccountName.value
$fileShareName = $foundation.fileShareName.value

az acr build --registry $acrName --image "skillpath-ai:$imageTag" .

$appDeployment = az deployment group create `
  --resource-group $resourceGroup `
  --template-file .\infra\app.bicep `
  --parameters `
    appName=$appName `
    managedEnvironmentName=$environmentName `
    registryLoginServer=$registryLoginServer `
    containerImage="$registryLoginServer/skillpath-ai:$imageTag" `
    identityResourceId=$identityResourceId `
    storageAccountName=$storageAccountName `
    fileShareName=$fileShareName `
    pollIntervalSeconds=60 `
  --query properties.outputs --output json | ConvertFrom-Json

$appUrl = $appDeployment.appUrl.value
Invoke-RestMethod "$appUrl/api/health"
Write-Host "SkillPath AI: $appUrl"
```

For the final live rehearsal, change only `pollIntervalSeconds=10` in the second deployment command. Return it to `60` afterward to reduce GitHub API calls.

## Add server-side secrets after the first deployment

The core public-repository demo runs without a token. Add only the integrations you intend to demonstrate. Never add secrets to a Bicep parameter file, Git, browser code, or a screenshot.

For a fast hackathon deployment, set an environment value for the current PowerShell process, then make a Container Apps secret reference. The command history contains the variable name, not the secret value:

```powershell
# Put the token into the current process without echoing it or saving it to Git.
$secureToken = Read-Host "Paste fine-grained GitHub token" -AsSecureString
$tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
  $env:GITHUB_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
  az containerapp secret set --name $appName --resource-group $resourceGroup `
    --secrets "github-token=$env:GITHUB_TOKEN"
  az containerapp update --name $appName --resource-group $resourceGroup `
    --set-env-vars "GITHUB_TOKEN=secretref:github-token"
}
finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer)
  Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
}
```

Repeat the same pattern only for features you enable:

| Container Apps secret name | Runtime environment variable | Enable/configure |
| --- | --- | --- |
| `openai-key` | `OPENAI_API_KEY=secretref:openai-key` | Also set `ENABLE_LLM_EXPLANATIONS=true`. |
| `xai-key` | `XAI_API_KEY=secretref:xai-key` | Also set `XAI_MODEL` and `ENABLE_XAI_FALLBACK=true`. |
| `jsearch-key` | `JSEARCH_API_KEY=secretref:jsearch-key` | Job discovery then becomes available. |
| `telegram-token` | `TELEGRAM_BOT_TOKEN=secretref:telegram-token` | Also set webhook secret and enable Telegram. |
| `telegram-webhook` | `TELEGRAM_WEBHOOK_SECRET=secretref:telegram-webhook` | Use a long random value. |

For the final presentation deployment, use Azure Key Vault instead of literal Container Apps secret values. The deployed app already has a user-assigned managed identity. Grant that identity **Key Vault Secrets User**, then use Container Apps Key Vault references. Azure documents the `keyvaultref:<url>,identityref:<identity-resource-id>` secret form and `secretref:<secret-name>` environment-variable form. Do this from Azure Portal or Azure Cloud Shell because Azure CLI notes Key Vault reference setup is not supported from PowerShell.

Set non-secret runtime values with `az containerapp update`, for example:

```powershell
az containerapp update --name $appName --resource-group $resourceGroup `
  --set-env-vars `
    "ENABLE_LLM_EXPLANATIONS=true" `
    "JSEARCH_API_URL=https://jsearch.p.rapidapi.com" `
    "TELEGRAM_NOTIFICATIONS_ENABLED=true" `
    "TELEGRAM_BOT_USERNAME=YourBotUsername" `
    "PUBLIC_BASE_URL=$appUrl"
```

## Enable the Telegram webhook

After the deployed app has its Telegram token, webhook secret, enable flag, bot username, and `PUBLIC_BASE_URL`, run this from a machine with the same environment values available (or run it inside a one-off secure operator shell):

```powershell
python -m backend.telegram_setup set
```

It configures Telegram to deliver only `message` updates to `/api/integrations/telegram/webhook` and validates the configured webhook secret on every incoming request. The dashboard generates an expiring `/start` pairing code per repository. A paired chat receives only a short automatic-reassessment alert, not job text, source excerpts, keys, or a GitHub token.

To remove the webhook later:

```powershell
python -m backend.telegram_setup delete
```

## Verify and update

```powershell
Invoke-RestMethod "$appUrl/api/health"
az containerapp logs show --name $appName --resource-group $resourceGroup --follow

# Build and deploy a new immutable image tag.
$imageTag = "v2"
az acr build --registry $acrName --image "skillpath-ai:$imageTag" .
az containerapp update --name $appName --resource-group $resourceGroup `
  --image "$registryLoginServer/skillpath-ai:$imageTag"
```

After an update, run the dashboard workflow with a public repository. Check the health endpoint, save a real posting, connect the repository, make a real commit, and wait for the automatic new-SHA reassessment.

## Cost and lifecycle guardrails

- `minReplicas=1` is intentional: the GitHub polling monitor must stay alive. It also means the app can incur idle compute charges.
- The Bicep profile uses one 0.5 vCPU / 1 GiB replica, Basic ACR, Standard LRS storage, a 5 GiB file share, and Log Analytics retention of 30 days. Review the Azure Pricing Calculator for the selected region before deployment.
- Create a subscription budget and an alert before demo day. Do not leave a test environment running indefinitely after the event.
- Delete only after exporting anything you want to retain. This is a destructive operation:

```powershell
az group delete --name $resourceGroup --yes --no-wait
```
