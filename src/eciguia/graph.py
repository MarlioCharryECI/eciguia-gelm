"""Agente de EciGuía construido con LangGraph.

    pregunta -> router -> documentos -> recuperar -> (hay contexto?) -> responder con citas
                       -> herramienta -> elegir tool MCP -> ejecutar -> responder
                       -> fuera_de_alcance -> rechazo amable
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Literal, TypedDict

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from langgraph.graph import END, START, StateGraph

from eciguia import config, prompts
from eciguia.retriever import Hit, Retriever, format_context

Route = Literal["documentos", "herramienta", "fuera_de_alcance"]
SRC_DIR = Path(__file__).resolve().parents[1]
PERIOD_HINT = re.compile(r"20\d\d|intersemestral", re.IGNORECASE)
PLAN_HINT = re.compile(r"2025|antes|anterior|antiguo|viejo|nuevo|actual", re.IGNORECASE)
TOOLS_WITH_QUERY = {"consultar_calendario", "consultar_valores_2027", "consultar_plan_estudios"}
TOOLS_WITH_FULL_QUESTION = {"consultar_valores_2027", "consultar_plan_estudios"}
CITATION_RE = re.compile(r"\[(\d+(?:\s*[,y]\s*\d+)*)\]")


def clean_rag_answer(answer: str, n_fragments: int) -> str:
    """Correcciones deterministas a la respuesta del LLM, para fallos que el prompt no logra evitar:
    - quita las citas a fragmentos que no existen (el modelo confunde "numeral 7" con "[7]");
    - quita el "No encontré..." pegado al final de una respuesta que sí tiene contenido."""
    def keep_valid(match: re.Match) -> str:
        numbers = [n for n in re.findall(r"\d+", match.group(1)) if 1 <= int(n) <= n_fragments]
        return f"[{', '.join(numbers)}]" if numbers else ""

    answer = CITATION_RE.sub(keep_valid, answer)
    if not answer.startswith("No encontré"):
        answer = answer.replace(prompts.NO_INFO_RAG, "")
    return re.sub(r"[ \t]+([.,])", r"\1", re.sub(r"[ \t]{2,}", " ", answer)).strip()


def stdio_transport() -> StdioTransport:
    """Lanza el servidor MCP como subproceso que habla por stdin/stdout, como lo haría cualquier cliente MCP."""
    env = {**os.environ, "FASTMCP_LOG_LEVEL": "WARNING", "PYTHONPATH": os.pathsep.join(filter(None, [str(SRC_DIR), os.environ.get("PYTHONPATH")]))}
    return StdioTransport(command=sys.executable, args=["-m", "eciguia.mcp_server"], env=env)


class AgentState(TypedDict, total=False):
    question: str
    route: Route
    route_reason: str
    hits: list[Hit]
    tool_name: str
    tool_args: dict
    tool_result: Any
    answer: str
    sources: list[str]
    error: str


def _today() -> str:
    return date.today().isoformat()


def _parse_json(text: str) -> dict:
    """Extrae el primer objeto JSON de la respuesta del modelo (los modelos pequeños a veces agregan texto)."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"El modelo no devolvió JSON: {text[:200]}")
    return json.loads(match.group(0))


def _text(message) -> str:
    return message.content if hasattr(message, "content") else str(message)


def default_llm(json_mode: bool = False, model: str | None = None):
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model or config.LLM_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0,
        keep_alive=config.KEEP_ALIVE,
        client_kwargs={"timeout": config.OLLAMA_TIMEOUT},
        format="json" if json_mode else None,
    )


