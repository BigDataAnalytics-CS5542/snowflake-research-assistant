from typing import List, Dict

import json, os, numpy as np
from scripts.sf_connect import get_conn

def get_top_chunks(query_text, top_k=5, passcode=''):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
    query_vec = model.encode([query_text], normalize_embeddings=True)[0]

    conn = get_conn(passcode=passcode)
    cur = conn.cursor()
    cur.execute('USE WAREHOUSE ROHAN_BLAKE_KENNETH_WH')
    cur.execute('USE DATABASE CS5542_PROJECT_ROHAN_BLAKE_KENNETH')
    cur.execute(
        'SELECT CHUNK_ID, PAPER_ID, TITLE, SECTION_NAME, TEXT_CONTENT, EMBEDDING FROM APP.CHUNKS_V'
    )
    rows = cur.fetchall()
    conn.close()

    results = []
    for chunk_id, paper_id, title, section, text, emb_json in rows:
        emb = np.array(json.loads(emb_json))
        score = float(np.dot(query_vec, emb))
        results.append((score, chunk_id, paper_id, title, section, text))

    results.sort(reverse=True)
    return results[:top_k]



def graph_search(entities: List[str], passcode: str = '') -> List[Dict]:
    '''
    Query GRAPH.KNOWLEDGE_EDGES and KNOWLEDGE_NODES to find relations 
    connected to the extracted entities.
    '''
    if not entities:
        return []

    conn = get_conn(passcode=passcode)
    cur = conn.cursor()
    
    # 1. Setup session context
    cur.execute('USE WAREHOUSE ROHAN_BLAKE_KENNETH_WH')
    cur.execute('USE DATABASE CS5542_PROJECT_ROHAN_BLAKE_KENNETH')

    # 2. Normalize entities for matching (assuming case-insensitive search)
    # We use a parameterized query to prevent injection and handle the IN clause
    placeholders = ', '.join(['%s'] * len(entities))
    normalized_entities = [e.strip().upper() for e in entities]

    query = f"""
    WITH target_nodes AS (
        -- Find IDs for the entities provided
        SELECT NODE_ID, NAME 
        FROM GRAPH.KNOWLEDGE_NODES 
        WHERE NAME_NORMALIZED IN ({placeholders})
    )
    SELECT 
        tn.NAME as SOURCE_ENTITY,
        e.RELATION_TYPE,
        n2.NAME as TARGET_ENTITY,
        e.WEIGHT
    FROM target_nodes tn
    JOIN GRAPH.KNOWLEDGE_EDGES e ON tn.NODE_ID = e.SOURCE_NODE_ID
    JOIN GRAPH.KNOWLEDGE_NODES n2 ON e.TARGET_NODE_ID = n2.NODE_ID
    
    UNION ALL
    
    SELECT 
        n2.NAME as SOURCE_ENTITY,
        e.RELATION_TYPE,
        tn.NAME as TARGET_ENTITY,
        e.WEIGHT
    FROM target_nodes tn
    JOIN GRAPH.KNOWLEDGE_EDGES e ON tn.NODE_ID = e.TARGET_NODE_ID
    JOIN GRAPH.KNOWLEDGE_NODES n2 ON e.SOURCE_NODE_ID = n2.NODE_ID
    """

    cur.execute(query, normalized_entities + normalized_entities)
    rows = cur.fetchall()
    conn.close()

    # 3. Format results into a list of dictionaries
    graph_results = []
    for src, rel, tgt, weight in rows:
        graph_results.append({
            "source": src,
            "relation": rel,
            "target": tgt,
            "weight": float(weight) if weight else 1.0
        })

    return graph_results

