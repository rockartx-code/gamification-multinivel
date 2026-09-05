#!/usr/bin/env bash
# Comprueba que el mundo simulado está listo ANTES de lanzar agentes.
# Falla ruidosamente: una ronda contra la API equivocada no mide nada.
set -u
ok=0
paso() { printf '  ✓ %s\n' "$1"; }
falla() { printf '  ✗ %s\n' "$1"; ok=1; }

echo "Comprobando el mundo simulado…"

grep -q "apiBaseUrl: 'http://localhost:4400'" gamificacion-multinivel-f/src/environments/environment.ts \
  && paso "environment.ts apunta al backend local" \
  || falla "environment.ts NO apunta a http://localhost:4400 (el frontend hablaría con producción)"

curl -s -o /dev/null -w '' localhost:4400/__sim/reloj && paso "backend en :4400 responde ($(curl -s localhost:4400/__sim/reloj | head -c 60))" \
  || falla "el backend de la simulación no responde en :4400"

code=$(curl -s -o /dev/null -w '%{http_code}' localhost:4321)
[ "$code" = "200" ] && paso "frontend en :4321 responde" || falla "el frontend no responde en :4321 (código $code)"

# Lo que de verdad importa: el bundle que se está sirviendo.
if curl -s localhost:4321/main.js | grep -qo 'execute-api\.[a-z0-9-]*\.amazonaws\.com'; then
  falla "el bundle servido todavía apunta a la API de AWS: reinicia ng serve tras corregir environment.ts"
else
  paso "el bundle servido no apunta a AWS"
fi

n=$(curl -s localhost:4400/catalog/product -H 'Authorization: Bearer sim-superadmin-token' 2>/dev/null | grep -o '"productId"' | wc -l)
[ "$n" -gt 0 ] && paso "catálogo sembrado ($n productos)" || falla "no hay catálogo: corre python3 sim/semilla.py"

[ -f sim/credenciales.json ] && paso "credenciales.json existe" || falla "falta sim/credenciales.json (semilla)"

# Guarda 15 (docs/qa/27 §4): el arnés tiene que poner el navegador en la hora del
# mundo. Si no, la persona mide el mes contable, "días desde la última compra" y
# el selector de meses con la fecha de la máquina, y lo apunta como defecto del
# producto. Abre UN navegador (regla del arnés: nunca dos) y lo cierra; no deja
# bitácora ni perfil. Se salta si el mundo no está en pie: ya falló arriba.
if [ $ok -eq 0 ]; then
  reloj=$(node sim/lib/comprobar-reloj.mjs 2>&1 | tail -1)
  case "$reloj" in
    OK*)    paso "reloj del navegador == reloj del mundo — ${reloj#OK }" ;;
    *)      falla "reloj del navegador desviado del mundo — ${reloj#FALLA }" ;;
  esac
else
  printf '  · reloj del navegador: sin comprobar (el mundo ya no está listo)\n'
fi

[ $ok -eq 0 ] && echo "Mundo listo." || echo "MUNDO NO LISTO: no lances agentes."
exit $ok
