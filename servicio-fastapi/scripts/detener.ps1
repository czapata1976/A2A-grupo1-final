param(
    [int]$Puerto = 8000,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$conexiones = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
if (-not $conexiones) {
    Write-Host "No hay ningún proceso escuchando en el puerto $Puerto." -ForegroundColor DarkGray
    exit 0
}

$pids = $conexiones | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procesoId in $pids) {
    $proceso = Get-Process -Id $procesoId -ErrorAction SilentlyContinue
    if (-not $proceso) { continue }
    if (-not $Force) {
        $respuesta = Read-Host "Detener $($proceso.ProcessName) (PID $procesoId) en el puerto $Puerto? [s/N]"
        if ($respuesta -notmatch "^[sS]") {
            Write-Host "Omitido PID $procesoId." -ForegroundColor DarkGray
            continue
        }
    }
    Stop-Process -Id $procesoId -Force
    Write-Host "Detenido PID $procesoId ($($proceso.ProcessName))." -ForegroundColor Green
}
