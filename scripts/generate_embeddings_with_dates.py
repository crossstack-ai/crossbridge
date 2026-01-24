"""
Generate vector embeddings with distributed timestamps for better Grafana visualization
"""

import psycopg2
import numpy as np
import json
from datetime import datetime, timedelta
import random

def generate_embeddings_with_dates(conn):
    """Generate embeddings spread over last 7 days."""
    
    # Get test case IDs
    with conn.cursor() as cur:
        cur.execute("SELECT id, test_name, description FROM test_case LIMIT 50")
        test_cases = cur.fetchall()
    
    print(f"Generating {len(test_cases)} embeddings spread over 7 days...")
    
    # Delete existing embeddings
    with conn.cursor() as cur:
        cur.execute("DELETE FROM memory_embeddings")
    conn.commit()
    print("Cleared existing embeddings")
    
    # Generate embeddings with distributed timestamps
    embeddings_data = []
    now = datetime.now()
    
    for i, (test_id, test_name, description) in enumerate(test_cases):
        # Distribute over last 7 days (7-8 per day)
        days_ago = (i // 7)  # 0-6 days ago
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        
        created_at = now - timedelta(days=days_ago, hours=hours_offset, minutes=minutes_offset)
        
        # Generate random 1536-dimensional vector (normalized)
        embedding = np.random.randn(1536).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        embeddings_data.append((
            test_id,
            'test_case',
            embedding.tolist(),
            f"hash_{hash(test_name) % 10000}",
            json.dumps({
                "test_name": test_name,
                "description": description[:100] if description else "",
                "model": "text-embedding-3-small",
                "dimension": 1536
            }),
            created_at
        ))
    
    # Insert with custom timestamps
    with conn.cursor() as cur:
        for entity_id, entity_type, embedding, content_hash, metadata, created_at in embeddings_data:
            cur.execute("""
                INSERT INTO memory_embeddings 
                (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (entity_id, entity_type, embedding, content_hash, metadata, created_at, created_at))
    
    conn.commit()
    print(f"✅ Generated {len(embeddings_data)} embeddings")
    
    # Verify distribution
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                DATE(created_at) as day, 
                COUNT(*) as count 
            FROM memory_embeddings 
            GROUP BY DATE(created_at) 
            ORDER BY day DESC
        """)
        distribution = cur.fetchall()
        
        print("\n📊 Embeddings distribution by day:")
        for day, count in distribution:
            print(f"  {day}: {count} embeddings")
        
        cur.execute("SELECT COUNT(*) FROM memory_embeddings")
        total = cur.fetchone()[0]
        print(f"\n✅ Total embeddings: {total}")

def main():
    conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    print(f"Connecting to database...")
    
    conn = psycopg2.connect(conn_string)
    
    try:
        generate_embeddings_with_dates(conn)
        print("\n✅ Embedding generation complete!")
        print("\n📌 Next steps:")
        print("1. Refresh Grafana dashboard")
        print("2. Check 'Embedding Storage Trend' panel - should show growth over 7 days")
        print("3. All other memory panels should show data")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
