<#
.SYNOPSIS
    Expone el agente_czz por un túnel temporal de Cloudflare (trycloudflare.com).

.DESCRIPTION
    Levanta `cloudflared tunnel --url http://127.0.0.1:<puerto>` en segundo plano, espera a que
    aparezca la URL pública, la guarda en `tunel.url` y deja el proceso corriendo.

    El servidor de LangGraph tiene que estar arriba antes de ejecutar el script:
        .venv\Scripts\langgraph.exe dev --port 2025

.PARAMETER Port
    Puerto local del servidor del agente. Por defecto 2025.

.PARAMETER TimeoutSegundos
    Cuánto esperar la URL pública. Por defecto 60.

.PARAMETER Detener
    Cierra el túnel abierto anteriormente (lee `tunel.pid`) y borra `tunel.url`.

.EXAMPLE
    .\tunel_cloudflare.ps1

.EXAMPLE
    .\tunel_cloudflare.ps1 -Port 2025

.EXAMPLE
    .\tunel_cloudflare.ps1 -Detener
#>
param(
    [int]$Port = 2025,
    [int]$TimeoutSegundos = 60,
    [switch]$Detener
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$log = Join-Path $raiz "cloudflared.log"
$logSalida = Join-Path $raiz "cloudflared.out.log"
$archivoUrl = Join-Path $raiz "tunel.url"
$archivoPid = Join-Path $raiz "tunel.pid"

function Comprobar-Servidor {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/ok" -TimeoutSec 3 -UseBasicParsing
        return $r.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

# ── Cerrar un túnel anterior ─────────────────────────────────────────────
if ($Detener) {
    if (Test-Path $archivoPid) {
        $pidTunel = (Get-Content -LiteralPath $archivoPid | Select-Object -First 1).Trim()
        if ($pidTunel) {
            try {
                Stop-Process -Id ([int]$pidTunel) -Force -ErrorAction Stop
                Write-Host "Túnel detenido (PID $pidTunel)." -ForegroundColor Green
            }
            catch {
                Write-Host "El proceso $pidTunel ya no estaba corriendo."
            }
        }
        Remove-Item -LiteralPath $archivoPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $archivoUrl -Force -ErrorAction SilentlyContinue
    exit 0
}

# ── Requisitos ───────────────────────────────────────────────────────────
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "cloudflared no está instalado." -ForegroundColor Yellow
    Write-Host "Instálalo con:   winget install Cloudflare.cloudflared"
    Write-Host "Después cierra y abre la terminal (o reinicia VS Code) para que quede en el PATH."
    exit 1
}

if (-not (Comprobar-Servidor)) {
    Write-Host "No responde http://127.0.0.1:$Port/ok" -ForegroundColor Yellow
    Write-Host "Levanta primero el agente:   .venv\Scripts\langgraph.exe dev --port $Port"
    exit 1
}

# ── Abrir el túnel ───────────────────────────────────────────────────────
if (Test-Path $archivoPid) {
    $anterior = (Get-Content -LiteralPath $archivoPid | Select-Object -First 1).Trim()
    if ($anterior -and (Get-Process -Id ([int]$anterior) -ErrorAction SilentlyContinue)) {
        Write-Host "Ya hay un túnel abierto (PID $anterior). Ciérralo con: .\tunel_cloudflare.ps1 -Detener" -ForegroundColor Yellow
        if (Test-Path $archivoUrl) { Write-Host "URL actual: $(Get-Content -LiteralPath $archivoUrl)" }
        exit 0
    }
}

Remove-Item -LiteralPath $log, $logSalida, $archivoUrl, $archivoPid -Force -ErrorAction SilentlyContinue

Write-Host "Abriendo el túnel hacia http://127.0.0.1:$Port ..."
$proceso = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://127.0.0.1:$Port", "--no-autoupdate" `
    -RedirectStandardError $log -RedirectStandardOutput $logSalida `
    -PassThru -WindowStyle Hidden

$url = $null
$limite = (Get-Date).AddSeconds($TimeoutSegundos)
while ((Get-Date) -lt $limite -and -not $url) {
    if (Test-Path $log) {
        try {
            $texto = Get-Content -LiteralPath $log -Raw -ErrorAction Stop
            $encontrada = [regex]::Match($texto, 'https://[a-z0-9-]+\.trycloudflare\.com')
            if ($encontrada.Success) { $url = $encontrada.Value }
        }
        catch {
            # cloudflared puede tener el log abierto mientras escribe: se reintenta.
        }
    }
    if ($proceso.HasExited) { break }
    Start-Sleep -Milliseconds 500
}

if (-not $url) {
    Write-Host "No pude leer la URL pública. Revisa $log" -ForegroundColor Red
    if (-not $proceso.HasExited) { $proceso.Kill() }
    exit 1
}

Set-Content -LiteralPath $archivoUrl -Value $url -Encoding ascii
Set-Content -LiteralPath $archivoPid -Value $proceso.Id -Encoding ascii

# ── Comprobar que el agente responde por la URL pública ─────────────────
try {
    $asistentes = Invoke-RestMethod -Method Post -Uri "$url/assistants/search" `
        -ContentType "application/json" -Body '{"graph_id":"agente_czz"}' -TimeoutSec 30
    $assistantId = $asistentes[0].assistant_id
    Invoke-RestMethod "$url/.well-known/agent-card.json?assistant_id=$assistantId" -TimeoutSec 30 | Out-Null
    $estado = "agente_czz visible por el túnel"
}
catch {
    $estado = "el túnel abrió, pero el agente todavía no responde: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Túnel activo: $url" -ForegroundColor Green
Write-Host "PID de cloudflared: $($proceso.Id)"
Write-Host "Estado: $estado"
Write-Host ""
Write-Host "Para que el notebook use la URL pública:" -ForegroundColor Cyan
Write-Host "  `$env:A2A_CZZ_URL = `"$url`""
Write-Host ""
Write-Host "Comprobaciones manuales:"
Write-Host "  Invoke-RestMethod -Method Post -Uri `"$url/assistants/search`" -ContentType `"application/json`" -Body '{`"graph_id`":`"agente_czz`"}'"
Write-Host "  Invoke-RestMethod `"$url/.well-known/agent-card.json?assistant_id=<uuid>`""
Write-Host ""
Write-Host "Avisos:"
Write-Host "  - La URL cambia cada vez que se abre el túnel; no se guarda en el repositorio."
Write-Host "  - La tarjeta anuncia la URL local (127.0.0.1). Un cliente remoto debe reescribirla"
Write-Host "    a la URL del túnel; el notebook de la etapa 3 ya lo hace."
Write-Host "  - Cierra el túnel al terminar:  .\tunel_cloudflare.ps1 -Detener"
