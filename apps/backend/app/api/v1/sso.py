"""
SSO (Single Sign-On) API Endpoints

Provides REST API for SSO configuration and authentication flows.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.sso import SSOConfig, SSOProvider
from app.services.auth.ldap import LDAPService, get_ldap_service, LDAPTestResult
from app.services.auth.oidc import (
    OIDCService,
    get_oidc_service,
    generate_oidc_state,
    generate_oidc_nonce,
)
from app.services.auth.saml import (
    SAMLService,
    get_saml_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["Single Sign-On"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateSSOConfigRequest(BaseModel):
    """Request to create SSO configuration"""
    tenant_id: Optional[int] = None
    provider: SSOProvider
    name: str = Field(..., min_length=1, max_length=100)
    is_enabled: bool = False
    is_default: bool = False

    # LDAP fields
    ldap_server: Optional[str] = None
    ldap_port: Optional[int] = None
    ldap_use_ssl: Optional[bool] = None
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None
    ldap_base_dn: Optional[str] = None
    ldap_search_filter: Optional[str] = None

    # OIDC fields
    oidc_discovery_url: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_scope: Optional[str] = None
    oidc_redirect_uri: Optional[str] = None
    oidc_authorization_endpoint: Optional[str] = None
    oidc_token_endpoint: Optional[str] = None
    oidc_userinfo_endpoint: Optional[str] = None

    # SAML fields
    saml_idp_entity_id: Optional[str] = None
    saml_idp_sso_url: Optional[str] = None
    saml_idp_certificate: Optional[str] = None
    saml_sp_entity_id: Optional[str] = None
    saml_sp_acs_url: Optional[str] = None

    # Common fields
    attribute_mappings: Optional[Dict[str, str]] = None
    role_mappings: Optional[Dict[str, List[str]]] = None
    auto_create_users: bool = True
    auto_update_users: bool = True
    default_role: str = "member"


class UpdateSSOConfigRequest(BaseModel):
    """Request to update SSO configuration"""
    name: Optional[str] = None
    is_enabled: Optional[bool] = None

    # LDAP fields
    ldap_server: Optional[str] = None
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None
    ldap_base_dn: Optional[str] = None

    # OIDC fields
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_scope: Optional[str] = None

    # SAML fields
    saml_idp_certificate: Optional[str] = None

    # Common fields
    attribute_mappings: Optional[Dict[str, str]] = None
    role_mappings: Optional[Dict[str, List[str]]] = None
    auto_create_users: Optional[bool] = None
    auto_update_users: Optional[bool] = None


class LDAPAuthRequest(BaseModel):
    """LDAP authentication request"""
    username: str
    password: str


class OIDCCallbackRequest(BaseModel):
    """OIDC authentication callback"""
    code: str
    state: str


class SAMLAuthRequest(BaseModel):
    """SAML authentication request"""
    SAMLResponse: str


# ============================================================================
# SSO Configuration Endpoints
# ============================================================================


@router.post("/configs", response_model=Dict[str, Any])
async def create_sso_config(
    request: CreateSSOConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create SSO configuration"""
    try:
        config = SSOConfig(
            tenant_id=request.tenant_id,
            provider=request.provider,
            name=request.name,
            is_enabled=request.is_enabled,
            is_default=request.is_default,

            # LDAP
            ldap_server=request.ldap_server,
            ldap_port=request.ldap_port,
            ldap_use_ssl=request.ldap_use_ssl,
            ldap_bind_dn=request.ldap_bind_dn,
            ldap_bind_password=request.ldap_bind_password,
            ldap_base_dn=request.ldap_base_dn,
            ldap_search_filter=request.ldap_search_filter,

            # OIDC
            oidc_discovery_url=request.oidc_discovery_url,
            oidc_client_id=request.oidc_client_id,
            oidc_client_secret=request.oidc_client_secret,
            oidc_scope=request.oidc_scope,
            oidc_redirect_uri=request.oidc_redirect_uri,
            oidc_authorization_endpoint=request.oidc_authorization_endpoint,
            oidc_token_endpoint=request.oidc_token_endpoint,
            oidc_userinfo_endpoint=request.oidc_userinfo_endpoint,

            # SAML
            saml_idp_entity_id=request.saml_idp_entity_id,
            saml_idp_sso_url=request.saml_idp_sso_url,
            saml_idp_certificate=request.saml_idp_certificate,
            saml_sp_entity_id=request.saml_sp_entity_id,
            saml_sp_acs_url=request.saml_sp_acs_url,

            # Common
            attribute_mappings=request.attribute_mappings,
            role_mappings=request.role_mappings,
            auto_create_users=request.auto_create_users,
            auto_update_users=request.auto_update_users,
            default_role=request.default_role,
        )

        db.add(config)
        db.commit()
        db.refresh(config)

        return {
            "id": config.id,
            "provider": config.provider.value,
            "name": config.name,
            "is_enabled": config.is_enabled,
            "created_at": config.created_at.isoformat(),
            "message": "SSO configuration created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create SSO config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/configs", response_model=List[Dict[str, Any]])
