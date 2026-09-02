#!/usr/bin/env python3
"""Auditoría mecánica del sistema de diseño del frontend.

Cuenta, sin juicio humano, todo lo que queda fuera de la librería `ui-*` y de
los tokens de `styles.css`. Pensado para ejecutarse en CI: sale con código 1 si
alguna categoría BLOQUEANTE supera su presupuesto.

    python3 tools/auditoria_ui.py            # informe completo
    python3 tools/auditoria_ui.py --breve    # solo los totales

Las categorías con presupuesto > 0 son deuda aceptada y documentada (ver
docs/qa/14); si el número sube, el script falla y obliga a decidirlo.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RAIZ, "src")

# Presupuestos: deuda aceptada hoy. Subirlos exige justificarlo en docs/qa.
# Trinquete: son los valores medidos hoy. El script falla si alguno SUBE, así
# que la deuda no puede crecer en silencio; al bajarla, baja también el número.
PRESUPUESTOS = {
    # Ya en cero: no admiten reincidencia.
    "controles_nativos": 0,      # input/select/textarea de texto en páginas
    "atributos_desconocidos": 0, # atributos que un ui-* ignora en silencio
    "img_sin_alt": 0,
    "iconos_sin_nombre": 0,      # botones solo-icono sin nombre accesible
    "paleta_ajena": 0,           # colores Tailwind fuera de la paleta del sistema
    # Deuda aceptada y documentada (docs/qa/16).
    "file_inputs": 13,           # disparadores y estilos propios
    "radios_nativos": 2,         # control segmentado con radios ocultos
}

# Familias de color de Tailwind que NO pertenecen a la paleta oro/bosque/crema.
PALETA_AJENA = re.compile(
    r"\b(?:bg|text|border|ring|from|via|to|divide|outline|decoration|shadow)-"
    r"(?:slate|zinc|neutral|stone|gray|red|orange|amber|yellow|lime|green|"
    r"emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-"
    r"\d{2,3}\b"
)
# Excepciones toleradas: grises/semánticos que el sistema redefine en styles.css
# y los avisos ámbar/rojo/verde de estados operativos del back office.
PALETA_TOLERADA = re.compile(
    r"\b(?:text-gray-(?:400|500|600|700)|"
    r"(?:bg|border|text)-(?:red|amber|emerald|green|blue)-(?:50|100|200|300|500|600|700|800|900))\b"
)

PALABRAS_SIN_ACENTO = [
    "Configuracion", "Campanas", "Estadisticas", "Ordenes", "Codigo", "codigo",
    "Telefono", "telefono", "sesion", "direccion", "Direccion", "envio",
    "danos", "credito", "articulo", "Articulo", "informacion", "Informacion",
    "validacion", "descripcion", "Descripcion", "numero", "Numero",
]


def htmls_de_pagina():
    """Plantillas de página y de componentes de negocio (excluye los ui-* base)."""
    for base, _, ficheros in os.walk(SRC):
        for f in ficheros:
            if not f.endswith(".html"):
                continue
            ruta = os.path.join(base, f)
            rel = os.path.relpath(ruta, RAIZ)
            if "/components/ui-" in rel.replace(os.sep, "/"):
                continue
            yield rel, open(ruta, encoding="utf-8").read()


def todos_los_htmls():
    for base, _, ficheros in os.walk(SRC):
        for f in ficheros:
            if f.endswith(".html"):
                ruta = os.path.join(base, f)
                yield os.path.relpath(ruta, RAIZ), open(ruta, encoding="utf-8").read()


def linea(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def atributos(tag_src: str):
    """Tokeniza los nombres de atributo de una etiqueta.

    Escanea respetando comillas, así que una expresión como
    [variant]="a === 'x' ? 'p' : 'g'" no produce falsos positivos.
    """
    i, n = 0, len(tag_src)
    while i < n:
        while i < n and tag_src[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        ini = i
        while i < n and tag_src[i] not in " \t\r\n=":
            i += 1
        nombre = tag_src[ini:i]
        while i < n and tag_src[i] in " \t\r\n":
            i += 1
        if i < n and tag_src[i] == "=":
            i += 1
            while i < n and tag_src[i] in " \t\r\n":
                i += 1
            if i < n and tag_src[i] in "\"'":
                comilla = tag_src[i]
                i += 1
                while i < n and tag_src[i] != comilla:
                    i += 1
                i += 1
            else:
                while i < n and tag_src[i] not in " \t\r\n":
                    i += 1
        if nombre:
            yield nombre


def contrato_componentes():
    """Lee los @Input/@Output declarados por cada componente ui-*."""
    contrato = {}
    for base, _, ficheros in os.walk(os.path.join(SRC, "app", "components")):
        for f in ficheros:
            if not f.endswith(".component.ts"):
                continue
            src = open(os.path.join(base, f), encoding="utf-8").read()
            m = re.search(r"selector:\s*'([^']+)'", src)
            if not m:
                continue
            nombres = set(re.findall(r"@Input\([^)]*\)\s*(?:set\s+)?(\w+)", src))
            nombres |= set(re.findall(r"@Input\('([^']+)'\)", src))
            salidas = set(re.findall(r"@Output\([^)]*\)\s*(\w+)", src))
            contrato[m.group(1)] = (nombres, salidas)
    return contrato


# Atributos que Angular o el DOM entienden en cualquier elemento.
GENERICOS = {
    "ngModel", "ngModelChange", "ngIf", "ngFor", "ngForOf", "ngClass", "ngStyle",
    "ngSwitchCase", "ngSwitchDefault", "ngTemplateOutlet", "ngValue",
    "class", "id", "style", "title", "hidden", "tabindex", "role", "disabled",
    "click", "change", "input", "blur", "focus", "keydown", "keyup", "submit",
    "routerLink", "routerLinkActive", "type", "name", "value",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--breve", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--archivo", default=None, help="filtra los hallazgos de un archivo")
    args = ap.parse_args()

    hallazgos = collections.defaultdict(list)

    # ── 1. Controles nativos que deberían ser ui-form-field / ui-checkbox ──
    for rel, src in htmls_de_pagina():
        for m in re.finditer(r"<(input|select|textarea)\b([^>]*)", src, re.DOTALL):
            tag, attrs = m.group(1), m.group(2)
            t = re.search(r'type="([^"]+)"', attrs)
            tipo = t.group(1) if t else "text"
            clave = {"file": "file_inputs", "radio": "radios_nativos"}.get(tipo, "controles_nativos")
            hallazgos[clave].append(f"{rel}:{linea(src, m.start())}  <{tag} type={tipo}>")

    # ── 2. Atributos que un componente ui-* ignora en silencio ──
    contrato = contrato_componentes()
    for rel, src in todos_los_htmls():
        for etiqueta, (entradas, salidas) in contrato.items():
            for m in re.finditer(r"<" + re.escape(etiqueta) + r"(\s[^>]*?)?/?>", src, re.DOTALL):
                for attr in atributos(m.group(1) or ""):
                    base = attr.strip("[]()*#")
                    # (keydown.enter), (click.stop)… son eventos del DOM con
                    # modificador: burbujean desde el interior del componente.
                    base = base.split(".")[0] if attr.startswith("(") else base
                    if (base in entradas or base in salidas or base in GENERICOS
                            or base.startswith(("attr.", "aria-", "data-", "class.", "style."))
                            or not base or base[0].isdigit()):
                        continue
                    hallazgos["atributos_desconocidos"].append(
                        f"{rel}:{linea(src, m.start())}  <{etiqueta} {attr}=…>")

    # ── 3. Fidelidad de paleta y tokens ──
    for rel, src in todos_los_htmls():
        for m in PALETA_AJENA.finditer(src):
            if PALETA_TOLERADA.match(m.group(0)):
                continue
            hallazgos["paleta_ajena"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)}")
        for m in re.finditer(r"shadow-\[[^\]]+\]", src):
            hallazgos["sombras_arbitrarias"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)[:48]}")
        for m in re.finditer(r"rounded-\[[^\]]+\]", src):
            hallazgos["radios_arbitrarios"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)}")
        for m in re.finditer(r"text-\[\d+px\]", src):
            hallazgos["tamanos_arbitrarios"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)}")
        for m in re.finditer(r"#[0-9a-fA-F]{6}\b|rgba?\([^)]*\)", src):
            hallazgos["color_literal"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)[:40]}")

    # ── 4. Accesibilidad mecánica ──
    for rel, src in todos_los_htmls():
        for m in re.finditer(r"<img\b([^>]*)>", src, re.DOTALL):
            if not re.search(r"\[?(?:attr\.)?alt\]?\s*=", m.group(1)):
                hallazgos["img_sin_alt"].append(f"{rel}:{linea(src, m.start())}")
        if "/components/" in rel.replace(os.sep, "/"):
            continue
        for m in re.finditer(r"<(button|ui-button)\b([^>]*?)>(.*?)</\1>", src, re.DOTALL):
            attrs, cuerpo = m.group(2), m.group(3)
            if "<ng-content" in cuerpo:
                continue
            texto = re.sub(r"<[^>]+>", "", cuerpo)
            texto = re.sub(r"\{\{[^}]*\}\}", "X", texto).strip()
            # El nombre accesible depende de la etiqueta: en <ui-button> el
            # atributo suelto aria-label se queda en el host (que no es el
            # <button> real ni recibe el foco), así que NO nombra nada; la
            # única vía válida es el @Input ariaLabel del componente.
            if m.group(1) == "ui-button":
                nombrado = re.search(r"\[?ariaLabel\]?\s*=", attrs)
            else:
                nombrado = re.search(r"(?:\[attr\.)?aria-label\]?\s*=", attrs)
            tiene_nombre = bool(texto) or bool(nombrado) or bool(
                re.search(r"\[?title\]?\s*=", attrs))
            if not tiene_nombre:
                hallazgos["iconos_sin_nombre"].append(f"{rel}:{linea(src, m.start())}")

    # ── 5. Higiene de contenido ──
    for rel, src in todos_los_htmls():
        for m in re.finditer(r">([^<>{}]{2,})<", src):
            texto = m.group(1)
            for palabra in PALABRAS_SIN_ACENTO:
                if re.search(r"\b" + palabra + r"\b", texto):
                    hallazgos["texto_sin_acento"].append(
                        f"{rel}:{linea(src, m.start())}  «{texto.strip()[:52]}»")
                    break
        for m in re.finditer(r"[\U0001F300-\U0001FAFF☀-➿]", src):
            hallazgos["emoji_en_plantilla"].append(f"{rel}:{linea(src, m.start())}  {m.group(0)}")
        for m in re.finditer(r"\b(TODO|FIXME|XXX|HACK)\b", src):
            hallazgos["marcas_pendientes"].append(f"{rel}:{linea(src, m.start())}  {m.group(1)}")

    # ── 6. Dependencias externas en tiempo de ejecución ──
    index = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
    for m in re.finditer(r'<link[^>]+href="(https?://[^"]+)"', index):
        hallazgos["cdn_en_runtime"].append(f"src/index.html:{linea(index, m.start())}  {m.group(1)[:70]}")

    # ── 7. Uso de la librería (contexto, no deuda) ──
    uso = collections.Counter()
    for _, src in todos_los_htmls():
        for etiqueta in contrato:
            uso[etiqueta] += len(re.findall(r"<" + re.escape(etiqueta) + r"\b", src))

    if args.json:
        print(json.dumps({k: len(v) for k, v in hallazgos.items()}, indent=2, ensure_ascii=False))
        return 0

    fallos = []
    print("=" * 72)
    print("AUDITORÍA MECÁNICA DEL SISTEMA DE DISEÑO")
    print("=" * 72)
    if args.archivo:
        clave_filtro = args.archivo.replace("\\", "/")
        hallazgos = collections.defaultdict(
            list,
            {k: [i for i in v if clave_filtro in i] for k, v in hallazgos.items()},
        )
    orden = sorted(hallazgos.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for clave, items in orden:
        presupuesto = PRESUPUESTOS.get(clave)
        n = len(items)
        if presupuesto is None:
            estado = "informativo"
        elif n > presupuesto:
            estado = f"EXCEDE (presupuesto {presupuesto})"
            fallos.append(clave)
        else:
            estado = f"dentro de presupuesto ({presupuesto})"
        print(f"\n{clave:26s} {n:5d}   {estado}")
        if not args.breve:
            tope = n if args.archivo else 8
            for it in items[:tope]:
                print(f"      {it}")
            if n > tope:
                print(f"      … y {n - tope} más")

    print("\n" + "-" * 72)
    print("USO DE LA LIBRERÍA")
    for etiqueta, n in uso.most_common():
        if n:
            print(f"  {etiqueta:22s} {n:5d}")

    print("\n" + "=" * 72)
    if fallos:
        print("RESULTADO: FALLA —", ", ".join(fallos))
        return 1
    print("RESULTADO: OK — ninguna categoría bloqueante excede su presupuesto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
