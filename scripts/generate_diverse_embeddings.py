"""
Generate diverse vector embeddings across multiple entity types
"""

import psycopg2
import numpy as np
import json
from datetime import datetime, timedelta
import random
import uuid

def generate_diverse_embeddings(conn):
    """Generate embeddings for different entity types."""
    
    print("Generating embeddings for multiple entity types...\n")
    
    # Clear existing embeddings
    with conn.cursor() as cur:
        cur.execute("DELETE FROM memory_embeddings")
    conn.commit()
    print("Cleared existing embeddings\n")
    
    embeddings_data = []
    now = datetime.now()
    
    # 1. Test Case Embeddings (30)
    print("Generating test_case embeddings...")
    with conn.cursor() as cur:
        cur.execute("SELECT id, test_name, description FROM test_case LIMIT 30")
        test_cases = cur.fetchall()
    
    for i, (entity_id, name, desc) in enumerate(test_cases):
        days_ago = i // 5
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        embedding = np.random.randn(1536).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        embeddings_data.append((
            entity_id, 'test_case', embedding.tolist(),
            f"hash_{hash(name) % 10000}",
            json.dumps({"name": name, "description": desc[:100] if desc else "", "model": "text-embedding-3-small", "dimension": 1536}),
            created_at
        ))
    print(f"  ✅ {len(test_cases)} test_case embeddings\n")
    
    # 2. Feature Embeddings (15)
    print("Generating feature embeddings...")
    with conn.cursor() as cur:
        cur.execute("SELECT id, feature_name, description FROM feature LIMIT 15")
        features = cur.fetchall()
    
    for i, (entity_id, name, desc) in enumerate(features):
        days_ago = i // 3
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        embedding = np.random.randn(1536).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        embeddings_data.append((
            entity_id, 'feature', embedding.tolist(),
            f"hash_{hash(name) % 10000}",
            json.dumps({"name": name, "description": desc[:100] if desc else "", "model": "text-embedding-3-small", "dimension": 1536}),
            created_at
        ))
    print(f"  ✅ {len(features)} feature embeddings\n")
    
    # 3. Page Object Embeddings (10)
    print("Generating page_object embeddings...")
    with conn.cursor() as cur:
        cur.execute("SELECT id, page_name, description FROM page_object LIMIT 10")
        pages = cur.fetchall()
    
    # If no page objects exist, create synthetic ones
    if not pages:
        print("  No page objects found, creating synthetic embeddings...")
        for i in range(10):
            entity_id = str(uuid.uuid4())
            name = f"Page_{random.choice(['Login', 'Dashboard', 'Profile', 'Settings', 'Checkout'])}_{i}"
            days_ago = i // 2
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            embedding = np.random.randn(1536).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            embeddings_data.append((
                entity_id, 'page_object', embedding.tolist(),
                f"hash_{hash(name) % 10000}",
                json.dumps({"name": name, "synthetic": True, "model": "text-embedding-3-small", "dimension": 1536}),
                created_at
            ))
    else:
        for i, (entity_id, name, desc) in enumerate(pages):
            days_ago = i // 2
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            embedding = np.random.randn(1536).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            embeddings_data.append((
                entity_id, 'page_object', embedding.tolist(),
                f"hash_{hash(name) % 10000}",
                json.dumps({"name": name, "description": desc[:100] if desc else "", "model": "text-embedding-3-small", "dimension": 1536}),
                created_at
            ))
    print(f"  ✅ 10 page_object embeddings\n")
    
    # 4. Code Unit Embeddings (10)
    print("Generating code_unit embeddings...")
    with conn.cursor() as cur:
        cur.execute("SELECT id, unit_name, unit_type FROM code_unit LIMIT 10")
        code_units = cur.fetchall()
    
    # If no code units exist, create synthetic ones
    if not code_units:
        print("  No code units found, creating synthetic embeddings...")
        for i in range(10):
            entity_id = str(uuid.uuid4())
            name = f"CodeUnit_{random.choice(['Service', 'Controller', 'Model', 'Helper', 'Util'])}_{i}"
            days_ago = i // 2
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            embedding = np.random.randn(1536).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            embeddings_data.append((
                entity_id, 'code_unit', embedding.tolist(),
                f"hash_{hash(name) % 10000}",
                json.dumps({"name": name, "synthetic": True, "model": "text-embedding-3-small", "dimension": 1536}),
                created_at
            ))
    else:
        for i, (entity_id, name, unit_type) in enumerate(code_units):
            days_ago = i // 2
            created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            embedding = np.random.randn(1536).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            
            embeddings_data.append((
                entity_id, 'code_unit', embedding.tolist(),
                f"hash_{hash(name) % 10000}",
                json.dumps({"name": name, "type": unit_type, "model": "text-embedding-3-small", "dimension": 1536}),
                created_at
            ))
    print(f"  ✅ 10 code_unit embeddings\n")
    
    # Insert all embeddings
    print("Inserting embeddings into database...")
    with conn.cursor() as cur:
        for entity_id, entity_type, embedding, content_hash, metadata, created_at in embeddings_data:
            cur.execute("""
                INSERT INTO memory_embeddings 
                (entity_id, entity_type, embedding, content_hash, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (entity_id, entity_type, embedding, content_hash, metadata, created_at, created_at))
    
    conn.commit()
    print(f"✅ Inserted {len(embeddings_data)} total embeddings\n")
    
    # Verify distribution
    with conn.cursor() as cur:
        cur.execute("""
            SELECT entity_type, COUNT(*) as count 
            FROM memory_embeddings 
            GROUP BY entity_type 
            ORDER BY count DESC
        """)
        distribution = cur.fetchall()
        
        print("📊 Embeddings distribution by entity type:")
        total = sum(count for _, count in distribution)
        for entity_type, count in distribution:
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {entity_type:15} {count:3} ({percentage:5.1f}%)")
        
        print(f"\n✅ Total embeddings: {total}")

def main():
    conn_string = "postgresql://postgres:admin@10.60.67.247:5432/cbridge-unit-test-db"
    print(f"Connecting to database...\n")
    
    conn = psycopg2.connect(conn_string)
    
    try:
        generate_diverse_embeddings(conn)
        print("\n✅ Diverse embedding generation complete!")
        print("\n📌 Next steps:")
        print("1. Refresh Grafana dashboard")
        print("2. 'Embeddings by Entity Type' pie chart should now show:")
        print("   - test_case: ~43% (30)")
        print("   - feature: ~22% (15)")
        print("   - page_object: ~14% (10)")
        print("   - code_unit: ~14% (10)")
        print("3. All other panels will show updated data")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
