#!/usr/bin/env python3
"""Junta las bitácoras de sim/metricas/*.json en tablas comparables.

Uso:  python3 sim/metricas.py            → resumen en pantalla
      python3 sim/metricas.py --markdown → tablas listas para el informe
"""
import json, glob, os, sys, statistics

RAIZ = os.path.dirname(os.path.abspath(__file__))


def cargar():
    datos = []
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "metricas", "*.json"))):
        with open(ruta) as f:
            d = json.load(f)
        d["_archivo"] = os.path.basename(ruta)
        datos.append(d)
    return datos


def _prom(valores):
    valores = [v for v in valores if isinstance(v, (int, float))]
    return round(statistics.mean(valores), 1) if valores else None


def resumen_persona(d):
    tareas = d.get("tareas", [])
    logradas = [t for t in tareas if t.get("logrado")]
    pensamientos = [p for t in tareas for p in t.get("pensamientos", [])] + [
        n for n in d.get("notas", []) if "segundosDesdeLoAnterior" in n]
    reflexion = sum(p.get("segundosDesdeLoAnterior", 0) for p in pensamientos)
    primeros = [p["primerClicMs"] for p in d.get("pantallas", []) if p.get("primerClicMs")]
    return {
        "persona": d.get("persona"),
        "rol": d.get("rol"),
        "dispositivo": d.get("dispositivo"),
        "min": d.get("duracionMin"),
        "tareas": len(tareas),
        "logradas": len(logradas),
        "abandonadas": len(tareas) - len(logradas),
        "clics": d["totales"].get("clics", 0),
        "teclas": d["totales"].get("teclas", 0),
        "pantallas": d["totales"].get("pantallas", 0),
        "recargas": d["totales"].get("recargas", 0),
        "atrases": d["totales"].get("atrases", 0),
        "dudas": sum(len(t.get("dudas", [])) for t in tareas) + len([n for n in d.get("notas", []) if "pantalla" in n]),
        "atorones": sum(len(t.get("atorones", [])) for t in tareas),
        "reintentos": sum(t.get("reintentos", 0) for t in tareas),
        "preguntas_soporte": len([q for q in d.get("preguntas", []) if q.get("aQuien") in ("soporte", "helpdesk")]),
        "preguntas_superior": len([q for q in d.get("preguntas", []) if q.get("aQuien") not in ("soporte", "helpdesk")]),
        "errores_vistos": len(d.get("erroresEnPantalla", [])),
        "reflexion_s": reflexion,
        "pensamientos": len(pensamientos),
        "lectura_media_s": round(_prom(primeros) / 1000, 1) if primeros and _prom(primeros) else None,
        "facilidad": _prom([t.get("facilidad") for t in tareas]),
        "confianza": _prom([t.get("confianza") for t in tareas]),
        "estetica": _prom([(d.get("estetica") or {}).get(k) for k in
                           ("primeraImpresion", "confianzaQueTransmite", "legibilidad", "coherencia")]),
        "recomendaria": (d.get("estetica") or {}).get("recomendarias"),
        "emocion_neta": _prom([e["intensidad"] * (1 if e["emocion"] in POSITIVAS else -1) for e in d.get("emociones", [])]),
    }


POSITIVAS = {"alivio", "orgullo", "gusto", "confianza", "sorpresa agradable", "tranquilidad", "satisfacción", "alegría"}


def filas_tareas(datos):
    filas = []
    for d in datos:
        for t in d.get("tareas", []):
            filas.append({
                "persona": d.get("persona", "").split(",")[0],
                "quiero": t.get("quiero"),
                "logrado": "sí" if t.get("logrado") else "no",
                "clics": t.get("clics"),
                "seg": t.get("segundos"),
                "pensamientos": len(t.get("pensamientos", [])),
                "reflexion_s": sum(p.get("segundosDesdeLoAnterior", 0) for p in t.get("pensamientos", [])),
                "dudas": len(t.get("dudas", [])),
                "atorones": len(t.get("atorones", [])),
                "reintentos": t.get("reintentos", 0),
                "preguntas": len(t.get("preguntas", [])),
                "facilidad": t.get("facilidad"),
                "confianza": t.get("confianza"),
            })
    return filas


def tabla_md(filas, columnas, titulos=None):
    titulos = titulos or columnas
    out = ["| " + " | ".join(titulos) + " |", "|" + "---|" * len(columnas)]
    for f in filas:
        out.append("| " + " | ".join("—" if f.get(c) is None else str(f.get(c)) for c in columnas) + " |")
    return "\n".join(out)


def main():
    datos = cargar()
    if not datos:
        print("No hay bitácoras en sim/metricas/. Cada agente-persona escribe la suya al cerrar el navegador.")
        return 1
    resumenes = [resumen_persona(d) for d in datos]
    md = "--markdown" in sys.argv

    cols = ["persona", "rol", "dispositivo", "min", "tareas", "logradas", "clics", "teclas", "pantallas",
            "lectura_media_s", "reflexion_s", "dudas", "atorones", "reintentos", "preguntas_soporte",
            "preguntas_superior", "errores_vistos", "facilidad", "confianza", "estetica"]
    print("## Por persona\n")
    print(tabla_md(resumenes, cols))

    print("\n## Por tarea\n")
    tcols = ["persona", "quiero", "logrado", "clics", "seg", "reflexion_s", "pensamientos", "dudas",
             "atorones", "reintentos", "preguntas", "facilidad", "confianza"]
    print(tabla_md(filas_tareas(datos), tcols))

    tareas = filas_tareas(datos)
    logradas = [t for t in tareas if t["logrado"] == "sí"]
    print("\n## Totales\n")
    print(f"- Personas: {len(datos)} · tareas intentadas: {len(tareas)} · logradas: {len(logradas)} "
          f"({round(100*len(logradas)/max(1,len(tareas)))} %)")
    print(f"- Clics por tarea lograda (mediana): {statistics.median([t['clics'] for t in logradas if t['clics']] or [0])}")
    print(f"- Segundos de reflexión antes de actuar (total): {sum(t['reflexion_s'] for t in tareas)}")
    print(f"- Preguntas a soporte: {sum(r['preguntas_soporte'] for r in resumenes)} · "
          f"a un superior o conocido: {sum(r['preguntas_superior'] for r in resumenes)}")
    print(f"- Atorones: {sum(r['atorones'] for r in resumenes)} · reintentos: {sum(r['reintentos'] for r in resumenes)} · "
          f"recargas: {sum(r['recargas'] for r in resumenes)}")
    f = _prom([r["facilidad"] for r in resumenes]); c = _prom([r["confianza"] for r in resumenes])
    e = _prom([r["estetica"] for r in resumenes]); n = _prom([r["recomendaria"] for r in resumenes])
    print(f"- Facilidad media (1 difícil – 7 fácil): {f} · confianza en que quedó guardado (1–5): {c}")
    print(f"- Estética media (1–10): {e} · recomendaría (0–10): {n}")

    if not md:
        print("\n## Emociones\n")
        for d in datos:
            for em in d.get("emociones", []):
                print(f"- {d['persona'].split(',')[0]}: {em['emocion']} ({em['intensidad']}/5) — {em['porque']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
