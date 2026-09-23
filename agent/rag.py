"""GraphRAG: pattern typology, policy text, closed-case notes + lightweight vector search.

Embeddings are a deterministic local hash-based bag-of-words (256-dim, L2-normalized);
no external embeddings API is used. Primary indexing path attempts TigerGraph vector
attributes on a DocChunk vertex type; retrieval falls back to in-memory cosine scoring
over the small corpus, which always works offline.
"""
import hashlib
import json
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

EMBED_DIM = 256
README_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Initial-docs", "dataset", "README (1).md",
)

PATTERN_DOCS = {
    "card_testing": (
        "Card testing is the pre-use validation of a stolen card number: three or more tiny "
        "online authorizations, often under $5, followed by a larger purchase. The sequence "
        "itself is the confirmation signal. Policy rule R5 applies: decline the flagged "
        "transaction and require step-up authentication, and block the card if a purchase "
        "over $100 has already cleared."
    ),
    "card_not_present_fraud": (
        "Card-not-present fraud means the card number is used online without the physical card. "
        "Amounts and products do not fit the cardholder's history, often in a burst of two to "
        "four purchases within 48 hours, frequently at a new merchant. A single unusual online "
        "purchase is ambiguous on its own, so verify with the customer (policy R1-R4) before "
        "any blocking action."
    ),
    "card_not_present_new_device": (
        "Card-not-present fraud from a new device is the same online fraud pattern, with the "
        "identity record marking the device as New for the account, sometimes behind a proxy. "
        "It is stronger evidence than plain card-not-present fraud but still not proof, since "
        "people legitimately buy new phones. Combine device novelty with amount and merchant "
        "anomalies before escalating beyond verification."
    ),
    "out_of_region_use": (
        "Out-of-region use is card-present purchasing in a billing region where the cardholder "
        "has no history while their normal activity continues at home. Several days of purchases "
        "in one new region is a trip, not a clone. Policy R2 and R3 cover the disputed-charge "
        "and confirmation paths for these cases."
    ),
    "account_takeover": (
        "Account takeover shows mixed-channel activity inconsistent with the cardholder, often "
        "with device and match-flag anomalies, pointing to stolen credentials rather than a "
        "stolen card number. Look for a credential or device change followed by value "
        "extraction. Coordinated across a customer's cards, it justifies case creation and "
        "monitoring of connected cards."
    ),
    "undocumented": (
        "Undocumented abuse is coordinated or repeated fraudulent activity that fits none of "
        "the five known patterns, for example many cards sharing one device profile, region, "
        "or recipient email in a single window. Policy R9: describe the pattern in your own "
        "words, do not force it into a known category, and recommend case creation, a report "
        "filing, and analyst escalation."
    ),
    "none": (
        "No pattern: the evidence does not support a known fraud typology. The activity may "
        "still be unusual, but neither graph evidence nor history matches card testing, "
        "card-not-present fraud, out-of-region use, account takeover, or coordinated abuse. "
        "Treat the case on its individual signals and prefer verification over blocking."
    ),
}

_CORPUS: Optional[list] = None
_TG_SEARCH_OK = False


def _tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


