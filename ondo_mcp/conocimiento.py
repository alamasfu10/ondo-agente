"""RAG sencillo sobre la base de conocimiento de Ondo.

Es el patrón que visteis en el Tema 5, en su versión mínima:

1. Cada documento de data/conocimiento/ se parte por secciones (## ...).
   Un fragmento por sección, con el documento y la sección como metadatos.
2. Cada fragmento se convierte en un embedding con text-embedding-3-small.
3. Los vectores viven en un InMemoryVectorStore de LangChain. Para no pagar
   los embeddings en cada arranque, se guardan en data/.cache/.
4. La búsqueda devuelve los 3 fragmentos más parecidos que superan un umbral.
   Si ninguno lo supera, devuelve "sin resultados" y el agente no inventa.
"""

import hashlib
import json
import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from .datos import DATA

CARPETA = DATA / "conocimiento"
CACHE = DATA / ".cache" / "indice.json"
MODELO_EMBEDDINGS = os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small")
K = 3
UMBRAL = float(os.getenv("RAG_UMBRAL", "0.35"))

_almacen: InMemoryVectorStore | None = None


def fragmentos() -> list[Document]:
    docs = []
    for f in sorted(CARPETA.glob("*.md")):
        titulo, seccion, lineas = f.stem, None, []
        for linea in f.read_text(encoding="utf-8").splitlines() + ["## FIN"]:
            if linea.startswith("# "):
                titulo = linea[2:].strip()
            elif linea.startswith("## "):
                if seccion and "".join(lineas).strip():
                    texto = " ".join(x.strip() for x in lineas if x.strip())
                    docs.append(Document(
                        page_content=f"{titulo}. {seccion}. {texto}",
                        metadata={"documento": titulo, "seccion": seccion, "fichero": f.name},
                    ))
                seccion, lineas = linea[3:].strip(), []
            else:
                lineas.append(linea)
    return docs


def _huella(docs):
    h = hashlib.sha256(MODELO_EMBEDDINGS.encode())
    for d in docs:
        h.update(d.page_content.encode())
    return h.hexdigest()


def almacen() -> InMemoryVectorStore:
    global _almacen
    if _almacen is not None:
        return _almacen
    docs = fragmentos()
    emb = OpenAIEmbeddings(model=MODELO_EMBEDDINGS)
    huella = _huella(docs)
    vectores = None
    if CACHE.exists():
        guardado = json.loads(CACHE.read_text(encoding="utf-8"))
        if guardado.get("huella") == huella:
            vectores = guardado["vectores"]
    if vectores is None:
        vectores = emb.embed_documents([d.page_content for d in docs])
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({"huella": huella, "vectores": vectores}), encoding="utf-8")
    st = InMemoryVectorStore(emb)
    for i, (d, v) in enumerate(zip(docs, vectores)):
        st.store[str(i)] = {"id": str(i), "vector": v, "text": d.page_content, "metadata": d.metadata}
    _almacen = st
    return st


def buscar(pregunta: str) -> list[dict]:
    resultados = almacen().similarity_search_with_score(pregunta, k=K)
    return [
        {
            "documento": d.metadata["documento"],
            "seccion": d.metadata["seccion"],
            "texto": d.page_content,
            "similitud": round(float(score), 3),
        }
        for d, score in resultados
        if score >= UMBRAL
    ]
