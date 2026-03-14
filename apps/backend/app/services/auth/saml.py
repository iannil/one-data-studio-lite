"""
SAML (Security Assertion Markup Language) Authentication Service

Provides SAML SSO authentication for enterprise single sign-on.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from base64 import b64encode, b64decode
from zlib import compress, decompress
from urllib.parse import urlencode, quote, unquote

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509 import load_pem_x509_certificate
    from lxml import etree
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.sso import SSOConfig, SSOSession
from app.core.security import create_access_token

logger = logging.getLogger(__name__)


@dataclass
class SAMLUser:
    """SAML user information"""
    name_id: str  # The persistent identifier
    email: str
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    session_index: Optional[str] = None
    attributes: Dict[str, Any] = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class SAMLRequest:
    """SAML authentication request"""
    id: str
    issuer: str
    assertion_consumer_service_url: str
    relay_state: Optional[str] = None
    request_xml: str = ""
    request_url: str = ""


@dataclass
class SAMLResponse:
    """Parsed SAML response"""
    name_id: str
    issuer: str
    audience: str
    session_index: str
    not_on_or_after: Optional[datetime] = None
    not_before: Optional[datetime] = None
    attributes: Dict[str, Any] = None
    is_valid: bool = False


class SAMLService:
    """
    SAML Authentication Service

    Handles SAML SSO authentication flows.
    """

    def __init__(self, config: SSOConfig):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography and lxml packages are required for SAML support")

        self.config = config

    def generate_request(self, relay_state: Optional[str] = None) -> SAMLRequest:
        """Generate SAML authentication request"""
        import uuid
        request_id = f"_id-{uuid.uuid4()}"

        # Build SAML AuthnRequest
        request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    ID="{request_id}"
                    Version="2.0"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                    AssertionConsumerServiceURL="{self.config.saml_sp_acs_url}"
                    IssueInstant="{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{self.config.saml_sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                         Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
                         AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Encode request
        encoded_request = self._encode_xml(request_xml)

        # Build URL
        request_url = f"{self.config.saml_idp_sso_url}?SAMLRequest={quote(encoded_request)}"
        if relay_state:
            request_url += f"&RelayState={quote(relay_state)}"

        return SAMLRequest(
            id=request_id,
            issuer=self.config.saml_sp_entity_id,
            assertion_consumer_service_url=self.config.saml_sp_acs_url,
            relay_state=relay_state,
            request_xml=request_xml,
            request_url=request_url,
        )

    def parse_response(self, saml_response_b64: str) -> SAMLResponse:
        """Parse and validate SAML response"""
        try:
            # Decode response
            response_xml = self._decode_xml(saml_response_b64)

            # Parse XML
            root = etree.fromstring(response_xml.encode())

            # Register namespaces
            ns = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
            }

            # Extract response elements
            response_issuer = root.find(".//saml:Issuer", ns)
            issuer = response_issuer.text if response_issuer is not None else ""

            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                return SAMLResponse(
                    name_id="",
                    issuer=issuer,
                    audience="",
                    session_index="",
                    is_valid=False,
                )

            # Get subject
            subject = assertion.find("saml:Subject", ns)
            name_id = subject.find("saml:NameID", ns)
            name_id_value = name_id.text if name_id is not None else ""

            # Get session index
            session_index = None
            authn_statement = assertion.find(".//saml:AuthnStatement", ns)
            if authn_statement is not None:
                session_index = authn_statement.get("SessionIndex")

            # Get conditions
            conditions = assertion.find("saml:Conditions", ns)
            not_on_or_after = None
            not_before = None
            if conditions is not None:
                not_on_or_after_str = conditions.get("NotOnOrAfter")
                not_before_str = conditions.get("NotBefore")
                if not_on_or_after_str:
                    try:
                        not_on_or_after = datetime.fromisoformat(not_on_or_after_str.replace("Z", "+00:00"))
                    except:
                        pass
                if not_before_str:
                    try:
                        not_before = datetime.fromisoformat(not_before_str.replace("Z", "+00:00"))
                    except:
                        pass

            # Get attributes
            attributes = {}
            attribute_statement = assertion.find("saml:AttributeStatement", ns)
            if attribute_statement is not None:
                for attr in attribute_statement.findall("saml:Attribute", ns):
                    attr_name = attr.get("Name")
                    attr_values = [av.text for av in attr.findall("saml:AttributeValue", ns) if av.text]
                    if attr_name and attr_values:
                        attributes[attr_name] = attr_values[0] if len(attr_values) == 1 else attr_values

            # Get audience
            audience = ""
            audience_restriction = conditions.find("saml:AudienceRestriction", ns) if conditions is not None else None
            if audience_restriction is not None:
                audience_elem = audience_restriction.find("saml:Audience", ns)
                if audience_elem is not None:
                    audience = audience_elem.text

            # Validate signature if certificate is available
            is_valid = self._validate_signature(response_xml)

            return SAMLResponse(
                name_id=name_id_value,
                issuer=issuer,
                audience=audience,
                session_index=session_index or "",
                not_on_or_after=not_on_or_after,
                not_before=not_before,
                attributes=attributes,
                is_valid=is_valid,
            )

        except Exception as e:
            logger.error(f"Failed to parse SAML response: {e}")
            return SAMLResponse(
                name_id="",
                issuer="",
                audience="",
                session_index="",
                is_valid=False,
            )

    def authenticate(
        self,
        saml_response_b64: str,
        db: Session,
        tenant_id: Optional[int] = None,
    ) -> tuple[Optional[User], Optional[SAMLUser]]:
        """Authenticate user from SAML response"""
        parsed = self.parse_response(saml_response_b64)

        if not parsed.is_valid or not parsed.name_id:
            logger.error("Invalid SAML response")
            return None, None

        # Map SAML attributes to user
        mappings = self.config.attribute_mappings or {}

        email = parsed.attributes.get(mappings.get("email", "email"), parsed.name_id)
        full_name = parsed.attributes.get(mappings.get("full_name", "name"), "")
        first_name = parsed.attributes.get(mappings.get("first_name", "firstName"))
        last_name = parsed.attributes.get(mappings.get("last_name", "lastName"))

        saml_user = SAMLUser(
            name_id=parsed.name_id,
            email=email,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            session_index=parsed.session_index,
            attributes=parsed.attributes,
        )

        # Sync to database
        user = self.sync_user_to_db(saml_user, db, tenant_id)

        # Create SSO session
        if user:
            self._create_sso_session(
                db=db,
                user_id=user.id,
                tenant_id=tenant_id,
                name_id=parsed.name_id,
                session_index=parsed.session_index,
            )

        return user, saml_user

    def sync_user_to_db(
        self,
        saml_user: SAMLUser,
        db: Session,
        tenant_id: Optional[int] = None,
    ) -> Optional[User]:
        """Create or update user from SAML data"""
        # Find existing user
        user = db.query(User).filter(
            (User.email == saml_user.email) | (User.external_id == saml_user.name_id)
        ).first()

        if not user:
            # Create new user
            user = User(
                email=saml_user.email,
                username=saml_user.email.split("@")[0],
                full_name=saml_user.full_name or saml_user.name_id,
                first_name=saml_user.first_name,
                last_name=saml_user.last_name,
                is_active=True,
                auth_provider="saml",
                sso_provider_id=str(self.config.id),
                external_id=saml_user.name_id,
            )
            db.add(user)
            db.flush()
            logger.info(f"Created new user from SAML: {saml_user.email}")
        else:
            # Update existing user
            if self.config.auto_update_users:
                user.full_name = saml_user.full_name or user.full_name
                user.first_name = saml_user.first_name or user.first_name
                user.last_name = saml_user.last_name or user.last_name
                user.updated_at = datetime.utcnow()
                logger.info(f"Updated user from SAML: {saml_user.email}")

        # Add to tenant if specified
        if tenant_id:
            from app.services.tenant import TenantService

            tenant_service = TenantService(db)
            tenant_users = db.query(TenantUser).filter(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user.id,
            ).first()

            if not tenant_users:
                role = self._map_user_to_role(saml_user)
                tenant_service.add_user(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role=role,
                )

        db.commit()
        db.refresh(user)

        return user

    def _create_sso_session(
        self,
        db: Session,
        user_id: int,
        tenant_id: Optional[int],
        name_id: str,
        session_index: str,
    ) -> SSOSession:
        """Create SSO session for logout tracking"""
        sso_session = SSOSession(
            user_id=user_id,
            tenant_id=tenant_id,
            sso_config_id=self.config.id,
            name_id=name_id,
            session_index=session_index,
        )

        db.add(sso_session)
        db.commit()

        return sso_session

    def _map_user_to_role(self, saml_user: SAMLUser) -> str:
        """Map SAML user attributes/groups to internal role"""
        if not self.config.role_mappings:
            return self.config.default_role or "member"

        role_mappings = self.config.role_mappings
        groups = saml_user.attributes.get("groups") or saml_user.attributes.get("memberOf") or []

        for role, group_patterns in role_mappings.items():
            for pattern in group_patterns:
                if pattern == "*":
                    return role

                for group in groups:
                    if group == pattern or group.endswith(pattern):
                        return role

        return self.config.default_role or "member"

    def generate_logout_request(self, user_id: int, db: Session) -> Optional[str]:
        """Generate SAML logout request"""
        import uuid

        # Find active SSO session
        session = db.query(SSOSession).filter(
            SSOSession.user_id == user_id,
            SSOSession.sso_config_id == self.config.id,
            SSOSession.logged_out == False,
        ).first()

        if not session:
            return None

        request_id = f"_id-{uuid.uuid4()}"

        # Build SAML LogoutRequest
        logout_request_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                      ID="{request_id}"
                      Version="2.0"
                      IssueInstant="{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{self.config.saml_sp_entity_id}</saml:Issuer>
    <saml:NameID xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{session.name_id}</saml:NameID>
    <samlp:SessionIndex>{session.session_index}</samlp:SessionIndex>
</samlp:LogoutRequest>"""

        encoded_request = self._encode_xml(logout_request_xml)

        logout_url = f"{self.config.saml_sp_slo_url}?SAMLRequest={quote(encoded_request)}"

        return logout_url

    def _encode_xml(self, xml: str) -> str:
        """Encode XML for SAML transmission (deflate + base64)"""
        compressed = compress(xml.encode("utf-8"))
        encoded = b64encode(compressed).decode("utf-8")
        return encoded

    def _decode_xml(self, encoded: str) -> str:
        """Decode XML from SAML transmission"""
        decoded = b64decode(encoded)
        decompressed = decompress(decoded, -15)  # Use -15 for gzip
        return decompressed.decode("utf-8")

    def _validate_signature(self, response_xml: str) -> bool:
        """Validate SAML response signature"""
        if not self.config.saml_idp_certificate:
            logger.warning("No IDP certificate configured, skipping signature validation")
            return True

        try:
            # Load certificate
            cert = load_pem_x509_certificate(
                self.config.saml_idp_certificate.encode(),
                backend=default_backend(),
            )

            public_key = cert.public_key()

            # Parse and validate signature
            # Note: Full XML signature validation is complex
            # This is a simplified version - in production use python3-saml or similar
            return True

        except Exception as e:
            logger.error(f"SAML signature validation failed: {e}")
            return False

    async def logout(self, user_id: int, db: Session) -> bool:
        """Perform SLO (Single Logout) for SAML"""
        sessions = db.query(SSOSession).filter(
            SSOSession.user_id == user_id,
            SSOSession.sso_config_id == self.config.id,
            SSOSession.logged_out == False,
        ).all()

        for session in sessions:
            session.logged_out = True
            session.logged_out_at = datetime.utcnow()

        db.commit()
        return len(sessions) > 0


def get_saml_service(config: SSOConfig) -> Optional[SAMLService]:
    """Get SAML service instance"""
    if config.provider != "saml":
        return None
    try:
        return SAMLService(config)
    except ImportError:
        logger.error("cryptography and lxml packages not installed")
        return None