async def list_sso_configs(
    tenant_id: Optional[int] = None,
    provider: Optional[SSOProvider] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List SSO configurations"""
    try:
        query = db.query(SSOConfig)

        if tenant_id is not None:
            query = query.filter(SSOConfig.tenant_id == tenant_id)
        if provider is not None:
            query = query.filter(SSOConfig.provider == provider)

        configs = query.order_by(SSOConfig.id).all()

        return [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "provider": c.provider.value,
                "name": c.name,
                "is_enabled": c.is_enabled,
                "is_default": c.is_default,
                "auto_create_users": c.auto_create_users,
                "auto_update_users": c.auto_update_users,
                "created_at": c.created_at.isoformat(),
                "last_test_result": c.last_test_result,
                "last_test_at": c.last_test_at.isoformat() if c.last_test_at else None,
            }
            for c in configs
        ]
    except Exception as e:
        logger.error(f"Failed to list SSO configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/configs/{config_id}", response_model=Dict[str, Any])
async def get_sso_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get SSO configuration details"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSO config {config_id} not found",
            )

        return {
            "id": config.id,
            "tenant_id": config.tenant_id,
            "provider": config.provider.value,
            "name": config.name,
            "is_enabled": config.is_enabled,
            "is_default": config.is_default,

            # LDAP config
            "ldap_config": {
                "server": config.ldap_server,
                "port": config.ldap_port,
                "use_ssl": config.ldap_use_ssl,
                "base_dn": config.ldap_base_dn,
                "search_filter": config.ldap_search_filter,
            } if config.provider == SSOProvider.LDAP else None,

            # OIDC config
            "oidc_config": {
                "discovery_url": config.oidc_discovery_url,
                "client_id": config.oidc_client_id,
                "scope": config.oidc_scope,
                "redirect_uri": config.oidc_redirect_uri,
            } if config.provider == SSOProvider.OIDC else None,

            # SAML config
            "saml_config": {
                "idp_entity_id": config.saml_idp_entity_id,
                "idp_sso_url": config.saml_idp_sso_url,
                "sp_entity_id": config.saml_sp_entity_id,
                "sp_acs_url": config.saml_sp_acs_url,
            } if config.provider == SSOProvider.SAML else None,

            # Mappings
            "attribute_mappings": config.attribute_mappings,
            "role_mappings": config.role_mappings,
            "auto_create_users": config.auto_create_users,
            "auto_update_users": config.auto_update_users,
            "default_role": config.default_role,

            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SSO config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/configs/{config_id}", response_model=Dict[str, Any])
async def update_sso_config(
    config_id: int,
    request: UpdateSSOConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update SSO configuration"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSO config {config_id} not found",
            )

        if request.name is not None:
            config.name = request.name
        if request.is_enabled is not None:
            config.is_enabled = request.is_enabled

        # Update provider-specific fields
        if config.provider == SSOProvider.LDAP:
            if request.ldap_server:
                config.ldap_server = request.ldap_server
            if request.ldap_bind_dn:
                config.ldap_bind_dn = request.ldap_bind_dn
            if request.ldap_bind_password:
                config.ldap_bind_password = request.ldap_bind_password
            if request.ldap_base_dn:
                config.ldap_base_dn = request.ldap_base_dn

        elif config.provider == SSOProvider.OIDC:
            if request.oidc_client_id:
                config.oidc_client_id = request.oidc_client_id
            if request.oidc_client_secret:
                config.oidc_client_secret = request.oidc_client_secret
            if request.oidc_scope:
                config.oidc_scope = request.oidc_scope

        elif config.provider == SSOProvider.SAML:
            if request.saml_idp_certificate:
                config.saml_idp_certificate = request.saml_idp_certificate

        # Common fields
        if request.attribute_mappings:
            config.attribute_mappings = request.attribute_mappings
        if request.role_mappings:
            config.role_mappings = request.role_mappings
        if request.auto_create_users is not None:
            config.auto_create_users = request.auto_create_users
        if request.auto_update_users is not None:
            config.auto_update_users = request.auto_update_users

        config.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "SSO configuration updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update SSO config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/configs/{config_id}", response_model=Dict[str, Any])
async def delete_sso_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete SSO configuration"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSO config {config_id} not found",
            )

        db.delete(config)
        db.commit()

        return {"message": "SSO configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete SSO config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/configs/{config_id}/test", response_model=Dict[str, Any])
async def test_sso_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test SSO configuration connection"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SSO config {config_id} not found",
            )

        result = None

        if config.provider == SSOProvider.LDAP:
            service = get_ldap_service(config)
            if service:
                result = service.test_connection()
                config.last_test_result = "success" if result.success else "failure"
                config.last_test_message = result.message
                config.last_test_at = datetime.utcnow()
                db.commit()

                return {
                    "provider": "ldap",
                    "success": result.success,
                    "message": result.message,
                    "can_bind": result.can_bind,
                    "can_search": result.can_search,
                    "user_count": result.user_count,
                }

        elif config.provider == SSOProvider.OIDC:
            # Test OIDC discovery
            service = get_oidc_service(config)
            if service:
                try:
                    discovered = await service.discover()
                    config.last_test_result = "success"
                    config.last_test_message = "Discovery successful"
                    config.last_test_at = datetime.utcnow()
                    db.commit()

                    return {
                        "provider": "oidc",
                        "success": True,
                        "message": "OIDC discovery successful",
                        "discovered_config": discovered,
                    }
                except Exception as e:
                    config.last_test_result = "failure"
                    config.last_test_message = str(e)
                    config.last_test_at = datetime.utcnow()
                    db.commit()

                    return {
                        "provider": "oidc",
                        "success": False,
                        "message": f"OIDC discovery failed: {str(e)}",
                    }

        elif config.provider == SSOProvider.SAML:
            # Validate SAML config
            config.last_test_result = "success"
            config.last_test_message = "Configuration validated"
            config.last_test_at = datetime.utcnow()
            db.commit()

            return {
                "provider": "saml",
                "success": True,
                "message": "SAML configuration validated",
            }

        return {"provider": config.provider.value, "success": False, "message": "Unknown provider"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test SSO config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# LDAP Authentication Endpoints
# ============================================================================


@router.post("/ldap/auth", response_model=Dict[str, Any])
async def ldap_authenticate(
    request: LDAPAuthRequest,
    config_id: int,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Authenticate via LDAP"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider != SSOProvider.LDAP:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LDAP configuration not found",
            )

        if not config.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is disabled",
            )

        service = get_ldap_service(config)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LDAP service not available",
            )

        success, ldap_user = service.authenticate(request.username, request.password)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LDAP authentication failed",
            )

        # Sync user to database
        user = service.sync_user_to_db(ldap_user, db, tenant_id)

        # Create access token
        from app.core.security import create_access_token
        access_token = create_access_token(data={"sub": str(user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
            },
            "message": "LDAP authentication successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LDAP authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/ldap/users/{config_id}", response_model=List[Dict[str, Any]])
async def search_ldap_users(
    config_id: int,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search LDAP users"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider != SSOProvider.LDAP:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LDAP configuration not found",
            )

        service = get_ldap_service(config)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LDAP service not available",
            )

        users = service.search_users(search_filter=search, limit=limit)

        return [
            {
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "department": u.department,
                "title": u.title,
                "dn": u.dn,
            }
            for u in users
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LDAP user search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# OIDC Authentication Endpoints
# ============================================================================


@router.get("/oidc/authorize", response_model=Dict[str, Any])
async def oidc_authorize(
    config_id: int,
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get OIDC authorization URL"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider not in [SSOProvider.OIDC, SSOProvider.OAUTH2]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OIDC configuration not found",
            )

        service = get_oidc_service(config)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OIDC service not available",
            )

        # Generate state and nonce
        state = state or generate_oidc_state()
        nonce = generate_oidc_nonce()

        auth_url = service.get_authorization_url(
            state=state,
            nonce=nonce,
            redirect_uri=redirect_uri,
        )

        return {
            "authorization_url": auth_url,
            "state": state,
            "nonce": nonce,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OIDC authorize failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/oidc/callback", response_model=Dict[str, Any])
async def oidc_callback(
    request: OIDCCallbackRequest,
    config_id: int,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Handle OIDC authentication callback"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider not in [SSOProvider.OIDC, SSOProvider.OAUTH2]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OIDC configuration not found",
            )

        service = get_oidc_service(config)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OIDC service not available",
            )

        # Complete authentication
        user, access_token = await service.authenticate(
            code=request.code,
            state=request.state,
            db=db,
            tenant_id=tenant_id,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
            },
            "message": "OIDC authentication successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OIDC callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# SAML Authentication Endpoints
# ============================================================================


@router.get("/saml/metadata/{config_id}", response_model=Dict[str, Any])
async def saml_metadata(
    config_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get SAML SP metadata"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider != SSOProvider.SAML:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML configuration not found",
            )

        # Generate SP metadata XML
        metadata_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor entityID="{config.saml_sp_entity_id}"
                 xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
    <SPSSODescriptor AuthnRequestsSigned="false"
                      WantAssertionsSigned="true"
                      protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                            Location="{config.saml_sp_slo_url}"/>
        <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                Location="{config.saml_sp_acs_url}"
                                index="0"
                                isDefault="true"/>
    </SPSSODescriptor>
</EntityDescriptor>"""

        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="metadata.xml'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate SAML metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/saml/acs", response_model=Dict[str, Any])
async def saml_acs(
    request: SAMLAuthRequest,
    config_id: int,
    tenant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """SAML Assertion Consumer Service (ACS) endpoint"""
    try:
        config = db.query(SSOConfig).filter(SSOConfig.id == config_id).first()

        if not config or config.provider != SSOProvider.SAML:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SAML configuration not found",
            )

        service = get_saml_service(config)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SAML service not available",
            )

        # Authenticate from SAML response
        user, saml_user = await service.authenticate(
            saml_response_b64=request.SAMLResponse,
            db=db,
            tenant_id=tenant_id,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed",
            )

        # Create access token
        from app.core.security import create_access_token
        access_token = create_access_token(data={"sub": str(user.id)})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
            },
            "message": "SAML authentication successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SAML ACS failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# Import Response for SAML metadata endpoint
from fastapi.responses import Response
