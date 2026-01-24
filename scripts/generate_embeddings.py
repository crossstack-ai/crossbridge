"""
Generate sample vector embeddings for CrossBridge database
"""

import psycopg2
import numpy as np
import json
from datetime import datetime

def generate_sample_embeddings(conn):
    """Generate sample 1536-dimensional embeddings for test cases."""
    
    # Get test case IDs
    with conn.cursor() as cur:
        cur.execute("SELECT id, test_name, description FROM test_case LIMIT 50")
        test_cases = cur.fetchall()
    
    print(f"Generating embeddings for {len(test_cases)} test cases...")
    
    # Generate embeddings
    embeddings_data = []
    for test_id, test_name, description in test_cases:
        # Generate random 1536-dimensional vector (normalized)
        # In production, this would come from OpenAI API
        embedding = np.random.randn(1536).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        embeddings_data.append((
            test_id,  # entity_id
            'test_case',  # entity_type
            embedding.tolist(),  # embedding vector
            f"hash_{hash(test_name) % 10000}",  # content_hash
            json.dumps({
                "test_name": test_name,
                "description": description[:100] if description else "",
                "model": "text-embedding-3-small",
                "dimension": 1536
            })
        ))
    
    # Insert embeddings
    with conn.cursor() as cur:
        for entity_id, entity_type, embedding, content_hash, metadata in embeddings_data:
            cur.execute("""
                INSERT INTO memory_embeddings 
                (entity_id, entity_type, embedding, content_hash, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (entity_type, entity_id) DO UPDATE 
                SET embedding = EXCLUDED.embedding,
                    content_hash = EXCLUDED.content_hash,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, (entity_id, entity_type, embedding, content_hash, metadata))
    
    conn.commit()
    print(f"✅ Generated {len(embeddings_data)} embeddings")
    
    # Verify
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memory_embeddings")
        count = cur.fetchone()[0]
        print(f"✅ Total embeddings in database: {count}")

def main():
    conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    print(f"Connecting to database...")
    
    conn = psycopg2.connect(conn_string)
    
    try:
        generate_sample_embeddings(conn)
        print("\n✅ Embedding generation complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
