# slack.py

import json
import secrets
from urllib.parse import quote
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from datetime import datetime
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from integrations.integration_item import IntegrationItem
import os


CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

REQUIRED_SCOPES = [
    'crm.objects.contacts.write',
    'crm.schemas.contacts.write',
    'oauth',
    'crm.schemas.contacts.read',
    'crm.objects.contacts.read'
]

def get_authorization_url(state: str) -> str:
    """
    Generate HubSpot authorization URL with required scopes
    """
    # URL encode the redirect URI and scopes
    encoded_redirect_uri = quote(REDIRECT_URI)
    encoded_scopes = quote(' '.join(REQUIRED_SCOPES))
    
    return (
        f'https://app-na2.hubspot.com/oauth/authorize'
        f'?client_id={CLIENT_ID}'
        f'&redirect_uri={encoded_redirect_uri}'
        f'&scope={encoded_scopes}'
        f'&state={state}'
    )

async def authorize_hubspot(user_id, org_id):
    """
    Initialize HubSpot OAuth flow
    """
    # Generate a secure random state
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
    
    return get_authorization_url(encoded_state)

async def oauth2callback_hubspot(request: Request):
    """
    Handle the OAuth callback from HubSpot
    """
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error'))

    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail='Missing code or state')

    state_data = json.loads(encoded_state)
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='Invalid state')

    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.hubspot.com/oauth/v1/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'code': code
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail='Failed to get access token')

    await add_key_value_redis(
        f'hubspot_credentials:{org_id}:{user_id}',
        json.dumps(response.json()),
        expire=600
    )

    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    """
    Retrieve stored HubSpot credentials
    """
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found')
    
    credentials_data = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    return credentials_data

def create_integration_item_metadata_object(
    response_json: dict,
    item_type: str,
    parent_id: str = None,
    parent_name: str = None
) -> IntegrationItem:
    """
    Creates an integration metadata object from the HubSpot response
    """
    item_id = response_json.get('id', '')
    
    # Handle different types of HubSpot objects
    if item_type == 'contact':
        name = f"{response_json['properties'].get('firstname', '')} {response_json['properties'].get('lastname', '')}".strip()
        creation_time = datetime.fromisoformat(response_json.get('createdAt', '').replace('Z', '+00:00'))
        last_modified_time = datetime.fromisoformat(response_json.get('updatedAt', '').replace('Z', '+00:00'))
    else:
        name = response_json.get('name', '')
        creation_time = None
        last_modified_time = None

    return IntegrationItem(
        id=f"{item_id}_{item_type}",
        type=item_type,
        name=name or "Unnamed",
        creation_time=creation_time,
        last_modified_time=last_modified_time,
        parent_id=parent_id,
        parent_path_or_name=parent_name,
        url=f"https://app.hubspot.com/contacts/{response_json.get('id')}" if item_type == 'contact' else None
    )

async def get_items_hubspot(credentials: str) -> list[IntegrationItem]:
    """
    Fetch items from HubSpot and return as IntegrationItem objects
    """
    credentials_data = json.loads(credentials)
    access_token = credentials_data.get('access_token')
    
    if not access_token:
        raise HTTPException(status_code=400, detail='Invalid credentials')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    list_of_integration_items = []
    
    # Fetch contacts
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://api.hubspot.com/crm/v3/objects/contacts',
            headers=headers,
            params={'limit': 100}  # Adjust limit as needed
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail='Failed to fetch contacts')

        contacts_data = response.json()
        
        for contact in contacts_data.get('results', []):
            integration_item = create_integration_item_metadata_object(
                response_json=contact,
                item_type='contact'
            )
            list_of_integration_items.append(integration_item)

        # Handle pagination if there are more contacts
        while contacts_data.get('paging', {}).get('next', {}).get('after'):
            response = await client.get(
                'https://api.hubspot.com/crm/v3/objects/contacts',
                headers=headers,
                params={
                    'limit': 100,
                    'after': contacts_data['paging']['next']['after']
                }
            )
            
            if response.status_code != 200:
                break
                
            contacts_data = response.json()
            for contact in contacts_data.get('results', []):
                integration_item = create_integration_item_metadata_object(
                    response_json=contact,
                    item_type='contact'
                )
                list_of_integration_items.append(integration_item)

    print(f"Retrieved {len(list_of_integration_items)} HubSpot items:")
    for item in list_of_integration_items:
        print(f"- {item.type}: {item.name} (ID: {item.id})")

    return list_of_integration_items