# Snowflake Research Assistant — Team Plan

## 🎯 **Objective**
Our goal is to build a Personalized Research Assistant powered by **Snowflake**, **Retrieval-Augmented Generation (RAG)**, and **Knowledge Graphs**. 

Unlike standard RAG, this system uses a dual-retrieval approach (Vector + Graph) to provide explicit citations and confidence scores based on academic datasets (arXiv/PubMed).

## 🏗️ **Core Infrastructure Overview**
The architecture consists of four main domains:
1.  **Snowflake Data Layer**: Vector storage for text chunks, Relational tables for the Knowledge Graph, and Logistics tracking (`METRICS`).
2.  **Ingestion Pipeline**: Python jobs to embed the academic papers and extract graph entities.
3.  **Backend AI Service**: API that orchestrates the Vector search, Graph traversal, and LLM prompt generation.
4.  **Frontend & Evaluation**: Streamlit Dashboard for user chat, plus automated logging of RAGAS metrics.

---

## 👥 **Role-Based Task Breakdown (3 Engineers)**

### **Engineer 1: The Data & Ingestion Specialist 🏗️**
**Focus:** Establishing the Snowflake infrastructure and managing the document processing pipelines.

*   **Core Responsibilities:**
    *   **SQL Definitions:** Finalize `sql/01_create_schema.sql` by ensuring the `RAW` (Vector) and `GRAPH` schema architectures accurately map to the target datasets.
    *   **Data Processing:** Complete `data/ingestion.py`. You will need to take the raw arXiv datasets, clean the text, and split them into semantic chunks.
    *   **Embeddings:** Connect to OpenAI (or local HuggingFace) APIs to generate standard text embeddings for the vector database.
    *   **Knowledge Extraction:** Write scripts to extract Nodes (Entities) and Edges (Relationships) from the paper abstracts/text, pushing these directly into the `GRAPH.KNOWLEDGE_EDGES` tables using Snowpark.

---

### **Engineer 2: The AI & Backend Architect 🧠**
**Focus:** Orchestrating the retrieval logic and securely connecting the LLM.

*   **Core Responsibilities:**
    *   **Vector Search (`vector_search`):** Execute Cosine Similarity queries against Snowflake's specific `VECTOR L2 DISTANCE` syntax using the `RAW.CHUNKS` table.
    *   **Graph Traversal (`graph_search`):** Query the knowledge graph to find immediate entity relationships connected to the user's keywords.
    *   **LLM Synthesis (`synthesize_answer`):** Assemble the final prompt by injecting the retrieved chunks AND graph entities. Call the chosen LLM (Snowflake Cortex or OpenAI).
    *   **Citations:** Ensure the API natively tracks which `CHUNK_ID` or Node successfully contributed to the LLM response, passing this back to the frontend.

---

### **Engineer 3: The Frontend & Evaluation Lead 💻📊**
**Focus:** User Interface (UI), User Experience (UX), and continuous model testing.

*   **Core Responsibilities:**
    *   **Dashboard Development:** Manage `frontend/app.py` in Streamlit. Ensure users can organically type queries and view the LLM's returned message.
    *   **Citation Viewer:** Build out the interactive "View Citations & Confidence" block, creating a seamless UX that links exact sources to the text.
    *   **RAG Validation:** Implement scripts in `evaluation/evaluate.py` to compare standard Vector Search against Graph-Augmented Search using metrics like *Faithfulness* and *Answer Relevance*.
    *   **Metrics Logging:** Create the telemetry hooks. Every final answer rendered on the frontend needs its success metadata pushed to the `APP.EVAL_METRICS` table in Snowflake.

---

## 📅 **Execution Plan**

1.  **Phase 1 (Setup):** [Complete] All engineers have access to Snowflake and the repo structure is initialized.
2.  **Phase 2 (Ingestion):** Engineer 1 populates the database with real arXiv dataset embeddings and test-graph nodes.
3.  **Phase 3 (Backend/AI):** Engineer 2 builds the `retrieval.py` functions to successfully pull context *from* the populated Snowflake DB, wrapping it in FastAPI.
4.  **Phase 4 (UI/Eval):** Engineer 3 wires Streamlit to the Backend API and ensures responses log properly.
5.  **Phase 5 (Refinement):** The entire team optimizes latency, tweaks the UI, and finalizes the `/reproducibility` documentation.
