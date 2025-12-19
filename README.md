# MCP Gateway avec OAuth Keycloak

Architecture complète pour sécuriser des serveurs MCP avec OAuth 2.1, suivant les meilleures pratiques entreprise (séparation Authorization Server / Resource Server).

## 🏗️ Architecture

```
┌──────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Postman    │      │   API Gateway   │ mTLS │  MCP Weather    │
│ (MCP Client) │─────▶│   (Traefik)     │─────▶│    Server       │
└──────┬───────┘      └────────┬────────┘      └─────────────────┘
       │                       │                (Resource Server)
       │ OAuth Flows           │ Token           - Stateless
       │                       │ Validation      - Pas d'endpoints OAuth
       ▼                       ▼                 - Vérifie claims
┌─────────────────────────────────────────┐
│           Keycloak                      │
│      (Authorization Server)             │
│  - /authorize, /token, /register        │
│  - JWKS, Token Introspection            │
└─────────────────────────────────────────┘
```

## 📋 Prérequis

- Docker & Docker Compose
- PowerShell 5.1+
- OpenSSL (pour les certificats mTLS)
- Postman

## 🚀 Démarrage Rapide

### 1. Générer les certificats mTLS

```powershell
cd c:\Users\dsylla\Documents\gateway
.\scripts\generate-certs.ps1
```

### 2. Copier et configurer l'environnement

```powershell
Copy-Item .env.example .env
# Éditez .env si vous avez une clé API OpenWeatherMap
```

### 3. Démarrer les services

```powershell
docker-compose up -d
```

### 4. Vérifier que tout fonctionne

```powershell
# Vérifier les containers
docker-compose ps

# Logs Keycloak (attendre "Running the server")
docker-compose logs -f keycloak
```

### 5. Importer la collection Postman

1. Ouvrir Postman
2. File → Import
3. Sélectionner `postman/MCP-Gateway.postman_collection.json`

## 🔐 Configuration OAuth dans Postman

1. Ouvrir la collection **MCP Gateway - OAuth Demo**
2. Aller dans l'onglet **Authorization**
3. Cliquer sur **Get New Access Token**
4. Se connecter avec:
   - **Username:** `testuser`
   - **Password:** `testpassword123`
5. Cliquer sur **Use Token**

## 📡 URLs des Services

| Service | URL | Description |
|---------|-----|-------------|
| Keycloak Admin | http://localhost:8080 | Console admin (admin/admin) |
| Keycloak Realm | http://localhost:8080/realms/mcp-gateway | Realm OAuth |
| Traefik Dashboard | http://localhost:8081 | Dashboard de la gateway |
| API Gateway | http://localhost:80/mcp | Endpoint MCP protégé |
| MCP Weather (direct) | http://localhost:8000 | Serveur MCP (interne) |

## 🧪 Tests

### Test sans token (401 attendu)

```powershell
curl http://localhost/mcp -X POST `
  -H "Content-Type: application/json" `
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Réponse attendue: `401 Unauthorized` avec header `WWW-Authenticate` contenant `discovery_uri` vers Keycloak.

### Test avec token

Utilisez Postman avec OAuth configuré, ou:

```powershell
# 1. Obtenir un token
$token = (Invoke-RestMethod -Uri "http://localhost:8080/realms/mcp-gateway/protocol/openid-connect/token" `
  -Method POST `
  -Body @{
    grant_type = "password"
    client_id = "mcp-client"
    client_secret = "mcp-client-secret-change-me"
    username = "testuser"
    password = "testpassword123"
  }).access_token

# 2. Appeler l'API MCP
Invoke-RestMethod -Uri "http://localhost/mcp" `
  -Method POST `
  -Headers @{ Authorization = "Bearer $token"; "Content-Type" = "application/json" } `
  -Body '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## 📁 Structure du Projet

```
gateway/
├── docker-compose.yml          # Orchestration Docker
├── .env.example                # Variables d'environnement
├── .gitignore
├── README.md
│
├── mcp-weather-server/         # Serveur MCP Weather
│   ├── Dockerfile
│   ├── weather_server.py       # Code MCP (Resource Server)
│   └── requirements.txt
│
├── auth-service/               # Service de validation OAuth
│   ├── Dockerfile
│   ├── auth_service.py         # ForwardAuth pour Traefik
│   └── requirements.txt
│
├── traefik/                    # API Gateway
│   ├── traefik.yml             # Config statique
│   └── dynamic/
│       ├── http.yml            # Routes et middlewares
│       └── tls.yml             # Configuration TLS/mTLS
│
├── keycloak/                   # Authorization Server
│   └── realm-export.json       # Config realm pré-importée
│
├── certs/                      # Certificats mTLS (générés)
│
├── postman/                    # Collection Postman
│   └── MCP-Gateway.postman_collection.json
│
└── scripts/
    └── generate-certs.ps1      # Script génération certificats
```

## 🔧 Personnalisation

### Ajouter une vraie API météo

1. Obtenir une clé API sur https://openweathermap.org/api
2. Ajouter dans `.env`:
   ```
   OPENWEATHER_API_KEY=votre_cle_api
   ```
3. Redémarrer: `docker-compose restart mcp-weather`

### Ajouter un nouveau serveur MCP

1. Créer un nouveau dossier `mcp-xxx-server/`
2. Implémenter avec FastMCP (comme `weather_server.py`)
3. Ajouter le service dans `docker-compose.yml`
4. Ajouter la route dans `traefik/dynamic/http.yml`

### Changer les secrets (Production)

1. Modifier dans `keycloak/realm-export.json`:
   - `mcp-client` → `secret`
   - `api-gateway` → `secret`
2. Mettre à jour dans `docker-compose.yml`
3. Mettre à jour dans Postman

## 📚 Références

- [Christian Posta - MCP OAuth Spec Analysis](https://blog.christianposta.com/the-updated-mcp-oauth-spec-is-a-mess/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Traefik ForwardAuth](https://doc.traefik.io/traefik/middlewares/http/forwardauth/)

## ⚠️ Notes de Sécurité

- **Développement uniquement** - Les secrets sont en clair pour faciliter les tests
- En production:
  - Utiliser des secrets Kubernetes/Docker Secrets
  - Activer HTTPS avec des certificats valides
  - Désactiver le dashboard Traefik
  - Utiliser une vraie CA pour mTLS
