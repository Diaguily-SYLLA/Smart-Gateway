# Script de generation de certificats mTLS pour MCP Gateway
# Genere: CA, certificat gateway, certificat MCP server

param(
    [string]$OutputDir = ".\certs",
    [int]$ValidDays = 365,
    [string]$CaName = "MCP-Gateway-CA",
    [string]$GatewayName = "gateway",
    [string]$McpServerName = "mcp-weather"
)

$ErrorActionPreference = "Stop"

Write-Host "Generating mTLS certificates for MCP Gateway" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "Directory created: $OutputDir" -ForegroundColor Green
}

# Check if OpenSSL is available
$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    Write-Host "OpenSSL is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Install via: winget install OpenSSL.Light" -ForegroundColor Yellow
    exit 1
}

Write-Host "OpenSSL found: $($openssl.Source)" -ForegroundColor Green

# === 1. Generate CA (Certificate Authority) ===
Write-Host ""
Write-Host "1. Generating CA (Certificate Authority)..." -ForegroundColor Yellow

$caKeyPath = Join-Path $OutputDir "ca.key"
$caCrtPath = Join-Path $OutputDir "ca.crt"

# Generate CA private key
& openssl genrsa -out $caKeyPath 4096

# Generate CA certificate
$caSubj = "/CN=" + $CaName + "/O=MCP-Gateway/C=FR"
& openssl req -new -x509 -days $ValidDays -key $caKeyPath -out $caCrtPath -subj $caSubj

Write-Host "   CA generated: $caCrtPath" -ForegroundColor Green

# === 2. Generate Gateway certificate ===
Write-Host ""
Write-Host "2. Generating Gateway certificate..." -ForegroundColor Yellow

$gwKeyPath = Join-Path $OutputDir "gateway.key"
$gwCsrPath = Join-Path $OutputDir "gateway.csr"
$gwCrtPath = Join-Path $OutputDir "gateway.crt"
$gwExtPath = Join-Path $OutputDir "gateway.ext"

# Create extensions file for SAN
$gwExtContent = @"
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = gateway
DNS.3 = traefik
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
"@
$gwExtContent | Out-File -FilePath $gwExtPath -Encoding ASCII -NoNewline

# Generate private key
& openssl genrsa -out $gwKeyPath 2048

# Generate CSR
$gwSubj = "/CN=" + $GatewayName + "/O=MCP-Gateway/C=FR"
& openssl req -new -key $gwKeyPath -out $gwCsrPath -subj $gwSubj

# Sign with CA
& openssl x509 -req -in $gwCsrPath -CA $caCrtPath -CAkey $caKeyPath -CAcreateserial -out $gwCrtPath -days $ValidDays -extfile $gwExtPath

# Clean up temporary files
Remove-Item $gwCsrPath, $gwExtPath -ErrorAction SilentlyContinue

Write-Host "   Gateway certificate generated: $gwCrtPath" -ForegroundColor Green

# === 3. Generate MCP Server certificate ===
Write-Host ""
Write-Host "3. Generating MCP Server certificate..." -ForegroundColor Yellow

$mcpKeyPath = Join-Path $OutputDir "mcp-weather.key"
$mcpCsrPath = Join-Path $OutputDir "mcp-weather.csr"
$mcpCrtPath = Join-Path $OutputDir "mcp-weather.crt"
$mcpExtPath = Join-Path $OutputDir "mcp-weather.ext"

# Create extensions file for SAN
$mcpExtContent = @"
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = mcp-weather
DNS.2 = localhost
IP.1 = 127.0.0.1
"@
$mcpExtContent | Out-File -FilePath $mcpExtPath -Encoding ASCII -NoNewline

# Generate private key
& openssl genrsa -out $mcpKeyPath 2048

# Generate CSR
$mcpSubj = "/CN=" + $McpServerName + "/O=MCP-Gateway/C=FR"
& openssl req -new -key $mcpKeyPath -out $mcpCsrPath -subj $mcpSubj

# Sign with CA
& openssl x509 -req -in $mcpCsrPath -CA $caCrtPath -CAkey $caKeyPath -CAcreateserial -out $mcpCrtPath -days $ValidDays -extfile $mcpExtPath

# Clean up temporary files
Remove-Item $mcpCsrPath, $mcpExtPath -ErrorAction SilentlyContinue

Write-Host "   MCP Server certificate generated: $mcpCrtPath" -ForegroundColor Green

# === Summary ===
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "All certificates generated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Files generated in $OutputDir :" -ForegroundColor White

Get-ChildItem $OutputDir -Filter "*.crt" | ForEach-Object {
    Write-Host "   CERT: $($_.Name)" -ForegroundColor Cyan
}
Get-ChildItem $OutputDir -Filter "*.key" | ForEach-Object {
    Write-Host "   KEY:  $($_.Name)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "   - Private keys (*.key) must remain confidential" -ForegroundColor Yellow
Write-Host "   - In production use certificates signed by a real CA" -ForegroundColor Yellow

Write-Host ""
Write-Host "Next step: docker-compose up -d" -ForegroundColor Green
