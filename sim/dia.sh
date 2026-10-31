#!/bin/bash
# Avanza el reloj del mundo simulado y deja una foto del estado.
# Uso: ./dia.sh 2026-09-03T09:00:00
set -e
FECHA="$1"; [ -z "$FECHA" ] && { echo "uso: dia.sh <fecha ISO>"; exit 1; }
curl -s -X POST localhost:4400/__sim/reloj -H 'Content-Type: application/json' -d "{\"fecha\":\"$FECHA\"}"
echo; curl -s localhost:4400/__sim/estado
echo; echo "correos totales: $(cat buzon/*.json 2>/dev/null | grep -c '"asunto"')"