def embed(text: str) -> list:
    """Deterministic 256-dim hash bag-of-words TF vector, L2-normalized."""
    vec = [0.0] * EMBED_DIM
    for token in _tokenize(text):
        idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % EMBED_DIM
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _cosine(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


def load_policy_text(path: str = README_PATH) -> list:
    """Parse the Fraud Policy section into chunks keyed by rule header."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    start = text.find("# Fraud Policy")
    end = text.find("# Answer Format")
    if start == -1:
        return []
    section = text[start:end if end != -1 else len(text)]

    chunks = []
    parts = re.split(r"^### ", section, flags=re.MULTILINE)[1:]
    for part in parts:
        title = part.splitlines()[0].strip()
        body = part[len(title):].strip()
        m = re.match(r"^(\d+[a-z]?)\.", title)
        ref = f"policy:{m.group(1)}" if m else f"policy:{re.sub(r'[^A-Za-z0-9]+', '_', title)[:30]}"
        chunks.append({"ref": ref, "text": body})
        if m and m.group(1) == "3":
            pieces = re.split(r"\*\*(R\d+)\.", body)
            for i in range(1, len(pieces) - 1, 2):
                rid, rtext = pieces[i], pieces[i + 1]
                chunks.append({"ref": f"policy:{rid}", "text": f"{rid}. {rtext.strip()}"})
    return chunks


def _fetch_closed_case_notes(conn) -> list:
    """Fetch analyst notes for a bounded sample of ClosedCase vertices."""
    gsql = (
        "INTERPRET QUERY () FOR GRAPH "
        f"{getattr(conn, 'graphname', 'FraudGraph')} {{\n"
        "  R = SELECT s FROM ClosedCase:s LIMIT 300;\n"
        "  PRINT R;\n"
        "}"
    )
    try:
        res = _run_query(conn, gsql, None)
        rows = []
        for entry in res:
            if isinstance(entry, dict) and "R" in entry:
                rows = entry["R"]
                break
        notes = []
        for row in rows:
            attrs = row.get("attributes", row) if isinstance(row, dict) else {}
            case_id = row.get("v_id", attrs.get("case_id", "")) if isinstance(row, dict) else ""
            note = attrs.get("analyst_notes", "")
            if case_id and note:
                notes.append({"ref": f"closed_case:{case_id}", "text": str(note)})
        return notes
    except Exception:
        return []


def _run_query(conn, gsql: str, params: Optional[dict]) -> Any:
    if hasattr(conn, "run_interpreted_query"):
        return conn.run_interpreted_query(gsql, params or {})
    if params:
        return conn.runInterpretedQuery(gsql, params)
    return conn.runInterpretedQuery(gsql)


def build_corpus(conn=None) -> list:
    """Pattern docs + policy chunks + closed-case analyst notes."""
    chunks = [
        {"ref": f"pattern:{key}", "text": doc}
        for key, doc in PATTERN_DOCS.items()
    ]
    chunks.extend(load_policy_text())
    if conn is not None:
        chunks.extend(_fetch_closed_case_notes(conn))
    for chunk in chunks:
        chunk["embedding"] = embed(chunk["text"])
    return chunks


def _ensure_corpus(conn=None) -> list:
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = build_corpus(conn)
    return _CORPUS


# ---------------------------------------------------------------------------
# TigerGraph vector index (primary path, best-effort)
# ---------------------------------------------------------------------------
# vectorSearch() is not supported in interpreted mode: it needs an installed
# query with a LIST<FLOAT> parameter. DocChunk is added to the graph (if
# missing) via a local schema change job; a small helper query is installed
# for kNN search. Any failure anywhere drops back to in-memory scoring.
RAG_SEARCH_QUERY = "rag_vector_search"

_GSQL_ERROR_MARKERS = ("Semantic Check Fails", "Encountered", "Failed to create", "Failed to run")


def _gsql_ok(result: str) -> bool:
    return not any(marker in result for marker in _GSQL_ERROR_MARKERS)


def _ensure_docchunk(conn) -> bool:
    """Create the DocChunk vertex type on the graph if missing."""
    result = str(conn.gsql(
        f"USE GRAPH {getattr(conn, 'graphname', 'FraudGraph')}\n"
        "CREATE SCHEMA_CHANGE JOB add_docchunk FOR GRAPH "
        f"{getattr(conn, 'graphname', 'FraudGraph')} {{\n"
        '  ADD VERTEX DocChunk (PRIMARY_ID chunk_id STRING, ref STRING, content STRING) '
        'WITH PRIMARY_ID_AS_ATTRIBUTE="true";\n'
        "}\n"
        "RUN SCHEMA_CHANGE JOB add_docchunk\n"
        "DROP JOB add_docchunk"
    ))
    return _gsql_ok(result) or "already exists" in result or "used by another object" in result


def _ensure_vector_attribute(conn) -> bool:
    """Add the 256-dim COSINE vector attribute to DocChunk if missing."""
    try:
        vectors = {name for name, _ in conn.getVertexVectors("DocChunk")}
        if "embedding" in vectors:
            return True
    except Exception:
        pass
    result = str(conn.gsql(
        f"USE GRAPH {getattr(conn, 'graphname', 'FraudGraph')}\n"
        "CREATE SCHEMA_CHANGE JOB add_docchunk_embedding FOR GRAPH "
        f"{getattr(conn, 'graphname', 'FraudGraph')} {{\n"
        '  ALTER VERTEX DocChunk ADD VECTOR ATTRIBUTE embedding(DIMENSION=256, METRIC="COSINE");\n'
        "}\n"
        "RUN SCHEMA_CHANGE JOB add_docchunk_embedding\n"
        "DROP JOB add_docchunk_embedding"
    ))
    return _gsql_ok(result) or "conflict" in result or "already exists" in result


def _install_search_query(conn) -> bool:
    gname = getattr(conn, "graphname", "FraudGraph")
    conn.gsql(f"USE GRAPH {gname}\nDROP QUERY {RAG_SEARCH_QUERY}")
    result = str(conn.gsql(
        f"USE GRAPH {gname}\n"
        f"CREATE QUERY {RAG_SEARCH_QUERY}(LIST<FLOAT> query_vec, INT k) FOR GRAPH {gname} SYNTAX v3 {{\n"
        "  MapAccum<VERTEX, FLOAT> @@distances;\n"
        "  v = vectorSearch({DocChunk.embedding}, query_vec, k, { distance_map: @@distances });\n"
        "  PRINT v;\n"
        "  PRINT @@distances AS distances;\n"
        "}\n"
        f"INSTALL QUERY {RAG_SEARCH_QUERY}"
    ))
    return _gsql_ok(result)


def _probe_vector_search(conn) -> bool:
    try:
        res = conn.runInstalledQuery(RAG_SEARCH_QUERY, {"query_vec": [0.0] * EMBED_DIM, "k": 3})
        return isinstance(res, list)
    except Exception:
        return False


def build_vector_index(conn=None) -> dict:
    """Index the RAG corpus. Attempts TigerVector first; falls back to in-memory.

    Returns counts only: {"mode", "chunks", "pattern_docs", "policy_chunks", "closed_cases"}.
    """
    global _CORPUS, _TG_SEARCH_OK
    corpus = _ensure_corpus(conn)
    mode = "in_memory"
    if conn is not None:
        try:
            if _ensure_docchunk(conn) and _ensure_vector_attribute(conn) and _install_search_query(conn):
                failures = 0
                for chunk in corpus:
                    try:
                        conn.upsertVertex("DocChunk", re.sub(r"[^A-Za-z0-9_]+", "_", chunk["ref"]), {
                            "ref": chunk["ref"],
                            "content": chunk["text"],
                            "embedding": chunk["embedding"],
                        })
                    except Exception:
                        failures += 1
                        break
                if failures == 0 and _probe_vector_search(conn):
                    mode = "tigergraph"
                    _TG_SEARCH_OK = True
        except Exception:
            mode = "in_memory"
    return {
        "mode": mode,
        "chunks": len(corpus),
        "pattern_docs": len(PATTERN_DOCS),
        "policy_chunks": len([c for c in corpus if c["ref"].startswith("policy:")]),
        "closed_cases": len([c for c in corpus if c["ref"].startswith("closed_case:")]),
    }


def _tg_search(conn, qvec: list, top_k: int) -> list:
    """Top-k chunk refs via the installed vectorSearch query."""
    res = conn.runInstalledQuery(RAG_SEARCH_QUERY, {"query_vec": qvec, "k": top_k})
    hits = []
    for entry in res:
        if isinstance(entry, dict) and "v" in entry:
            for row in entry["v"]:
                attrs = row.get("attributes", row) if isinstance(row, dict) else {}
                ref = attrs.get("ref", row.get("v_id", "")) if isinstance(row, dict) else ""
                if ref:
                    hits.append({"ref": ref, "text": attrs.get("content", ""), "score": 1.0})
            break
    return hits


def retrieve_context(conn, queries: list, top_k: int = 3) -> list:
    """Return top_k [{"source": "document", "ref", "text", "score"}] across queries."""
    corpus = _ensure_corpus(conn)
    if not corpus or not queries:
        return []
    scores: dict = {}
    for query in queries:
        qvec = embed(query)
        if _TG_SEARCH_OK and conn is not None:
            try:
                for hit in _tg_search(conn, qvec, top_k):
                    current = scores.get(hit["ref"])
                    if current is None or hit["score"] > current["score"]:
                        scores[hit["ref"]] = hit
                continue
            except Exception:
                pass
        for chunk in corpus:
            score = _cosine(qvec, chunk["embedding"])
            current = scores.get(chunk["ref"])
            if current is None or score > current["score"]:
                scores[chunk["ref"]] = {"ref": chunk["ref"], "text": chunk["text"], "score": round(score, 4)}
    ranked = sorted(scores.values(), key=lambda s: s["score"], reverse=True)[:top_k]
    return [
        {"source": "document", "ref": s["ref"], "text": s["text"][:240], "score": s["score"]}
        for s in ranked
    ]


if __name__ == "__main__":
    _ensure_corpus(None)
    print(json.dumps({"chunks": len(_CORPUS), "policy_chunks": len(load_policy_text())}))
