import json
import secrets
import logging
from urllib.parse import quote
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from datetime import datetime
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
from integrations.integration_item import IntegrationItem
import os
from dotenv import load_dotenv
from store import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

REQUIRED_SCOPES = [
    'crm.schemas.contacts.write',
    'oauth',
    'crm.objects.contacts.write',
    'crm.schemas.contacts.read',
    'crm.objects.contacts.read',
]

HUBSPOT_OBJECTS=['contacts']


def get_authorization_url(state: str) -> str:
    """
    Generate HubSpot authorization URL with required scopes
    """
    try:
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
    except Exception as e:
        logger.error(f"Error generating authorization URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

async def authorize_hubspot(user_id, org_id):
    """
    Initialize HubSpot OAuth flow
    """
    try:
        # Generate a secure random state
        state_data = {
            'state': secrets.token_urlsafe(32),
            'user_id': user_id,
            'org_id': org_id
        }
        encoded_state = json.dumps(state_data)
        
        await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)
        logger.info(f"Initialized OAuth flow for user {user_id} in org {org_id}")
        
        return get_authorization_url(encoded_state)
    except Exception as e:
        logger.error(f"Error in authorize_hubspot: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initialize OAuth flow")

async def oauth2callback_hubspot(request: Request):
    """
    Handle the OAuth callback from HubSpot
    """
    try:
        if request.query_params.get('error'):
            error_msg = request.query_params.get('error')
            logger.error(f"OAuth callback error: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        code = request.query_params.get('code')
        encoded_state = request.query_params.get('state')
        
        if not code or not encoded_state:
            logger.error("Missing code or state in OAuth callback")
            raise HTTPException(status_code=400, detail='Missing code or state')

        state_data = json.loads(encoded_state)
        original_state = state_data.get('state')
        user_id = state_data.get('user_id')
        org_id = state_data.get('org_id')

        saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
        if not saved_state or original_state != json.loads(saved_state).get('state'):
            logger.error("Invalid state in OAuth callback")
            raise HTTPException(status_code=400, detail='Invalid state')
        
        logger.info("Saving credentials")

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                'https://api.hubspot.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                }
            )

            if token_response.status_code != 200:
                logger.error(f"Failed to get access token: {token_response.text}")
                raise HTTPException(status_code=400, detail='Failed to get access token')

            access_token = token_response.json().get('access_token')
            
            # Get user info while client is still open
            user_info_response = await client.get(
                'https://api.hubspot.com/oauth/v1/access-tokens/' + access_token
            )
            hubspot_user_id = user_info_response.json().get('user_id')

            credentials_data = {
                **token_response.json(),
                'user_info': user_info_response.json(),
                'user_id': user_id,
                'org_id': org_id
            }

            await add_key_value_redis(
                f'hubspot_credentials:{org_id}:{user_id}',
                json.dumps(credentials_data),
                expire=600
            )

            db.save_hubspot_credentials(
                user_id=user_id,
                org_id=org_id,
                hubspot_user_id=hubspot_user_id,
            )

        await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
        logger.info(f"Successfully completed OAuth flow for user {user_id}")

        close_window_script = """
        <html>
            <script>
                window.close();
            </script>
        </html>
        """
        logger.info("Closing OAuth window")
        return HTMLResponse(content=close_window_script)
    except Exception as e:
        logger.error(f"Error in oauth2callback_hubspot: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth callback failed")

async def get_hubspot_credentials(user_id, org_id):
    """
    Retrieve stored HubSpot credentials
    """
    try:
        credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
        if not credentials:
            logger.error(f"No credentials found for user {user_id}")
            raise HTTPException(status_code=400, detail='No credentials found')
        await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
        return json.loads(credentials)
    except Exception as e:
        logger.error(f"Error retrieving credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credentials")

def create_integration_item_metadata_object(
    response_json: dict,
    item_type: str,
    parent_id: str = None,
    parent_name: str = None
) -> IntegrationItem:
    """
    Creates an integration metadata object from the HubSpot response
    """
    try:
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
    except Exception as e:
        logger.error(f"Error creating integration item: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create integration item")

async def get_items_hubspot(credentials: str) -> list[IntegrationItem]:
    """
    Fetch items from HubSpot and return as IntegrationItem objects
    """
    try:
        credentials_data = json.loads(credentials)
        access_token = credentials_data.get('access_token')
        org_id = credentials_data.get('org_id')
        user_id = credentials_data.get('user_id')
        hubspot_user_id = db.get_hubspot_user_id(user_id, org_id)
        
        if not access_token:
            logger.error("Invalid credentials - missing access token")
            raise HTTPException(status_code=400, detail='Invalid credentials')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        list_of_integration_items = []
        
        async with httpx.AsyncClient() as client:
            cached_items = await get_value_redis(f'hubspot_items:{hubspot_user_id}')
            if cached_items:
                logger.info("Returning items from cache")
                return json.loads(cached_items)

            for object in HUBSPOT_OBJECTS:
                response = await client.get(
                    f'https://api.hubspot.com/crm/v3/objects/{object}',
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.error(f"Failed to fetch contacts: {response.text}")
                    raise HTTPException(status_code=400, detail='Failed to fetch contacts')

                response_json = response.json()
                
                for data in response_json.get('results', []):
                    integration_item = create_integration_item_metadata_object(
                        response_json=data,
                        item_type=object
                    )
                    list_of_integration_items.append(integration_item)

                items_dict = [item.to_dict() for item in list_of_integration_items]
                await add_key_value_redis(f'hubspot_items:{hubspot_user_id}', json.dumps(items_dict), expire=600)
                logger.info(f"Successfully fetched {len(list_of_integration_items)} items from HubSpot")

        return list_of_integration_items
    except Exception as e:
        logger.error(f"Error fetching HubSpot items: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch HubSpot items")

async def invalidate_hubspot_cache(request: Request):
    """
    Invalidate HubSpot cache
    """
    try:
        body = await request.json()
        hubspot_user_id = body[0].get('sourceId').split(':')[1]
        await delete_key_redis(f'hubspot_items:{hubspot_user_id}')
        logger.info(f"Successfully invalidated cache for HubSpot user {hubspot_user_id}")
    except Exception as e:
        logger.error(f"Error invalidating HubSpot cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")
