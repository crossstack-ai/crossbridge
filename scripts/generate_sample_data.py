"""
Generate Sample Data for Grafana Dashboard Testing

This script creates sample behavioral coverage data to populate
Grafana dashboards when no real test data exists yet.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import random
import uuid
import json

# Register UUID adapter
psycopg2.extras.register_uuid()

# Database connection
DB_CONN = "postgresql://postgres:admin@10.55.12.99:5432/udp-native-webservices-automation"

def get_connection():
    """Get database connection"""
    return psycopg2.connect(DB_CONN)

def check_existing_data():
    """Check if data already exists in coverage tables"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM api_endpoint_coverage")
        api_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ui_component_coverage")
        ui_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM test_case")
        test_count = cursor.fetchone()[0]
        
        print(f"\n📊 Existing Data:")
        print(f"  - API Coverage Records: {api_count}")
        print(f"  - UI Coverage Records: {ui_count}")
        print(f"  - Test Cases: {test_count}")
        
        return api_count > 0 or ui_count > 0
    finally:
        cursor.close()
        conn.close()


def create_sample_test_cases(conn, count=10):
    """Create sample test case records"""
    cursor = conn.cursor()
    test_case_ids = []
    frameworks = ['pytest', 'selenium', 'playwright', 'cypress', 'robot']
    timestamp = int(datetime.now().timestamp())
    
    for i in range(count):
        test_id = str(uuid.uuid4())
        framework = random.choice(frameworks)
        cursor.execute("""
            INSERT INTO test_case (id, framework, package, class_name, method_name, file_path, tags, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            test_id,
            framework,
            f"tests.{framework}",
            f"Test{framework.capitalize()}_{timestamp}",
            f"test_sample_{timestamp}_{i}",
            f"tests/{framework}/test_sample_{i}.py",
            ['smoke', 'regression'],
            datetime.now() - timedelta(hours=random.randint(1, 24))
        ))
        test_case_ids.append(test_id)
    
    conn.commit()
    return test_case_ids

def generate_api_coverage(conn, test_case_ids: list, count=50):
    """Generate sample API coverage data"""
    cursor = conn.cursor()
    
    endpoints = [
        ("/api/users", "GET"),
        ("/api/users", "POST"),
        ("/api/users/{id}", "GET"),
        ("/api/users/{id}", "PUT"),
        ("/api/users/{id}", "DELETE"),
        ("/api/products", "GET"),
        ("/api/products", "POST"),
        ("/api/orders", "GET"),
        ("/api/orders", "POST"),
        ("/api/auth/login", "POST"),
        ("/api/auth/logout", "POST"),
        ("/api/settings", "GET"),
        ("/api/settings", "PATCH"),
    ]
    
    status_codes = [200, 201, 204, 400, 401, 404, 500]
    weights = [60, 20, 10, 4, 2, 3, 1]  # Mostly successful
    
    for i in range(count):
        endpoint, method = random.choice(endpoints)
        test_id = random.choice(test_case_ids)
        status = random.choices(status_codes, weights=weights)[0]
        
        cursor.execute("""
            INSERT INTO api_endpoint_coverage (
                id, test_case_id, endpoint_path, http_method, status_code,
                execution_time_ms, request_schema, response_schema, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            uuid.uuid4(),
            test_id,
            endpoint,
            method,
            status,
            random.uniform(10, 500),
            json.dumps({"type": "object", "properties": {"sample": {"type": "string"}}}) if method in ['POST', 'PUT', 'PATCH'] else None,
            json.dumps({"type": "object", "properties": {"result": {"type": "string"}}}) if status < 400 else json.dumps({"type": "object", "properties": {"error": {"type": "string"}}}),
            datetime.now() - timedelta(hours=random.randint(0, 24))
        ))
    
    conn.commit()
    print(f"✅ Generated {count} API coverage records")

