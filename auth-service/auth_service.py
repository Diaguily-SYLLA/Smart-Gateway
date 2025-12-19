"""
Auth Service - OAuth Token Verification Service
This service validates tokens against Keycloak and returns user claims
to be forwarded to MCP servers by Traefik.
"""

from flask import Flask, request, jsonify
import requests
import os
import jwt
from functools import wraps

app = Flask(__name__)

# Keycloak configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "mcp-gateway")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "api-gateway")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "api-gateway-secret-change-me")

# Cache for JWKS
_jwks_cache = None


def get_keycloak_jwks():
    """Fetch JWKS from Keycloak for token verification."""
    global _jwks_cache
    if _jwks_cache is None:
        jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


def get_discovery_metadata():
    """Return OAuth discovery metadata pointing to Keycloak."""
    return {
        "issuer": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}",
        "authorization_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth",
        "token_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        "introspection_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect",
        "userinfo_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo",
        "end_session_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout",
        "jwks_uri": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs",
        "registration_endpoint": f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/clients-registrations/openid-connect",
        "scopes_supported": ["openid", "profile", "email", "weather:read", "weather:alerts"],
        "response_types_supported": ["code", "token", "id_token", "code token", "code id_token"],
        "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "code_challenge_methods_supported": ["S256"]
    }


def introspect_token(token: str) -> dict:
    """Introspect token using Keycloak's introspection endpoint."""
    introspect_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"
    
    response = requests.post(
        introspect_url,
        data={
            "token": token,
            "token_type_hint": "access_token"
        },
        auth=(KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET),
        timeout=10
    )
    response.raise_for_status()
    return response.json()


@app.route("/.well-known/oauth-authorization-server", methods=["GET"])
def oauth_discovery():
    """OAuth 2.0 Authorization Server Metadata endpoint."""
    return jsonify(get_discovery_metadata())


@app.route("/verify", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def verify_token():
    """
    Verify OAuth token for Traefik ForwardAuth.
    Returns 200 with user headers if valid, 401 if invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        # Return 401 with WWW-Authenticate header pointing to Keycloak
        discovery_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
        auth_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
        
        response = jsonify({
            "error": "unauthorized",
            "error_description": "Bearer token required",
            "authorization_uri": auth_url,
            "discovery_uri": discovery_url
        })
        response.status_code = 401
        response.headers["WWW-Authenticate"] = (
            f'Bearer realm="mcp-gateway", '
            f'error="invalid_token", '
            f'error_description="Bearer token required", '
            f'authorization_uri="{auth_url}", '
            f'discovery_uri="{discovery_url}"'
        )
        return response
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    
    try:
        # Introspect token with Keycloak
        token_info = introspect_token(token)
        
        if not token_info.get("active", False):
            raise ValueError("Token is not active")
        
        # Extract user information
        sub = token_info.get("sub", "")
        email = token_info.get("email", "")
        roles = token_info.get("realm_access", {}).get("roles", [])
        scope = token_info.get("scope", "")
        
        # Return success with user headers
        response = jsonify({"status": "ok"})
        response.status_code = 200
        response.headers["X-User-Sub"] = sub
        response.headers["X-User-Email"] = email
        response.headers["X-User-Roles"] = ",".join(roles)
        response.headers["X-User-Scopes"] = scope
        
        return response
        
    except Exception as e:
        # Return 401 with WWW-Authenticate header
        discovery_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
        auth_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
        
        response = jsonify({
            "error": "unauthorized",
            "error_description": str(e),
            "authorization_uri": auth_url,
            "discovery_uri": discovery_url
        })
        response.status_code = 401
        response.headers["WWW-Authenticate"] = (
            f'Bearer realm="mcp-gateway", '
            f'error="invalid_token", '
            f'error_description="Token validation failed", '
            f'authorization_uri="{auth_url}", '
            f'discovery_uri="{discovery_url}"'
        )
        return response


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "auth-service",
        "keycloak_url": KEYCLOAK_URL,
        "realm": KEYCLOAK_REALM
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
