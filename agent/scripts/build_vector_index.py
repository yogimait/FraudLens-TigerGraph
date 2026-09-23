"""CLI: build the GraphRAG vector index. Prints counts only; never crashes offline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    conn = None
    try:
        import pyTigerGraph as tg

        conn = tg.TigerGraphConnection(
            host=os.environ.get("TG_HOST", ""),
            graphname=os.environ.get("TG_GRAPH", "FraudGraph"),
            gsqlSecret=os.environ.get("TG_SECRET", ""),
            tgCloud=True,
        )
        conn.getToken(conn.createSecret())
    except Exception as e:
        print(f"Skipping vector index build, TigerGraph unreachable: {type(e).__name__}: {e}")
        return 0

    try:
        import rag

        result = rag.build_vector_index(conn)
        print(f"Vector index built: mode={result['mode']}, chunks={result['chunks']}, "
              f"pattern_docs={result['pattern_docs']}, policy_chunks={result['policy_chunks']}, "
              f"closed_cases={result['closed_cases']}")
    except Exception as e:
        print(f"Skipping vector index build: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
