# VectorShift Assignment

## HubSpot Integration(Backend)

The backend provides a complete integration with HubSpot's API, allowing for authentication, data retrieval, and webhook handling.

### API Endpoints

1. **Authorization**

   - `POST /integrations/hubspot/authorize`
   - Initiates the OAuth2 flow for HubSpot integration
   - Required parameters:
     - `user_id`: Internal user identifier
     - `org_id`: Organization identifier

2. **OAuth2 Callback**

   - `GET /integrations/hubspot/oauth2callback`
   - Handles the OAuth2 callback from HubSpot
   - Processes the authorization code and stores credentials

3. **Credentials Management**

   - `POST /integrations/hubspot/credentials`
   - Retrieves stored HubSpot credentials
   - Required parameters:
     - `user_id`: Internal user identifier
     - `org_id`: Organization identifier

4. **Data Loading**

   - `POST /integrations/hubspot/load`
   - Retrieves items from HubSpot
   - Required parameters:
     - `credentials`: HubSpot credentials

5. **Webhook Handler**
   - `POST /webhook`
   - Handles incoming webhooks from HubSpot
   - Invalidates HubSpot cache when changes are detected

## Database System

The backend uses a JSON-based database system for storing integration credentials and user data.

### Database Structure

The database is stored in `store/db.json` and maintains the following structure:

```json
{
  "hubspot": [
    {
      "user_id": "internal_user_id",
      "org_id": "organization_id",
      "integration_user_id": "hubspot_user_id"
    }
  ]
}
```

### Database Functions

Db.py file includes functions for reading and writing data to json file


### How caching works currently

when the user clicks on connect , the access token that is generated contains the hubspot_user_id that will be used to generate the redis key accoring to the user.

how cache is invalieded ; when the user creates a new object (like contact) a webhook request is made to vectorshits backend that will delete the data from redis cache

## HubSpot Integration(Frontend)

**Hubspot.js**

This file includes the code of calling the backend server for auth and getting hubspot data.

**CredentialsContext**

This file stores the credentials temp credentails which is helpful in persisting creds when we change the integration type



