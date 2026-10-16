@description('Name of the Azure Container App.')
param appName string

@description('Region for the app resource.')
param location string = resourceGroup().location

@description('Name of the managed environment created by foundation.bicep in this resource group.')
param managedEnvironmentName string

@description('Registry server returned by foundation.bicep, for example teamacr.azurecr.io.')
param registryLoginServer string

@description('Full immutable image reference in the registry.')
param containerImage string

@description('Resource ID of the user-assigned identity granted AcrPull by foundation.bicep.')
param identityResourceId string

@description('Existing storage account name created by foundation.bicep.')
param storageAccountName string

@description('Existing Azure Files share name created by foundation.bicep.')
param fileShareName string = 'skillpath-data'

@description('Name used by the managed environment storage registration.')
param environmentStorageName string = 'skillpath-data'

@description('Monitor cadence in seconds. Use 10 only during a rehearsal to conserve GitHub API quota.')
@minValue(10)
param pollIntervalSeconds int = 60

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: managedEnvironmentName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource environmentStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: environmentStorageName
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: fileShareName
      accessMode: 'ReadWrite'
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: registryLoginServer
          identity: identityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'skillpath-ai'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'DATABASE_PATH'
              value: '/app/data/career_coach.sqlite3'
            }
            {
              name: 'SQLITE_JOURNAL_MODE'
              value: 'DELETE'
            }
            {
              name: 'MONITORING_ENABLED'
              value: 'true'
            }
            {
              name: 'POLL_INTERVAL_SECONDS'
              value: string(pollIntervalSeconds)
            }
            {
              name: 'ENABLE_LLM_EXPLANATIONS'
              value: 'false'
            }
            {
              name: 'TELEGRAM_NOTIFICATIONS_ENABLED'
              value: 'false'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'skillpath-data'
              mountPath: '/app/data'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'skillpath-data'
          storageType: 'AzureFile'
          storageName: environmentStorage.name
        }
      ]
    }
  }
}

output appName string = app.name
output appFqdn string = app.properties.configuration.ingress.fqdn
output appUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
