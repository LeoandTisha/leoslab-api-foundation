"""
Vault API endpoints.

Provides REST API endpoints for HashiCorp Vault operations including
health checks, secret retrieval, and authentication status.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from leoslab_toolkit import VaultClient
from leoslab_toolkit.common.exceptions import VaultError, AuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vault", tags=["vault"])


class VaultHealthResponse(BaseModel):
    """Vault health status response."""
    vault_url: str
    server_healthy: bool
    authenticated: bool
    auth_method: str
    error: Optional[str] = None


class SecretResponse(BaseModel):
    """Secret retrieval response."""
    mount: str
    path: str
    field: Optional[str] = None
    data: Dict[str, Any]


class SecretListResponse(BaseModel):
    """Secret list response."""
    mount: str
    path: str
    secrets: List[str]


class JiraTokenResponse(BaseModel):
    """Jira token response."""
    token_type: str
    token: str


@router.get("/health", response_model=VaultHealthResponse)
async def get_vault_health():
    """
    Get Vault server health and authentication status.
    
    Returns health information including server status, authentication
    status, and connection details.
    
    Raises:
        HTTPException: If Vault client initialization fails.
    """
    try:
        client = VaultClient()
        health_info = client.health_check()
        
        return VaultHealthResponse(**health_info)
        
    except AuthenticationError as e:
        logger.error(f"Vault authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to check Vault health: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/secrets/{mount}/{path:path}", response_model=SecretResponse)
async def get_secret(
    mount: str,
    path: str,
    field: Optional[str] = Query(None, description="Specific field to retrieve")
):
    """
    Retrieve a secret from Vault.
    
    Args:
        mount: Vault secret mount point (e.g., "leoslab", "kv").
        path: Secret path within mount.
        field: Optional specific field to retrieve.
        
    Returns:
        Secret data.
        
    Raises:
        HTTPException: If secret retrieval fails.
    """
    try:
        client = VaultClient()
        secret_data = client.get_secret(mount, path, field)
        
        return SecretResponse(
            mount=mount,
            path=path,
            field=field,
            data=secret_data if field is None else {field: secret_data}
        )
        
    except ValueError as e:
        logger.warning(f"Secret not found or invalid: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Vault authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to retrieve secret {mount}/{path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Secret retrieval failed: {str(e)}")


@router.get("/secrets/{mount}/{path:path}/list", response_model=SecretListResponse)
async def list_secrets(mount: str, path: str = ""):
    """
    List available secrets at a path.
    
    Args:
        mount: Vault secret mount point.
        path: Path within mount to list.
        
    Returns:
        List of available secrets.
        
    Raises:
        HTTPException: If listing fails.
    """
    try:
        client = VaultClient()
        secrets = client.list_secrets(mount, path)
        
        return SecretListResponse(
            mount=mount,
            path=path,
            secrets=secrets
        )
        
    except AuthenticationError as e:
        logger.error(f"Vault authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to list secrets at {mount}/{path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Secret listing failed: {str(e)}")


@router.get("/jira-token", response_model=JiraTokenResponse)
async def get_jira_token(
    token_type: str = Query("cloud", regex="^(cloud|admin)$", description="Token type: cloud or admin")
):
    """
    Get Jira API token from Vault.
    
    Args:
        token_type: Type of token to retrieve ("cloud" or "admin").
        
    Returns:
        Jira API token.
        
    Raises:
        HTTPException: If token retrieval fails.
    """
    try:
        client = VaultClient()
        token = client.get_jira_token(token_type)
        
        return JiraTokenResponse(
            token_type=token_type,
            token=token
        )
        
    except ValueError as e:
        logger.warning(f"Invalid token type: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"Vault authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to retrieve Jira token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token retrieval failed: {str(e)}")


@router.post("/auth/test")
async def test_vault_authentication():
    """
    Test Vault authentication.
    
    Returns basic authentication status without exposing sensitive data.
    
    Raises:
        HTTPException: If authentication fails.
    """
    try:
        client = VaultClient()
        health = client.health_check()
        
        return {
            "authenticated": health["authenticated"],
            "auth_method": health["auth_method"],
            "vault_url": health["vault_url"]
        }
        
    except AuthenticationError as e:
        logger.error(f"Vault authentication test failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"Authentication test error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication test failed: {str(e)}")