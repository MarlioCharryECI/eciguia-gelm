"""Lógica pura de las herramientas (sin MCP), para poder probarla aparte.

El servidor MCP (mcp_server.py) solo expone estas funciones.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import date

from eciguia import config

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
STOPWORDS = {"de", "del", "la", "el", "los", "las", "y", "o", "a", "en", "para", "por", "con",
             "que", "cuando", "cual", "es", "fecha", "hasta", "se", "un", "una", "al", "mi"}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _human_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def load_calendar() -> list[dict]:
    with open(config.CALENDAR_PATH, encoding="utf-8") as file:
        return json.load(file)["eventos"]


def _status(inicio: str, fin: str, today: date) -> dict:
    """Días que faltan para el evento y si ya pasó, para responder "¿cuánto falta?" sin otra herramienta."""
    start, end = date.fromisoformat(inicio), date.fromisoformat(fin)
    if end < today:
        return {"estado": "ya pasó", "dias_para_inicio": (start - today).days}
    if start <= today:
        return {"estado": "en curso", "dias_para_inicio": 0}
    return {"estado": "próximo", "dias_para_inicio": (start - today).days}


def consultar_calendario(consulta: str, periodo: str | None = None, max_resultados: int = 5,
                         hoy: str | None = None) -> list[dict]:
    """Busca eventos del calendario académico 2027 por palabras clave.

    consulta: palabras del evento, por ejemplo "cancelación de asignaturas" o "exámenes finales".
    periodo: opcional, uno de "2026-2", "2027-1", "2027-i", "2027-2", "2028-1".
    hoy: fecha AAAA-MM-DD contra la que se calculan los días que faltan (por defecto, hoy).
    """
    today = date.fromisoformat(hoy) if hoy else date.today()
    words = [w for w in _normalize(consulta).replace("?", " ").split() if w not in STOPWORDS and len(w) > 2]
    results = []
    for event in load_calendar():
        if periodo and event["periodo"].lower() != periodo.lower():
            continue
        name = _normalize(event["evento"])
        # coincidencia por raíz de 5 letras para tolerar plurales y conjugaciones
        score = sum(1 for w in words if w[:5] in name)
        if score:
            results.append((score, event))
    # Primero los más relevantes; entre ellos, los vigentes o próximos antes que los que ya pasaron
    results.sort(key=lambda item: (-item[0], item[1]["fin"] < today.isoformat(), item[1]["inicio"]))
    best = results[0][0] if results else 0
    return [
        {
            "evento": e["evento"],
            "periodo": e["periodo"],
            "inicio": _human_date(e["inicio"]),
            "fin": _human_date(e["fin"]),
            **_status(e["inicio"], e["fin"], today),
        }
        for score, e in results[:max_resultados]
        if score == best or score >= 2
    ]


def dias_hasta(fecha: str, hoy: str | None = None) -> dict:
    """Días calendario que faltan desde hoy (o desde 'hoy' si se indica) hasta una fecha ISO AAAA-MM-DD."""
    today = date.fromisoformat(hoy) if hoy else date.today()
    target = date.fromisoformat(fecha)
    return {"desde": _human_date(today.isoformat()), "hasta": _human_date(fecha), "dias": (target - today).days}


def calcular_promedio_ponderado(asignaturas: list[dict]) -> dict:
    """Promedio ponderado por créditos, como define el artículo 80 del Reglamento Estudiantil.

    asignaturas: lista de {"nota": float entre 0 y 5, "creditos": int > 0}.
    El resultado se expresa con un solo decimal, igual que el promedio acumulado oficial.
    """
    if not asignaturas:
        raise ValueError("Se necesita al menos una asignatura")
    total_creditos = 0
    suma = 0.0
    for item in asignaturas:
        nota, creditos = float(item["nota"]), int(item["creditos"])
        if not 0 <= nota <= 5 or creditos <= 0:
            raise ValueError(f"Asignatura inválida: {item}")
        suma += nota * creditos
        total_creditos += creditos
    exacto = suma / total_creditos
    # El reglamento dice "con un solo decimal" pero no si se redondea o se trunca, así que devolvemos ambos
    return {
        "promedio_un_decimal": round(exacto, 1),
        "promedio_exacto": round(exacto, 3),
        "creditos": total_creditos,
    }


# ---------------------------------------------------------------- valores 2027 (matrícula y derechos pecuniarios)

STOPWORDS_VALORES = STOPWORDS | {"cuanto", "cuesta", "cuestan", "valor", "vale", "precio", "pagar", "pago", "costo",
                                 "2027", "año", "ano", "escuela", "derecho", "derechos"}
# Palabras con que los estudiantes preguntan, frente a como los nombra la resolución
SINONIMOS_VALORES = {"notas": "calificaciones", "graduarme": "grado", "graduacion": "grado", "graduar": "grado",
                     "titulo": "diploma", "certificado": "certificados", "oxford": "ingles"}
GRUPOS_MATRICULA = {
    "ingenierias": ("ingenier", "sistemas", "civil", "industrial", "electr", "mecan", "ambiental", "biomed",
                    "estadist", "ciberseg", "inteligencia", "biotecn"),
    "economia_administracion": ("econom", "administ"),
    "matematicas": ("matemat",),
}


def _pesos(valor: int) -> str:
    return "$" + f"{valor:,}".replace(",", ".")


def load_values() -> dict:
    with open(config.VALUES_PATH, encoding="utf-8") as file:
        return json.load(file)


def _grupo_matricula(texto: str) -> str | None:
    texto = _normalize(texto)
    # "economía" y "matemáticas" se revisan antes que "ingeniería" (más específicos)
    for grupo in ("economia_administracion", "matematicas", "ingenierias"):
        if any(raiz in texto for raiz in GRUPOS_MATRICULA[grupo]):
            return grupo
    return None


def consultar_valores_2027(consulta: str, programa: str | None = None, rango: int | None = None) -> dict:
    """Valores de 2027 en pesos: matrícula de pregrado por programa y rango socioeconómico, y derechos
    pecuniarios (inscripción, gastos de grado, certificados, examen de validación, etc.)."""
    datos = load_values()
    texto = _normalize(f"{consulta} {programa or ''}")
    if any(p in texto for p in ("maestr", "posgrad", "especializ", "doctorad")) and "validacion" not in texto:
        # La resolución de matrícula es solo de pregrado: no se puede responder con valores de pregrado
        return {"fuente": datos["matricula"]["fuente"].split(". Transcrita")[0], "resultados": [],
                "aviso": "Solo tengo los valores de matrícula de PREGRADO 2027. No tengo los de maestrías, "
                         "especializaciones ni doctorados."}
    if "matricula" in texto or "semestre" in texto or rango is not None:
        m = datos["matricula"]
        nuevos = m["estudiantes_nuevos"]
        grupo = _grupo_matricula(f"{programa or ''} {consulta}")
        grupos = [grupo] if grupo else list(nuevos["grupos"])
        filas = [f for f in nuevos["rangos"] if rango is None or f["rango"] == int(rango)]
        if rango is None:
            filas = [filas[0], filas[-1]]  # sin rango: el mínimo y el máximo
        valores = [{"rango": f["rango"], "pagina": f["pagina"],
                    **{nuevos["grupos"][g]: _pesos(f[g]) for g in grupos}} for f in filas]
        resultado = {
            "fuente": m["fuente"].split(". Transcrita")[0],
            "tipo": "matrícula 2027",
            "estudiantes_nuevos": nuevos["descripcion"],
            "valores": valores,
            "estudiantes_antiguos_o_reintegro": m["estudiantes_antiguos_o_reintegro"]["descripcion"],
        }
        if rango is None:
            resultado["aclaracion"] = ("Hay 12 rangos según la información socioeconómica; se muestran el rango 1 (mínimo) "
                                       "y el 12 (máximo). El rango de cada estudiante lo asigna la Escuela al ingresar.")
        if "biomed" in texto:
            resultado["nota_biomedica"] = nuevos["nota_biomedica"]
        return resultado

    d = datos["derechos_pecuniarios"]
    palabras = [SINONIMOS_VALORES.get(w, w) for w in texto.replace("?", " ").split()
                if w not in STOPWORDS_VALORES and len(w) > 2]
    puntajes = []
    for item in d["conceptos"]:
        nombre = _normalize(item["concepto"])
        score = sum(1 for w in palabras if w[:4] in nombre)  # raíz de 4 letras: "grad" acierta grado y graduación
        if score:
            puntajes.append((score, item))
    mejor = max((s for s, _ in puntajes), default=0)
    resultados = [{"concepto": i["concepto"], "valor_2027": _pesos(i["valor_2027"]), "valor_2026": _pesos(i["valor_2026"]),
                   "incremento": i["incremento"], **({"nota": d["notas"][i["nota"]]} if "nota" in i else {})}
                  for s, i in puntajes if s == mejor]
    return {
        "fuente": d["fuente"].split(". Transcrita")[0],
        "tipo": "derechos pecuniarios 2027",
        "resultados": resultados,
        **({} if resultados else {"conceptos_disponibles": [i["concepto"] for i in d["conceptos"]]}),
    }


# ---------------------------------------------------------------- plan de estudios de Ingeniería de Sistemas

# Nombres de PROGRAMA (no de materia: "Probabilidad y Estadística" o "Matemáticas para Informática" son de Sistemas)
OTROS_PROGRAMAS = [
    (r"ingenieria\s+(civil|industrial|electrica|electronica|mecanica|ambiental|biomedica|estadistica)", None),
    (r"ingenieria\s+(de\s+ciberseguridad|de\s+inteligencia\s+artificial|en\s+biotecnologia)", None),
    (r"\b(economia|administracion\s+de\s+empresas)\b", None),
    (r"(programa|carrera)\s+de\s+matematicas", "Matemáticas"),
]


TILDES = {"ingenieria": "Ingeniería", "electrica": "Eléctrica", "electronica": "Electrónica", "mecanica": "Mecánica",
          "biomedica": "Biomédica", "estadistica": "Estadística", "economia": "Economía",
          "administracion": "Administración", "biotecnologia": "Biotecnología"}


def _otro_programa(texto: str) -> str | None:
    """Nombre legible del programa (distinto de Sistemas) que menciona la consulta, si menciona alguno."""
    for patron, nombre in OTROS_PROGRAMAS:
        if m := re.search(patron, texto):
            palabras = re.split(r"\s+", m.group(0))
            return nombre or " ".join(TILDES.get(w, w if w in ("de", "en") else w.capitalize()) for w in palabras)
    return None
ORDINALES = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4, "quinto": 5,
             "sexto": 6, "septimo": 7, "octavo": 8, "noveno": 9, "decimo": 10}
STOPWORDS_PLAN = STOPWORDS | {"semestre", "semestres", "creditos", "credito", "materia", "materias", "asignatura",
                              "asignaturas", "plan", "estudios", "sistemas", "ingenieria", "cuantos", "cuantas",
                              "tiene", "vale", "valen", "veo", "ven", "como", "nuevo", "antiguo", "anterior", "antes",
                              "desde", "2025", "2025-1", "programa", "carrera"}


def load_study_plans() -> dict:
    with open(config.STUDY_PLAN_PATH, encoding="utf-8") as file:
        return json.load(file)


def _semestre_pedido(texto: str) -> int | None:
    m = re.search(r"semestre\s+(\d{1,2})\b|\b(\d{1,2})\s*(?:°|º|er|do|ro|to|vo|no|mo)?\s+semestre", texto)
    if m:
        return int(m.group(1) or m.group(2))
    for palabra, numero in ORDINALES.items():
        if re.search(rf"\b{palabra}\s+semestre", texto):
            return numero
    return None


def _plan_pedido(texto: str) -> list[str]:
    if any(w in texto for w in ("antes", "anterior", "antiguo", "viejo")):
        return ["antes_2025_1"]
    if any(w in texto for w in ("nuevo", "desde", "a partir", "actual", "plan 15", "n.° 15")):
        return ["desde_2025_1"]
    return ["desde_2025_1", "antes_2025_1"]


def consultar_plan_estudios(consulta: str, plan: str | None = None) -> dict:
    """Asignaturas, semestre y créditos de los planes de estudio de Ingeniería de Sistemas
    (desde 2025-1 y antes de 2025-1). No incluye prerrequisitos ni otros programas."""
    datos = load_study_plans()
    texto = _normalize(consulta)
    otro = _otro_programa(texto)
    if otro and "sistemas" not in texto:
        # Solo existe el plan de Sistemas: responder con él una pregunta sobre otro programa sería un error
        return {"fuente": "Planes de estudio oficiales de Ingeniería de Sistemas", "planes": [],
                "aviso": f"Solo tengo el plan de estudios de Ingeniería de Sistemas. No tengo el plan de {otro}."}
    claves = [plan] if plan in datos["planes"] else _plan_pedido(texto)
    semestre = _semestre_pedido(texto)
    codigos = {w.upper() for w in re.findall(r"[a-z0-9]{4,6}", texto)}
    palabras = [w for w in re.findall(r"[a-z0-9]+", texto) if w not in STOPWORDS_PLAN and len(w) > 2]
    salida = []
    for clave in claves:
        p = datos["planes"][clave]
        asignaturas = p["asignaturas"]
        if por_codigo := [a for a in asignaturas if a["codigo"] in codigos]:
            elegidas = por_codigo
        elif semestre is not None:
            elegidas = [a for a in asignaturas if a["semestre"] == semestre]
        else:
            puntajes = [(sum(1 for w in palabras if w[:5] in _normalize(a["nombre"])), a) for a in asignaturas]
            mejor = max((s for s, _ in puntajes), default=0)
            elegidas = [a for s, a in puntajes if mejor and s == mejor]
        salida.append({
            "plan": p["nombre"],
            "resumen": {"total_creditos": p["total_creditos"], "semestres": p["semestres"],
                        "creditos_por_semestre": p["creditos_por_semestre"], "creditos_por_nucleo": p["creditos_por_nucleo"],
                        "nota": p["nota_total"]},
            "asignaturas": [{"codigo": a["codigo"], "nombre": a["nombre"], "creditos": a["creditos"],
                             "semestre": a["semestre"]} for a in elegidas[:15]],
        })
    return {
        "fuente": "Planes de estudio oficiales de Ingeniería de Sistemas (mallas en PDF de la Escuela)",
        "planes": salida,
        "limitaciones": "Solo Ingeniería de Sistemas. No incluye prerrequisitos.",
    }