def generate_ui_coverage(conn, test_case_ids: list, count=40):
    """Generate sample UI coverage data"""
    cursor = conn.cursor()
    
    components = [
        ("LoginButton", "button", "click", "/login"),
        ("UsernameInput", "input", "type", "/login"),
        ("PasswordInput", "input", "type", "/login"),
        ("SubmitForm", "form", "submit", "/login"),
        ("ProductCard", "div", "click", "/products"),
        ("AddToCartButton", "button", "click", "/products"),
        ("SearchBar", "input", "type", "/search"),
        ("NavigationMenu", "nav", "click", "/"),
        ("UserProfile", "div", "click", "/profile"),
        ("LogoutButton", "button", "click", "/profile"),
        ("FilterDropdown", "select", "change", "/products"),
        ("SortButton", "button", "click", "/products"),
    ]
    
    for i in range(count):
        component, comp_type, interaction, page = random.choice(components)
        test_id = random.choice(test_case_ids)
        
        cursor.execute("""
            INSERT INTO ui_component_coverage (
                id, test_case_id, component_name, component_type, interaction_type,
                page_url, interaction_count, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            uuid.uuid4(),
            test_id,
            component,
            comp_type,
            interaction,
            page,
            random.randint(1, 10),
            datetime.now() - timedelta(hours=random.randint(0, 24))
        ))
    
    conn.commit()
    print(f"✅ Generated {count} UI coverage records")

def generate_network_coverage(conn, test_case_ids: list, count=30):
    """Generate sample network capture data"""
    cursor = conn.cursor()
    
    resources = [
        ("https://cdn.example.com/styles.css", "stylesheet", 1024, 50),
        ("https://cdn.example.com/app.js", "script", 2048, 100),
        ("https://api.example.com/data", "xhr", 512, 200),
        ("https://cdn.example.com/logo.png", "image", 4096, 30),
        ("https://api.example.com/metrics", "fetch", 256, 150),
    ]
    
    for i in range(count):
        url, res_type, size, duration = random.choice(resources)
        test_id = random.choice(test_case_ids)
        
        cursor.execute("""
            INSERT INTO network_capture (
                id, test_case_id, request_url, request_method, response_status,
                duration_ms, timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            uuid.uuid4(),
            test_id,
            url,
            "GET",
            200,
            duration + random.uniform(-20, 50),
            datetime.now() - timedelta(hours=random.randint(0, 24))
        ))
    
    conn.commit()
    print(f"✅ Generated {count} network capture records")

def generate_contract_coverage(conn, test_case_ids: list, count=20):
    """Generate sample contract coverage data"""
    cursor = conn.cursor()
    
    contracts = [
        ("user-service", "v1", "/api/users", "GET"),
        ("user-service", "v1", "/api/users", "POST"),
        ("product-service", "v2", "/api/products", "GET"),
        ("order-service", "v1", "/api/orders", "POST"),
        ("auth-service", "v1", "/api/auth/login", "POST"),
    ]
    
    for i in range(count):
        service, version, endpoint, method = random.choice(contracts)
        test_id = random.choice(test_case_ids)
        passed = random.random() > 0.25  # 75% pass
        
        cursor.execute("""
            INSERT INTO contract_coverage (
                id, test_case_id, contract_name, contract_version,
                request_fields_covered, response_fields_covered, validation_passed,
                validation_errors, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            uuid.uuid4(),
            test_id,
            f"{service}.{endpoint.replace('/', '.')}.{method}",
            version,
            ['id', 'name'] if method in ['POST', 'PUT'] else [],
            ['id', 'name', 'created_at', 'status'],
            passed,
            [] if passed else ['Field mismatch: id expected string but got number'],
            datetime.now() - timedelta(hours=random.randint(0, 24))
        ))
    
    conn.commit()
    print(f"✅ Generated {count} contract coverage records")


def main():
    print("🚀 CrossBridge Sample Data Generator")
    print("=" * 50)
    
    try:
        # Check existing data
        has_data = check_existing_data()
        
        if has_data:
            response = input("\n⚠️  Data already exists. Regenerate? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cancelled.")
                return
            
            # Clear existing data
            print("\n🗑️  Clearing existing coverage data...")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM contract_coverage")
            cursor.execute("DELETE FROM network_capture")
            cursor.execute("DELETE FROM ui_component_coverage")
            cursor.execute("DELETE FROM api_endpoint_coverage")
            cursor.execute("DELETE FROM test_case")
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Cleared existing data")
        
        # Generate new data
        print("\n📝 Generating sample data...")
        
        # Create connection for all operations
        conn = get_connection()
        
        try:
            # Create test cases
            print("\n1️⃣  Creating test cases...")
            test_case_ids = create_sample_test_cases(conn, count=10)
            print(f"✅ Created {len(test_case_ids)} test cases")
            
            # Generate coverage data
            print("\n2️⃣  Generating API coverage...")
            generate_api_coverage(conn, test_case_ids, count=50)
            
            print("\n3️⃣  Generating UI coverage...")
            generate_ui_coverage(conn, test_case_ids, count=40)
            
            print("\n4️⃣  Generating network coverage...")
            generate_network_coverage(conn, test_case_ids, count=30)
            
            print("\n5️⃣  Generating contract coverage...")
            generate_contract_coverage(conn, test_case_ids, count=20)
            
            # Verify data
            conn.close()
            print("\n" + "=" * 50)
            check_existing_data()
            
            print("\n✅ Sample data generation complete!")
            print("\n📊 Next steps:")
            print("  1. Open Grafana: http://10.55.12.99:3000/")
            print("  2. Go to your dashboard")
            print("  3. Refresh the page")
            print("  4. All panels should now display data!")
            
        finally:
            conn.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
