import sqlite3
import hashlib
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="repairpro.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        return conn

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # === STORES TABLE ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # === USERS TABLE ===
            cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'manager', 'staff', 'technician')) DEFAULT 'staff',
            full_name TEXT,
            email TEXT,
            store_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
        )
    ''')

            # === STORE_TECHNICIANS TABLE ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS store_technicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER NOT NULL,
                    technician_id INTEGER NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(store_id, technician_id)
                )
            ''')

            # === CUSTOMERS TABLE ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    address TEXT,
                    store_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
                )
            ''')

            # === JOBS TABLE ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    device_type TEXT NOT NULL,
                    device_model TEXT,
                    device_password_type TEXT,
                    device_password TEXT,
                    notification_methods TEXT,
                    problem_description TEXT NOT NULL,
                    estimated_cost REAL DEFAULT 0,
                    actual_cost REAL DEFAULT 0,
                    status TEXT DEFAULT 'New',
                    store_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
                )
            ''')

            # === JOB PHOTOS TABLE ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    photo BLOB NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')

            # === TECHNICIAN ASSIGNMENTS ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technician_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technician_id INTEGER NOT NULL,
                    assigned_by INTEGER,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    FOREIGN KEY (technician_id) REFERENCES users(id),
                    FOREIGN KEY (assigned_by) REFERENCES users(id)
                )
            ''')

            # === ASSIGNMENT JOBS ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assignment_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    FOREIGN KEY (assignment_id) REFERENCES technician_assignments(id) ON DELETE CASCADE,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')



            # === Insert default data only if first run ===
            cursor.execute("SELECT COUNT(*) FROM stores")
            if cursor.fetchone()[0] == 0:
                # Default Stores
                stores = [
                    ("RepairPro Main", "Downtown Plaza", "555-0101", "main@repairpro.com"),
                    ("RepairPro North", "North Mall", "555-0102", "north@repairpro.com"),
                    ("RepairPro East", "Eastside Center", "555-0103", "east@repairpro.com")
                ]
                cursor.executemany("INSERT INTO stores (name, location, phone, email) VALUES (?, ?, ?, ?)", stores)

                # Admin and sample users
                admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
                cursor.execute("INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)",
                               ("admin", admin_pw, "admin", "System Admin", "admin@repairpro.com"))

                staff_pw = hashlib.sha256("staff123".encode()).hexdigest()
                staff_users = [
                    ("manager1", staff_pw, "manager", "John Doe", "john@repairpro.com"),
                    ("manager2", staff_pw, "manager", "Jane Smith", "jane@repairpro.com"),
                    ("reception1", staff_pw, "staff", "Alice Brown", "alice@repairpro.com"),
                    ("reception2", staff_pw, "staff", "Bob Green", "bob@repairpro.com")
                ]
                cursor.executemany("INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)",
                                   staff_users)

                tech_pw = hashlib.sha256("tech123".encode()).hexdigest()
                tech_users = [
                    ("tech_mike", tech_pw, "technician", "Mike Johnson", "mike@repairpro.com"),
                    ("tech_sarah", tech_pw, "technician", "Sarah Williams", "sarah@repairpro.com"),
                    ("tech_david", tech_pw, "technician", "David Lee", "david@repairpro.com"),
                    ("tech_emma", tech_pw, "technician", "Emma Davis", "emma@repairpro.com"),
                    ("tech_james", tech_pw, "technician", "James Wilson", "james@repairpro.com"),
                    ("tech_lisa", tech_pw, "technician", "Lisa Taylor", "lisa@repairpro.com")
                ]
                cursor.executemany("INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)",
                                   tech_users)

                store_technicians = [
                    (1, 5), (1, 6), (2, 7), (2, 8), (3, 9), (3, 10),
                    (1, 7), (2, 6)  # multi-store assignments
                ]
                cursor.executemany("INSERT INTO store_technicians (store_id, technician_id) VALUES (?, ?)", store_technicians)

                customer_data = [
                    (1, "Tom Johnson", "555-1001", "tom@example.com", "123 Main St"),
                    (1, "Lisa Smith", "555-1002", "lisa@example.com", "456 Oak Ave"),
                    (2, "Robert Brown", "555-2001", "robert@example.com", "789 Pine Rd"),
                    (2, "Emily Wilson", "555-2002", "emily@example.com", "321 Elm St"),
                    (3, "Michael Davis", "555-3001", "michael@example.com", "654 Maple Dr")
                ]
                cursor.executemany(
                    "INSERT INTO customers (store_id, name, phone, email, address) VALUES (?, ?, ?, ?, ?)",
                    customer_data
                )

            conn.commit()

    def insert_job_photos(self, job_id, image_paths):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for image_path in image_paths:
                if not os.path.exists(image_path):
                    continue
                with open(image_path, 'rb') as f:
                    photo_blob = f.read()

                photo_hash = hashlib.sha256(photo_blob).hexdigest()

                cursor.execute(
                    "SELECT 1 FROM job_photos WHERE job_id = ? AND hex(photo) = ?",
                    (job_id, photo_hash)
                )
                if cursor.fetchone():
                    continue  # Skip duplicates

                cursor.execute(
                    "INSERT INTO job_photos (job_id, photo) VALUES (?, ?)",
                    (job_id, photo_blob)
                )

            conn.commit()

    def get_photos_for_job(self, job_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, photo FROM job_photos WHERE job_id = ?", (job_id,))
            photos = cursor.fetchall()

            for photo_id, blob in photos:
                with open(f"job_{job_id}_photo_{photo_id}.jpg", "wb") as f:
                    f.write(blob)