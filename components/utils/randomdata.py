import sqlite3
import random
from faker import Faker

fake = Faker()

DB_PATH = "/Users/jayanth/Documents/GitHub/refactored-JobSheet/repairpro.db"  

def seed_stores(conn, count=50):
    print("Seeding stores...")
    cursor = conn.cursor()
    for _ in range(count):
        name = f"{fake.company()} Store"
        location = fake.address()
        phone = fake.phone_number()
        email = fake.company_email()

        cursor.execute("""
            INSERT INTO stores (name, location, phone, email)
            VALUES (?, ?, ?, ?)
        """, (name, location, phone, email))
    conn.commit()

def seed_customers(conn, count=50):
    print("Seeding customers...")
    cursor = conn.cursor()
    store_ids = [row[0] for row in cursor.execute("SELECT id FROM stores").fetchall()]
    for _ in range(count):
        name = fake.name()
        phone = fake.phone_number()
        email = fake.email()
        address = fake.address()
        store_id = random.choice(store_ids)

        cursor.execute("""
            INSERT INTO customers (name, phone, email, address, store_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, phone, email, address, store_id))
    conn.commit()

def seed_jobs(conn, count=50):
    print("Seeding jobs...")
    cursor = conn.cursor()
    store_ids = [row[0] for row in cursor.execute("SELECT id FROM stores").fetchall()]
    statuses = ["Pending", "In Progress", "Completed"]
    technicians = [fake.name() for _ in range(10)] + ["Unassigned"]

    for _ in range(count):
        customer_name = fake.name()
        device_type = random.choice(["Phone", "Laptop", "Tablet", "Smartwatch"])
        device_model = f"{device_type} {fake.word().capitalize()}"
        problem_description = fake.sentence(nb_words=6)
        estimated_cost = round(random.uniform(50, 500), 2)
        status = random.choice(statuses)
        technician = random.choice(technicians)
        store_id = random.choice(store_ids)

        cursor.execute("""
            INSERT INTO jobs (customer_name, device_type, device_model, 
                              problem_description, estimated_cost, status, 
                              technician, store_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_name, device_type, device_model, problem_description,
              estimated_cost, status, technician if technician != "Unassigned" else None, store_id))
    conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    
    seed_stores(conn)
    seed_customers(conn)
    seed_jobs(conn)
    
    print("✅ Done seeding dummy data!")
    conn.close()
