import json
import os
from typing import Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), 'db.json')

def read_db() -> Dict[str, Any]:
    """Read the database file"""
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
            initial_data = {}
            with open(DB_FILE, 'w') as f:
                json.dump(initial_data, f, indent=4)
            return initial_data
            
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        initial_data = {}
        with open(DB_FILE, 'w') as f:
            json.dump(initial_data, f, indent=4)
        return initial_data

def write_db(data: Dict[str, Any]) -> None:
    """Write to the database file"""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_integration_credentials(integration_type: str, user_id: str, org_id: str, integration_user_id: str, credentials: Optional[Dict[str, Any]] = None) -> None:
    """Save integration credentials to the database
    
    Args:
        integration_type: Type of integration (e.g., 'hubspot', 'notion')
        user_id: Internal user ID
        org_id: Organization ID
        integration_user_id: User ID from the integration service
        credentials: Optional credentials data to store
    """
    data = read_db()
    
    if integration_type not in data:
        data[integration_type] = []
    
    for entry in data[integration_type]:
        if entry['user_id'] == user_id and entry['org_id'] == org_id:
            entry['integration_user_id'] = integration_user_id
            if credentials:
                entry['credentials'] = credentials
            write_db(data)
            return
    
    new_entry = {
        'user_id': user_id,
        'org_id': org_id,
        'integration_user_id': integration_user_id
    }
    if credentials:
        new_entry['credentials'] = credentials
        
    data[integration_type].append(new_entry)
    write_db(data)


def get_integration_user_id(integration_type: str, user_id: str, org_id: str) -> Optional[str]:
    """Get integration user ID from the database
    
    Args:
        integration_type: Type of integration (e.g., 'hubspot', 'notion')
        user_id: Internal user ID
        org_id: Organization ID
    """
    data = read_db()
    for entry in data.get(integration_type, []):
        if entry['user_id'] == user_id and entry['org_id'] == org_id:
            return entry['integration_user_id']
    return None

#Temporary functions for HubSpot
def save_hubspot_credentials(user_id: str, org_id: str, hubspot_user_id: str) -> None:
    """Save HubSpot credentials to the database"""
    save_integration_credentials('hubspot', user_id, org_id, hubspot_user_id)

def get_hubspot_user_id(user_id: str, org_id: str) -> Optional[str]:
    """Get HubSpot user ID from the database"""
    return get_integration_user_id('hubspot', user_id, org_id) 