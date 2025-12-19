"""
MCP Calculator Server - Resource Server Only (Stateless)
Following enterprise best practices: No OAuth endpoints here.
Token validation is handled by the API Gateway.

This server exposes a JSON-RPC 2.0 API compatible with MCP protocol.
"""

import os
import math
from datetime import datetime
from typing import Any, Optional
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# FastAPI app
app = FastAPI(
    title="MCP Calculator Server",
    description="Calculator MCP server - Resource Server Only",
    version="1.0.0"
)


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
    return ["calculator:read"]  # Default for demo


def check_scope(scopes: list, required_scope: str) -> bool:
    """Check if user has required scope."""
    # Accept multiple scope formats
    if required_scope == "calculator:read":
        return "calculator:read" in scopes or "calculator-scope" in scopes or "openid" in scopes
    return required_scope in scopes


def calculate_add(a: float, b: float) -> str:
    """Addition de deux nombres."""
    result = a + b
    return f"""
🧮 Calcul: Addition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {a} + {b}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def calculate_subtract(a: float, b: float) -> str:
    """Soustraction de deux nombres."""
    result = a - b
    return f"""
🧮 Calcul: Soustraction
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {a} - {b}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def calculate_multiply(a: float, b: float) -> str:
    """Multiplication de deux nombres."""
    result = a * b
    return f"""
🧮 Calcul: Multiplication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {a} × {b}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def calculate_divide(a: float, b: float) -> str:
    """Division de deux nombres."""
    if b == 0:
        return f"""
🧮 Calcul: Division
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {a} ÷ {b}
❌ Erreur: Division par zéro impossible!
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    result = a / b
    return f"""
🧮 Calcul: Division
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {a} ÷ {b}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def calculate_power(base: float, exponent: float) -> str:
    """Puissance d'un nombre."""
    result = math.pow(base, exponent)
    return f"""
🧮 Calcul: Puissance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: {base}^{exponent}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


def calculate_sqrt(number: float) -> str:
    """Racine carrée d'un nombre."""
    if number < 0:
        return f"""
🧮 Calcul: Racine Carrée
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: √{number}
❌ Erreur: Racine carrée d'un nombre négatif impossible!
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    result = math.sqrt(number)
    return f"""
🧮 Calcul: Racine Carrée
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Opération: √{number}
✅ Résultat: {result}
📅 Calculé le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""


# ============================================
# MCP Tool Definitions
# ============================================

MCP_TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers together (a + b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "subtract",
        "description": "Subtract two numbers (a - b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Number to subtract"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers (a × b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "divide",
        "description": "Divide two numbers (a ÷ b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "number",
                    "description": "Dividend (number to divide)"
                },
                "b": {
                    "type": "number",
                    "description": "Divisor (number to divide by)"
                }
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "power",
        "description": "Calculate power of a number (base^exponent)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base": {
                    "type": "number",
                    "description": "Base number"
                },
                "exponent": {
                    "type": "number",
                    "description": "Exponent"
                }
            },
            "required": ["base", "exponent"]
        }
    },
    {
        "name": "sqrt",
        "description": "Calculate square root of a number",
        "inputSchema": {
            "type": "object",
            "properties": {
                "number": {
                    "type": "number",
                    "description": "Number to calculate square root of"
                }
            },
            "required": ["number"]
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
        "service": "mcp-calculator-server",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/info")
async def server_info():
    """Server information endpoint."""
    return {
        "name": "MCP Calculator Server",
        "version": "1.0.0",
        "description": "Calculator MCP server - Stateless Resource Server",
        "tools": [t["name"] for t in MCP_TOOLS]
    }


@app.post("/")
@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    x_user_sub: str = Header(default="anonymous", alias="X-User-Sub"),
    x_user_email: str = Header(default="", alias="X-User-Email"),
    x_user_roles: str = Header(default="", alias="X-User-Roles"),
    x_user_scopes: str = Header(default="calculator:read", alias="X-User-Scopes")
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
        if not check_scope(scopes, "calculator:read"):
            return {
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "error": {
                    "code": -32600,
                    "message": "Insufficient permissions",
                    "data": "Required scope: calculator:read"
                }
            }
        
        # Execute tool
        if tool_name == "add":
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            result = calculate_add(a, b)
        
        elif tool_name == "subtract":
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            result = calculate_subtract(a, b)
        
        elif tool_name == "multiply":
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            result = calculate_multiply(a, b)
        
        elif tool_name == "divide":
            a = float(arguments.get("a", 0))
            b = float(arguments.get("b", 0))
            result = calculate_divide(a, b)
        
        elif tool_name == "power":
            base = float(arguments.get("base", 0))
            exponent = float(arguments.get("exponent", 0))
            result = calculate_power(base, exponent)
        
        elif tool_name == "sqrt":
            number = float(arguments.get("number", 0))
            result = calculate_sqrt(number)
        
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
                    "name": "mcp-calculator-server",
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
    
    port = int(os.getenv("PORT", "8001"))
    use_mtls = os.getenv("MTLS_ENABLED", "false").lower() == "true"
    
    if use_mtls:
        # mTLS Configuration
        ssl_certfile = os.getenv("SSL_CERTFILE", "/certs/mcp-calculator.crt")
        ssl_keyfile = os.getenv("SSL_KEYFILE", "/certs/mcp-calculator.key")
        ssl_ca_certs = os.getenv("SSL_CA_CERTS", "/certs/ca.crt")
        
        print(f"🔐 Starting MCP Calculator Server with mTLS on port {port}")
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
        print(f"🧮 Starting MCP Calculator Server (HTTP) on port {port}")
        uvicorn.run(app, host="0.0.0.0", port=port)