class EciGuiaAgent:
    """Envuelve el grafo. Recibe el LLM, el retriever y el destino MCP para poder probarlo con dobles."""

    def __init__(self, llm=None, json_llm=None, retriever: Retriever | None = None, mcp_target=None,
                 rag_prompt: str = prompts.RAG_ANSWER, router_prompt: str = prompts.ROUTER, use_router: bool = True):
        self.llm = llm or default_llm()
        self.json_llm = json_llm or (default_llm(json_mode=True) if llm is None else llm)
        self.retriever = retriever or Retriever()
        # Por defecto el servidor MCP corre como subproceso (stdio). En pruebas se pasa la instancia en memoria.
        self.mcp_target = mcp_target
        self.rag_prompt = rag_prompt
        self.router_prompt = router_prompt
        self.use_router = use_router  # False = línea base: todo va directo al RAG
        self._mcp: tuple | None = None  # (cliente, event loop, catálogo de herramientas)
        self.graph = self._build()

    async def _mcp_session(self) -> tuple[Client, str]:
        """Conexión MCP que se abre una vez y se reutiliza: lanzar el servidor en cada pregunta costaba ~5 s.
        Si cambia el event loop (cada asyncio.run de las pruebas), se abre una nueva."""
        loop = asyncio.get_running_loop()
        if self._mcp is None or self._mcp[1] is not loop:
            client = Client(self.mcp_target or stdio_transport())
            await client.__aenter__()
            tools = await client.list_tools()
            catalog = "\n".join(
                f"- {t.name}: {t.description.strip()}\n  argumentos: {json.dumps((getattr(t, 'input_schema', None) or t.inputSchema).get('properties', {}), ensure_ascii=False)}"
                for t in tools
            )
            self._mcp = (client, loop, catalog)
        return self._mcp[0], self._mcp[2]

    # ------------------------------------------------------------ nodos

    async def route(self, state: AgentState) -> AgentState:
        if not self.use_router:
            return {"route": "documentos", "route_reason": "sin router (línea base)"}
        try:
            reply = await self.json_llm.ainvoke(self.router_prompt.format(question=state["question"]))
            data = _parse_json(_text(reply))
            route = data.get("ruta", "documentos")
            if route not in ("documentos", "herramienta", "fuera_de_alcance"):
                route = "documentos"
            return {"route": route, "route_reason": data.get("razon", "")}
        except Exception as exc:  # si el router falla, la ruta más segura es buscar en documentos
            return {"route": "documentos", "route_reason": f"fallback: {exc}"}

    async def retrieve(self, state: AgentState) -> AgentState:
        return {"hits": self.retriever.search(state["question"])}

    async def answer_from_docs(self, state: AgentState) -> AgentState:
        hits = state["hits"]
        prompt = self.rag_prompt.format(context=format_context(hits), question=state["question"])
        reply = await self.llm.ainvoke(prompt)
        answer = clean_rag_answer(_text(reply).strip(), len(hits))
        if answer.startswith("No encontré"):  # el modelo no usó el contexto: citar fuentes confundiría
            return {"answer": answer, "sources": []}
        return {"answer": answer, "sources": [f"[{i}] {h.citation}" for i, h in enumerate(hits, 1)]}

    async def no_info(self, state: AgentState) -> AgentState:
        return {"answer": prompts.NO_INFO, "sources": []}

    async def use_tool(self, state: AgentState) -> AgentState:
        try:
            client, catalog = await self._mcp_session()
            reply = await self.json_llm.ainvoke(
                prompts.TOOL_SELECTION.format(today=_today(), tools=catalog, question=state["question"])
            )
            choice = _parse_json(_text(reply))
            name, args = choice["herramienta"], choice.get("argumentos", {})
            if name == "consultar_calendario" and not PERIOD_HINT.search(state["question"]):
                # El modelo tiende a suponer un periodo (p. ej. 2027-1) aunque la pregunta no lo diga, y eso
                # esconde el evento vigente. Sin periodo, la herramienta devuelve todos y se elige el más próximo.
                args.pop("periodo", None)
            if name == "consultar_plan_estudios" and not PLAN_HINT.search(state["question"]):
                args.pop("plan", None)  # mismo problema: sin pista, se consultan los dos planes
            args = {k: v for k, v in args.items() if v not in (None, "")}
            if name in TOOLS_WITH_QUERY and not args.get("consulta"):
                # El modelo a veces omite "consulta" (o la deja vacía) en preguntas generales como
                # "¿cuántos créditos tiene el plan?". La pregunta misma es una buena consulta.
                args["consulta"] = state["question"]
            elif name in TOOLS_WITH_FULL_QUESTION:
                # Al resumir la consulta, el modelo puede perder lo que hace inválida la pregunta
                # ("quinto semestre" en vez de "quinto semestre de Ingeniería Civil"). Las herramientas
                # de datos reciben también la pregunta original para poder decir "no tengo ese dato".
                args["consulta"] = f"{args['consulta']} | {state['question']}"
            result = await client.call_tool(name, args)
            data = result.data if result.data is not None else [c.text for c in result.content if hasattr(c, "text")]
            return {"tool_name": name, "tool_args": args, "tool_result": data}
        except Exception as exc:
            if not getattr(self._mcp and self._mcp[0], "is_connected", lambda: True)():
                self._mcp = None  # la conexión se cayó: la próxima pregunta abre una nueva
            return {"error": f"Error usando la herramienta: {exc}", "tool_result": None, "tool_name": "ninguna"}

    async def answer_from_tool(self, state: AgentState) -> AgentState:
        if state.get("tool_result") in (None, [], {}):
            return {"answer": "No encontré ese dato en mis herramientas (calendario académico 2027, valores 2027 y "
                              "plan de estudios de Ingeniería de Sistemas) ni pude calcularlo. Revisa la información "
                              "oficial en escuelaing.edu.co.", "sources": []}
        result = json.dumps(state["tool_result"], ensure_ascii=False, default=str)
        reply = await self.llm.ainvoke(
            prompts.TOOL_ANSWER.format(today=_today(), tool=state["tool_name"], result=result, question=state["question"])
        )
        tool_result = state["tool_result"]
        if state["tool_name"] == "consultar_calendario":
            source = "Calendario Académico 2027"
        elif isinstance(tool_result, dict) and tool_result.get("fuente"):
            source = f"{tool_result['fuente']} (herramienta MCP {state['tool_name']})"
        else:
            source = f"Herramienta MCP: {state['tool_name']}"
        return {"answer": _text(reply).strip(), "sources": [source]}

    async def reject(self, state: AgentState) -> AgentState:
        return {"answer": prompts.OUT_OF_SCOPE, "sources": []}

    # ------------------------------------------------------------ grafo

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("router", self.route)
        g.add_node("recuperar", self.retrieve)
        g.add_node("responder_documentos", self.answer_from_docs)
        g.add_node("sin_informacion", self.no_info)
        g.add_node("usar_herramienta", self.use_tool)
        g.add_node("responder_herramienta", self.answer_from_tool)
        g.add_node("rechazar", self.reject)

        g.add_edge(START, "router")
        g.add_conditional_edges("router", lambda s: s["route"], {
            "documentos": "recuperar",
            "herramienta": "usar_herramienta",
            "fuera_de_alcance": "rechazar",
        })
        g.add_conditional_edges("recuperar", lambda s: "con_contexto" if s["hits"] else "sin_contexto", {
            "con_contexto": "responder_documentos",
            "sin_contexto": "sin_informacion",
        })
        g.add_edge("usar_herramienta", "responder_herramienta")
        for node in ("responder_documentos", "sin_informacion", "responder_herramienta", "rechazar"):
            g.add_edge(node, END)
        return g.compile()

    async def ask(self, question: str) -> AgentState:
        start = time.perf_counter()
        state = await self.graph.ainvoke({"question": question})
        state["latency_s"] = round(time.perf_counter() - start, 2)
        return state


def main() -> None:
    """Prueba rápida desde la terminal: uv run python -m eciguia.graph "tu pregunta"."""
    question = " ".join(sys.argv[1:]) or "¿Cuántos créditos debo tener aprobados para hacer la práctica?"
    state = asyncio.run(EciGuiaAgent().ask(question))
    print(f"Ruta: {state['route']} ({state.get('route_reason', '')})")
    if state.get("tool_name"):
        print(f"Herramienta: {state['tool_name']} {json.dumps(state.get('tool_args', {}), ensure_ascii=False)}")
    if state.get("hits"):
        print("Distancias: " + ", ".join(f"{h.distance:.3f}" for h in state["hits"]))
    if state.get("error"):
        print(f"Error: {state['error']}")
    print(f"Latencia: {state['latency_s']} s\n")
    print(state["answer"])
    for source in state.get("sources", []):
        print("  ", source)


if __name__ == "__main__":
    main()
