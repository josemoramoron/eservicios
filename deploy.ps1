# Empuja el código a GitHub (respaldo/historial) y luego a producción (dispara el deploy en la Pi).
$ErrorActionPreference = "Stop"

Write-Host "-> Pushing a GitHub (origin)..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Fallo el push a origin, abortando (no se toco produccion)." -ForegroundColor Red
    exit 1
}

Write-Host "-> Pushing a produccion (Pi)..." -ForegroundColor Cyan
git push production main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Fallo el push a produccion. Revisa la salida del hook arriba." -ForegroundColor Red
    exit 1
}

Write-Host "Listo: GitHub actualizado y deploy disparado en la Pi." -ForegroundColor Green
