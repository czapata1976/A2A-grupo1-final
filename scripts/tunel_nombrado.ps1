param(
    [string]$Nombre = "a2a-grupo1",
    [string]$Config = "",
    [switch]$Detener
)

# Levanta o detiene el túnel nombrado de Cloudflare (URLs estables).
#
# Uso:
#   .\scripts\tunel_nombrado.ps1
#   .\scripts\tunel_nombrado.ps1 -Detener
#
# Antes hay que ejecutar una vez:
#   .\scripts\configurar_tunel_nombrado.ps1 -Dominio "a2a.midominio.cl"

$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$carpeta = Join-Path $raiz "cloudflared"
if (-not $Config) { $Config = Join-Path $carpeta "config.yml" }
$archivoPid = Join-Path $carpeta "tunel.pid"
$log = Join-Path $carpeta "tunel.log"

if ($Detener) {
    if (Test-Path -LiteralPath $archivoPid) {
        $pidTunel = (Get-Content -LiteralPath $archivoPid -Raw).Trim()
        if ($pidTunel) {
            try {
                Stop-Process -Id ([int]$pidTunel) -Force -ErrorAction Stop
                Write-Host "Túnel detenido (PID $pidTunel)."
            } catch {
                Write-Host "El proceso $pidTunel ya no estaba corriendo."
            }
        }
        Remove-Item -LiteralPath $archivoPid -Force
    } else {
        Write-Host "No hay túnel registrado."
    }
    return
}

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw "No se encontró cloudflared. Instálalo con: winget install Cloudflare.cloudflared"
}
if (-not (Test-Path -LiteralPath $Config)) {
    throw "No existe $Config. Ejecuta primero scripts\configurar_tunel_nombrado.ps1 -Dominio <tu-dominio>."
}

$proceso = Start-Process -FilePath $cloudflared.Source `
    -ArgumentList @("tunnel", "--config", $Config, "run", $Nombre) `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err" `
    -WindowStyle Hidden -PassThru
$proceso.Id | Set-Content -LiteralPath $archivoPid -Encoding ASCII

Write-Host "Túnel '$Nombre' iniciado (PID $($proceso.Id))." -ForegroundColor Green
Write-Host "Log: $log"
if (Test-Path (Join-Path $carpeta "a2a-servidores.txt")) {
    Write-Host ""
    Write-Host "Recuerda que A2A_SERVIDORES debe ser:" -ForegroundColor Cyan
    Get-Content -LiteralPath (Join-Path $carpeta "a2a-servidores.txt")
}
