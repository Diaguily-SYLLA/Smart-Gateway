"""
MCP Weather Server - Resource Server Only (Stateless)
Following enterprise best practices: No OAuth endpoints here.
Token validation is handled by the API Gateway.

This server exposes a JSON-RPC 2.0 API compatible with MCP protocol.
"""

import os
from datetime import datetime
from typing import Any, Optional
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# FastAPI app
app = FastAPI(
    title="MCP Weather Server",
    description="Weather data MCP server - Resource Server Only",
    version="1.0.0"
)

# OpenWeatherMap API configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")


# ============================================
# Pydantic Models for JSON-RPC 2.0
# ============================================

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str
    method: str
    params: dict = {}


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str
    result: Any = None
    error: Optional[dict] = None


# ============================================
# Helper Functions
# ============================================

def get_user_scopes(x_user_scopes: str = "") -> list:
    """Extract scopes from header."""
    if x_user_scopes:
        return x_user_scopes.split(" ")
    return ["weather:read"]  # Default for demo


def check_scope(scopes: list, required_scope: str) -> bool:
    """Check if user has required scope."""
    # Accept both weather:read and weather-scope
    if required_scope == "weather:read":
        return "weather:read" in scopes or "weather-scope" in scopes
    return required_scope in scopes


def get_mock_forecast(city: str, country_code: str) -> str:
    """Return mock weather data for demo purposes."""
    return f"""
🌤️ Météo pour {city}, {country_code}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Conditions: Partiellement nuageux
🌡️ Température: 12°C
🤔 Ressenti: 10°C
💧 Humidité: 65%
💨 Vent: 15 km/h
📅 Mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def get_weather_alerts(region: str) -> str:
    """Return mock weather alerts."""
    return f"""
⚠️ Alertes Météo pour {region}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 Vigilance Jaune - Vent
   Région: Normandie, Bretagne
   Valide: {datetime.now().strftime('%Y-%m-%d')} 06:00 - 18:00
   
🟢 Aucune alerte majeure
   Le reste du territoire est en vigilance verte.
   
📅 Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def get_uv_index(city: str, country_code: str) -> str:
    """Return mock UV index."""
    return f"""
☀️ Indice UV pour {city}, {country_code}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Indice UV: 5
📈 Niveau: Modéré
🛡️ Recommandation: Protection nécessaire: lunettes de soleil, crème solaire SPF 30+
📅 Date: {datetime.now().strftime('%Y-%m-%d')}
"""


# ============================================
# MCP Tool Definitions
# ============================================

MCP_TOOLS = [
    {
        "name": "get_weather_forecast",
        "description": "Get current weather forecast for a city",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city (e.g., Paris, Lyon, Marseille)"
                },
                "country_code": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code (default: FR)",
                    "default": "FR"
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "get_weather_alerts",
        "description": "Get active weather alerts for a region",
        "inputSchema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Region or country name",
                    "default": "France"
                }
            }
        }
    },
    {
        "name": "get_uv_index",
        "description": "Get UV index for a city",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city"
                },
                "country_code": {
                    "type": "string",
                    "description": "ISO country code",
                    "default": "FR"
                }
            },
            "required": ["city"]
        }
    }
]


# ============================================
# API Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp-weather-server",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/info")
async def server_info():
    """Server information endpoint."""
    return {
        "name": "MCP Weather Server",
        "version": "1.0.0",
        "description": "Weather data MCP server - Stateless Resource Server",
        "tools": [t["name"] for t in MCP_TOOLS]
    }


@app.post("/")
@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    x_user_sub: str = Header(default="anonymous", alias="X-User-Sub"),
    x_user_email: str = Header(default="", alias="X-User-Email"),
    x_user_roles: str = Header(default="", alias="X-User-Roles"),
    x_user_scopes: str = Header(default="weather:read", alias="X-User-Scopes")
):
    """
    Main MCP JSON-RPC 2.0 endpoint.
    Handles tool listing and tool execution.
    """
    try:
        body = await request.json()
        rpc_request = JsonRpcRequest(**body)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(e)
                }
            }
        )
    
    scopes = get_user_scopes(x_user_scopes)
    
    # Handle different MCP methods
    if rpc_request.method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_request.id,
            "result": {
                "tools": MCP_TOOLS
            }
        }
    
    elif rpc_request.method == "tools/call":
        tool_name = rpc_request.params.get("name")
        arguments = rpc_request.params.get("arguments", {})
        
        # Check scope
        if not check_scope(scopes, "weather:read"):
            return {
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "error": {
                    "code": -32600,
                    "message": "Insufficient permissions",
                    "data": "Required scope: weather:read"
                }
            }
        
        # Execute tool
        if tool_name == "get_weather_forecast":
            city = arguments.get("city", "Paris")
            country_code = arguments.get("country_code", "FR")
            result = get_mock_forecast(city, country_code)
        
        elif tool_name == "get_weather_alerts":
            region = arguments.get("region", "France")
            result = get_weather_alerts(region)
        
        elif tool_name == "get_uv_index":
            city = arguments.get("city", "Paris")
            country_code = arguments.get("country_code", "FR")
            result = get_uv_index(city, country_code)
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Unknown tool: {tool_name}"
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": rpc_request.id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ],
                "user": {
                    "sub": x_user_sub,
                    "email": x_user_email
                }
            }
        }
    
    elif rpc_request.method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_request.id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "mcp-weather-server",
                    "version": "1.0.0"
                }
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": rpc_request.id,
            "error": {
                "code": -32601,
                "message": "Method not found",
                "data": f"Unknown method: {rpc_request.method}"
            }
        }


if __name__ == "__main__":
    import ssl
    
    port = int(os.getenv("PORT", "8000"))
    use_mtls = os.getenv("MTLS_ENABLED", "false").lower() == "true"
    
    if use_mtls:
        # mTLS Configuration
        ssl_certfile = os.getenv("SSL_CERTFILE", "/certs/mcp-weather.crt")
        ssl_keyfile = os.getenv("SSL_KEYFILE", "/certs/mcp-weather.key")
        ssl_ca_certs = os.getenv("SSL_CA_CERTS", "/certs/ca.crt")
        
        # Create SSL context with client certificate verification
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
        ssl_context.load_verify_locations(ssl_ca_certs)
        ssl_context.verify_mode = ssl.CERT_REQUIRED  # Require client certificate
        
        print(f"🔐 Starting MCP Weather Server with mTLS on port {port}")
        print(f"   Server cert: {ssl_certfile}")
        print(f"   CA cert: {ssl_ca_certs}")
        print(f"   Client cert verification: REQUIRED")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            ssl_ca_certs=ssl_ca_certs,
            ssl_cert_reqs=ssl.CERT_REQUIRED
        )
    else:
        print(f"🌤️ Starting MCP Weather Server (HTTP) on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
