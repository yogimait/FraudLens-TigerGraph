# TigerGraph — Setup, Queries, MCP, GraphRAG

> [[Home]] · [[Data-Model]] · [[Architecture]] · [[Agent-Workflow]]

## Setup

### TigerGraph Savanna (recommended for hackathon)
1. Sign up at https://savanna.tgcloud.io
2. Create workspace → "Explore with Your Own Data"
3. **Enable auto-stop and auto-start** (challenge requirement)
4. Note: free tier; stop workspace when not using

### TigerGraph MCP
```bash
pip install tigergraph-mcp
```
- Requires Python 3.10–3.14
- Requires TigerGraph 4.1+ (4.2+ for TigerVector)
- Supports **stdio** and **streamable HTTP** transports
- Repo: https://github.com/tigergraph/tigergraph-mcp

Run MCP server:
```bash
# Streamable HTTP (for agent to connect remotely)
tigergraph-mcp --transport streamable-http --port 8001

# Or stdio (for same-process usage)
tigergraph-mcp --transport stdio
```

## Key GSQL Queries

### 1. `get_card_transactions` — Card transaction history
```gsql
CREATE QUERY get_card_transactions(VERTEX<Card> card, DATETIME start_time, DATETIME end_time) FOR GRAPH fraud_graph {
  txns = SELECT t FROM card:c -(MADE>)- Transaction:t
         WHERE t.ts >= start_time AND t.ts <= end_time
         ORDER BY t.ts ASC;
  PRINT txns;
}
```

### 2. `get_device_neighbors` — Cards sharing a device
```gsql
CREATE QUERY get_device_neighbors(VERTEX<DeviceProfile> device) FOR GRAPH fraud_graph {
  cards = SELECT c FROM device:d -(reverse_FROM_DEVICE>)- Transaction:t -(reverse_MADE>)- Card:c;
  PRINT cards;
}
```

### 3. `get_card_sequence` — Recent transactions in time window
```gsql
CREATE QUERY get_card_sequence(VERTEX<Card> card, INT hours) FOR GRAPH fraud_graph {
  now_minus_hours = datetime_sub(now(), INTERVAL hours HOUR);
  txns = SELECT t FROM card:c -(MADE>)- Transaction:t
         WHERE t.ts >= now_minus_hours
         ORDER BY t.ts ASC;
  PRINT txns;
}
```

### 4. `detect_card_testing` — Find testing patterns
```gsql
CREATE QUERY detect_card_testing(VERTEX<Card> card, DATETIME around_time) FOR GRAPH fraud_graph {
  // Find 3+ small txns (<$5) within 1 hour followed by larger purchase
  window_start = datetime_sub(around_time, INTERVAL 2 HOUR);
  window_end = datetime_add(around_time, INTERVAL 2 HOUR);

  txns = SELECT t FROM card:c -(MADE>)- Transaction:t
         WHERE t.ts >= window_start AND t.ts <= window_end
         AND t.channel == "online"
         ORDER BY t.ts ASC;
  PRINT txns;
  // Agent analyzes the sequence for small→large pattern
}
```

### 5. `get_region_activity` — Customer's regional history
```gsql
CREATE QUERY get_region_activity(STRING customer_id) FOR GRAPH fraud_graph {
  regions = SELECT r FROM Customer:c -(OWNS>)- Card:k -(MADE>)- Transaction:t -(BILLED_IN>)- BillingRegion:r
            WHERE c.customer_id == customer_id;
  PRINT regions;
}
```

### 6. `find_closed_cases_for_entity` — Case memory lookup
```gsql
CREATE QUERY find_closed_cases_for_entity(STRING card_id) FOR GRAPH fraud_graph {
  cases = SELECT cc FROM Card:c -(reverse_ON_CARD>)- ClosedCase:cc
          WHERE c.card_id == card_id;
  connected = SELECT cc FROM Card:c -(reverse_CONNECTED_TO>)- ClosedCase:cc
              WHERE c.card_id == card_id;
  PRINT cases, connected;
}
```

### 7. `get_customer_exposure` — Total exposure across cards
```gsql
CREATE QUERY get_customer_exposure(STRING customer_id, LIST<STRING> txn_ids) FOR GRAPH fraud_graph {
  total = SELECT t FROM Customer:c -(OWNS>)- Card:k -(MADE>)- Transaction:t
          WHERE t.txn_id IN txn_ids;
  PRINT total;  // Agent sums amounts
}
```

### 8. `write_investigation_case` — Persist case to graph
```gsql
CREATE QUERY write_investigation_case(
  STRING case_id, STRING source_case_id, STRING status, STRING verdict,
  FLOAT fraud_probability, STRING pattern, FLOAT exposure_usd,
  STRING summary, LIST<STRING> txn_ids, STRING primary_card_id,
  LIST<STRING> connected_card_ids
) FOR GRAPH fraud_graph {
  // Create case vertex
  INSERT INTO InvestigationCase VALUES(case_id, source_case_id, status, verdict,
    fraud_probability, pattern, exposure_usd, summary, now());

  // Create edges
  FOREACH tid IN txn_ids DO
    INSERT INTO INVOLVES VALUES(case_id, tid);
  END;

  INSERT INTO ON_CARD VALUES(case_id, primary_card_id);

  FOREACH cid IN connected_card_ids DO
    INSERT INTO CONNECTED_TO VALUES(case_id, cid);
  END;
}
```

## Graph Algorithms (Relevant)

| Algorithm | Use Case |
|---|---|
| **Connected Components** | Find fraud rings — groups of cards/customers sharing devices |
| **PageRank** | Identify central nodes in suspicious networks |
| **k-Hop Neighbors** | Expand investigation radius from flagged transaction |
| **Shortest Path** | Trace connections between flagged and known fraud entities |
| **Community Detection** | Identify clusters of coordinated activity |

## GraphRAG — Vector Search

Load into TigerGraph vector store:
1. **Closed case analyst_notes** — embeddings of case narratives for similarity search
2. **Fraud policy text** — policy rules R1–R10 for retrieval
3. **Pattern descriptions** — the 5 known patterns + regulatory guidance
4. **Dataset README pattern section** — detailed pattern definitions

**Usage**: When investigating, vector-search for:
- Cases with similar evidence patterns
- Relevant policy rules for current situation
- Pattern descriptions matching observed behavior

## Cross-References

- Schema details: [[Data-Model]]
- How agent uses these: [[Agent-Workflow]]
- MCP in architecture: [[Architecture]]
