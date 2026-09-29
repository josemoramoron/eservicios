#!/bin/bash
# Empuja el codigo a GitHub (respaldo/historial) y luego a produccion (dispara el
# deploy en la Pi via el hook post-receive). Equivalente en Ubuntu de
# deploy-eservicios.ps1 (Windows) -- misma logica: aborta si el primer push falla,
# nunca toca produccion si origin no quedo actualizado.
set -u

echo "-> Pushing a GitHub (origin)..."
git push origin main
if [ $? -ne 0 ]; then
    echo "Fallo el push a origin, abortando (no se toco produccion)."
    exit 1
fi

echo "-> Pushing a produccion (Pi)..."
git push production main
if [ $? -ne 0 ]; then
    echo "Fallo el push a produccion. Revisa la salida del hook arriba."
    exit 1
fi

echo "Listo: GitHub actualizado y deploy disparado en la Pi."
