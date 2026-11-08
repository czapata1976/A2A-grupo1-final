param(
    [Parameter(Mandatory = $true)]
    [string]$Dominio,
    [string]$Nombre = "a2a-grupo1",
    [int[]]$Puertos = @(2025, 2026, 2027, 2028),
    [string[]]$Subdominios = @("czz", "bryhan", "alejandra", "cm")
)

# Configura un túnel NOMBRADO de Cloudflare con hostnames estables para los cuatro agentes.
#
# Uso:
#   .\scripts\configurar_tunel_nombrado.ps1 -Dominio "a2a.midominio.cl"
#
# Requisitos:
#   1. Un dominio administrado en Cloudflare (plan gratuito sirve).
#   2. Haber autorizado cloudflared una vez:  cloudflared tunnel login
#   3. Los cuatro agentes levantados en los puertos 2025-2028.
#
# Genera cloudflared/config.yml y deja el valor de A2A_SERVIDORES listo para Heroku.

$ErrorActionPreference = "Stop"

if ($Puertos.Count -ne $Subdominios.Count) {
    throw "Debes indicar la misma cantidad de puertos y subdominios (recibidos: $($Puertos.Count) y $($Subdominios.Count))."
}

$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$carpeta = Join-Path $raiz "cloudflared"
New-Item -ItemType Directory -Force -Path $carpeta | Out-Null

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw "No se encontró cloudflared. Instálalo con: winget install Cloudflare.cloudflared"
}

$cert = Join-Path $env:USERPROFILE ".cloudflared\cert.pem"
if (-not (Test-Path -LiteralPath $cert)) {
    Write-Host "Falta la autorización de Cloudflare." -ForegroundColor Yellow
    Write-Host "Ejecuta una vez y completa el navegador:" -ForegroundColor Yellow
    Write-Host "  cloudflared tunnel login" -ForegroundColor Cyan
    Write-Host "Después vuelve a correr este script." -ForegroundColor Yellow
    exit 1
}

Write-Host "Buscando el túnel '$Nombre' ..." -ForegroundColor Cyan
$lista = cloudflared tunnel list --output json | ConvertFrom-Json
$tunel = $lista | Where-Object { $_.name -eq $Nombre } | Select-Object -First 1

if (-not $tunel) {
    Write-Host "Creando el túnel '$Nombre' ..." -ForegroundColor Cyan
    cloudflared tunnel create $Nombre | Out-Null
    $lista = cloudflared tunnel list --output json | ConvertFrom-Json
    $tunel = $lista | Where-Object { $_.name -eq $Nombre } | Select-Object -First 1
}
if (-not $tunel) {
    throw "No se pudo crear ni encontrar el túnel '$Nombre'."
}

$id = $tunel.id
Write-Host "Túnel: $Nombre ($id)" -ForegroundColor Green

# DNS: cada subdominio apunta al túnel (idempotente; si ya existe, CNAME ya está).
$hostnames = @()
foreach ($sub in $Subdominios) {
    $hostname = "$sub.$Dominio"
    $hostnames += $hostname
    Write-Host "Enrutando $hostname -> túnel $Nombre ..." -ForegroundColor Cyan
    $salida = cloudflared tunnel route dns $Nombre $hostname 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "No se pudo crear el DNS de $hostname : $salida"
    }
}

# Configuración del túnel: un ingress por agente y 404 para el resto.
$lineas = @(
    "# Generado por scripts/configurar_tunel_nombrado.ps1",
    "tunnel: $id",
    "credentials-file: $((Join-Path $env:USERPROFILE ".cloudflared\$id.json") -replace '\\', '/')",
    "",
    "ingress:"
)
for ($i = 0; $i -lt $hostnames.Count; $i++) {
    $lineas += "  - hostname: $($hostnames[$i])"
    $lineas += "    service: http://127.0.0.1:$($Puertos[$i])"
}
$lineas += "  - service: http_status:404"

$config = Join-Path $carpeta "config.yml"
$lineas | Set-Content -LiteralPath $config -Encoding UTF8

$urls = ($hostnames | ForEach-Object { "https://$_" }) -join ","
$archivo = Join-Path $carpeta "a2a-servidores.txt"
"A2A_SERVIDORES=$urls" | Set-Content -LiteralPath $archivo -Encoding UTF8

Write-Host ""
Write-Host "Configuración escrita en cloudflared/config.yml" -ForegroundColor Green
Write-Host "Config Var para Heroku:" -ForegroundColor Cyan
Write-Host "A2A_SERVIDORES=$urls"
Write-Host ""
Write-Host "Levanta el túnel con:  .\scripts\tunel_nombrado.ps1" -ForegroundColor Cyan
Write-Host "Aviso: las URLs ya no cambian aunque reinicies el PC." -ForegroundColor Yellow
