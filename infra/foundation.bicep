@description('Short lowercase prefix used in globally unique Azure resource names.')
@minLength(3)
@maxLength(14)
param prefix string

@description('Azure region for every resource, for example centralindia.')
param location string = resourceGroup().location

@description('Name of the Azure Container Apps managed environment.')
param environmentName string = '${prefix}-env'

@description('Name of the Azure Container Registry.')
param registryName string = '${replace(prefix, '-', '')}acr'

@description('Name of the Azure storage account that hosts the single-replica SQLite volume.')
param storageAccountName string = '${replace(prefix, '-', '')}data'

@description('Name of the Azure Files share mounted by the container app.')
param fileShareName string = 'skillpath-data'

@description('Name of the managed identity permitted to pull from the registry.')
param identityName string = '${prefix}-app-id'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: registryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: fileShareName
  properties: {
    shareQuota: 5
    enabledProtocols: 'SMB'
  }
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, appIdentity.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: appIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output environmentId string = environment.id
output environmentName string = environment.name
output storageAccountName string = storage.name
output fileShareName string = fileShare.name
output identityResourceId string = appIdentity.id
output appIdentityPrincipalId string = appIdentity.properties.principalId
