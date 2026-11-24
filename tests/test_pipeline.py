"""Pruebas de punta a punta sin Ollama: uv run pytest"""

import asyncio

import pytest
from langchain_chroma import Chroma

from eciguia import tools_logic
from eciguia.graph import EciGuiaAgent
from eciguia.ingest import chunk_documents, load_pages
from eciguia.mcp_server import mcp
from eciguia.retriever import Retriever
from fakes import HashEmbeddings, ScriptedLLM


@pytest.fixture(scope="module")
def pages():
    return load_pages()


@pytest.fixture(scope="module")
def agent(pages, tmp_path_factory):
    docs = chunk_documents(pages, "articulo")
    store = Chroma(
        collection_name="test",
        embedding_function=HashEmbeddings(),
        persist_directory=str(tmp_path_factory.mktemp("chroma")),
        collection_metadata={"hnsw:space": "cosine"},
    )
    store.add_documents(docs)
    retriever = Retriever(store=store, k=4, max_distance=0.95)
    return EciGuiaAgent(llm=ScriptedLLM(), retriever=retriever, mcp_target=mcp)


ORIGINAL_DOCUMENTS = {
    "modificacion_reglamento_estudiantil_2025.pdf", "reglamento_practicas_profesionales.pdf",
    "lineamientos_opcion_de_grado.pdf", "reglamento_trabajos_dirigidos.pdf",
    "reglamento_movilidad_estudiantil.pdf", "reglamento_ingles_2025.pdf",
}


def test_loads_all_documents(pages):
    # Los 6 documentos de la primera etapa se siguen cargando aunque el corpus crezca
    assert ORIGINAL_DOCUMENTS <= {p.source for p in pages}


@pytest.mark.parametrize("strategy", ["articulo", "fijo"])
def test_chunking(pages, strategy):
    docs = chunk_documents(pages, strategy)
    assert len(docs) > 50
    assert all(d.metadata["page"] >= 1 for d in docs)


def test_article_chunks_keep_section(pages):
    docs = chunk_documents(pages, "articulo")
    sections = {d.metadata["section"] for d in docs}
    assert any(s.startswith("Artículo 12. Duración de la práctica") for s in sections)


def test_section_is_only_the_bold_title(pages):
    docs = chunk_documents(pages, "articulo")
    sections = {d.metadata["section"] for d in docs if d.metadata["source"] == "reglamento_practicas_profesionales.pdf"}
    assert "Artículo 10. Requisitos para solicitar el acceso al programa de prácticas profesionales" in sections


def test_modification_keeps_only_new_version(pages):
    docs = [d for d in chunk_documents(pages, "articulo") if d.metadata["source"].startswith("modificacion")]
    text = " ".join(d.page_content for d in docs)
    assert "en el proceso de admisión" in text  # frase que solo está en la nueva versión del art. 69


def test_calendar_lookup():
    result = tools_logic.consultar_calendario("cancelación de asignaturas", "2027-1")
    assert result[0]["fin"] == "8 de mayo de 2027"


def test_calendar_reports_days_left():
    result = tools_logic.consultar_calendario("cancelación de asignaturas", "2027-1", hoy="2027-05-01")
    assert result[0]["estado"] == "próximo"
    assert result[0]["dias_para_inicio"] == 7
    past = tools_logic.consultar_calendario("cancelación de asignaturas", "2027-1", hoy="2027-06-01")
    assert past[0]["estado"] == "ya pasó"


def test_calendar_without_period_puts_upcoming_first():
    result = tools_logic.consultar_calendario("cancelación de semestre", hoy="2026-11-20")
    assert result[0]["periodo"] == "2026-2"
    assert result[0]["fin"] == "21 de noviembre de 2026"
    later = tools_logic.consultar_calendario("cancelación de semestre", hoy="2026-12-01")
    assert later[0]["periodo"] == "2027-1"


def test_transcriptions_replace_scanned_pdfs(pages):
    sources = {p.source for p in pages}
    assert {p.number for p in pages if p.source == "lineamientos_creditos_adicionales.md"} == {1, 2}
    # el PDF escaneado (o mixto) no se indexa: se usa su transcripción
    assert "lineamientos_creditos_adicionales.pdf" not in sources
    assert "lineamientos_cancelacion_asignaturas_2025.pdf" not in sources
    assert "lineamientos_cancelacion_asignaturas_2025.md" in sources


def test_attendance_list_page_is_skipped(pages):
    assert not [p for p in pages if p.source == "condiciones_doble_programa_2026.pdf" and p.number == 1]


def test_values_2027():
    grado = tools_logic.consultar_valores_2027("gastos de grado")
    assert grado["resultados"][0]["valor_2027"] == "$979.000"
    matricula = tools_logic.consultar_valores_2027("matrícula", programa="economía", rango=5)
    assert matricula["valores"][0]["Economía y Administración de Empresas"] == "$9.596.000"


def test_study_plan_both_versions():
    planes = tools_logic.consultar_plan_estudios("ARSW")["planes"]
    semestres = {p["plan"].split(" (")[0]: p["asignaturas"][0]["semestre"] for p in planes}
    assert sorted(semestres.values()) == [6, 8]  # 6.° en el plan desde 2025-1, 8.° en el anterior
    assert {p["resumen"]["total_creditos"] for p in planes} == {139, 158}


def test_weighted_average():
    result = tools_logic.calcular_promedio_ponderado([{"nota": 4.2, "creditos": 3}, {"nota": 3.5, "creditos": 4}])
    assert result["promedio_exacto"] == 3.8
    assert result["creditos"] == 7


def test_agent_document_route(agent):
    state = asyncio.run(agent.ask("¿Cuánto dura la práctica profesional nacional?"))
    assert state["route"] == "documentos"
    assert state["sources"]


def test_agent_tool_route_uses_mcp(agent):
    state = asyncio.run(agent.ask("¿Hasta cuándo puedo cancelar asignaturas en 2027-1?"))
    assert state["route"] == "herramienta"
    assert state["tool_name"] == "consultar_calendario"
    assert "8 de mayo de 2027" in state["answer"]


def test_agent_average_tool(agent):
    state = asyncio.run(agent.ask("¿Cuál es mi promedio si saqué 4.2 en 3 créditos y 3.5 en 4 créditos?"))
    assert state["tool_name"] == "calcular_promedio_ponderado"
    assert "3.8" in state["answer"]


def test_agent_rejects_out_of_scope(agent):
    state = asyncio.run(agent.ask("¿Me recomiendas una película?"))
    assert state["route"] == "fuera_de_alcance"
