# FraudLens: Ops Intelligence

An agentic fraud investigation system built for the TigerGraph Agentic Fraud Investigation Hackathon (HHGOA / IEEE-CIS Fraud dataset).

## Motive of the Project
The goal of this project is to automate the grueling, manual process of fraud investigation by employing a multi-agent AI system. In traditional financial systems, analysts manually pull data from disparate sources (graphs, tables, APIs), try to piece together complex attack vectors, and write Suspicious Activity Reports (SARs). This is slow, error-prone, and scales poorly.

FraudLens acts as a highly autonomous "digital analyst" that:
1. Translates a raw transaction alert into deep context using **TigerGraph** (uncovering hidden connections like shared devices, IP overlaps, and card testing networks).
2. Uses **Jev** for ultra-fast, deterministic heuristics based on dataset parameters (Risk Score, Amount, Transaction Distances).
3. Synthesizes this evidence using an **LLM** to identify the specific fraud pattern.
4. Makes a deterministic policy routing decision (e.g. `BLOCK_ALL_CARDS`, `L1_APPROVAL` required).
5. Interacts with a Next.js **Dashboard** to keep human analysts in the loop for edge cases and approvals.

## How It Works
The architecture consists of three core components, interacting in real-time:

1. **The LangGraph Agent (Python/FastAPI):**
   - The brains of the operation. Triggered via HTTP.
   - Runs three GSQL queries against TigerGraph Savanna.
   - Computes total financial exposure and builds a structured evidence map.
   - Generates a human-readable synthesis and formats a ready-to-file SAR.
   - Returns the entire state (including the literal graph nodes/edges) to the backend.

2. **The Backend (NestJS/TypeScript):**
   - A robust API built on NestJS and MongoDB (using Mongoose).
   - Serves as the central state manager (Case Memory).
   - Forwards "Trigger" requests to the Agent, and persists the Agent's rich JSON output.
   - Exposes REST endpoints for the frontend to query cases, stats, and approve/reject actions.

3. **The Frontend (Next.js/React):**
   - A "Bloomberg Terminal"-esque dark-mode dashboard tailored for Fraud Analysts.
   - Features dynamic KPIs, real-time investigation triggers, graph visualization (using React Flow), and a dedicated Approvals center for policy-restricted actions.

## Quick Start (How to Run)

To run the entire system locally, you need three terminal windows.

### 1. Start the Backend API (NestJS)
```bash
cd backend
npm install
npm run start:dev
```
*(Runs on `http://localhost:3001`)*

### 2. Start the AI Agent (Python FastAPI)
```bash
cd agent
pip install -r requirements.txt
python main.py
```
*(Runs on `http://localhost:8000`)*

### 3. Start the Frontend Dashboard (Next.js)
```bash
cd frontend
npm install
npm run dev
```
*(Runs on `http://localhost:3000`)*

## Demo Guide
1. Navigate to `http://localhost:3000` in your browser.
2. Click **New Investigation** in the top right.
3. Enter a valid Transaction ID from the dataset (e.g. `3514030` or `3391850`) and click **Run Agent**.
4. The backend will trigger the Python Agent. You'll see a new case appear.
5. Click **View** to see the detailed Case Analysis, including the Interactive Graph, Synthesis, SAR Report, and deterministic Policy Actions!
