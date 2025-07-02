import sqlite3
import hashlib

class DatabaseManager:
    def __init__(self, db_path="repairpro.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    store_id INTEGER NOT NULL,
                    is_primary BOOLEAN DEFAULT 0,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
                )
            """)

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS store_technicians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER NOT NULL,
                    technician_id INTEGER NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                    FOREIGN KEY (technician_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(technician_id)
                )
            ''')

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
                    deposit_cost REAL DEFAULT 0,
                    raw_cost REAL DEFAULT 0,
                    estimate_cost REAL DEFAULT 0,
                    actual_cost REAL DEFAULT 0,
                    payment_status TEXT DEFAULT 'Pending',
                    payment_method TEXT,
                    status TEXT DEFAULT 'New',
                    store_id INTEGER,
                    assigned_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    started_at TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL,
                    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    photo BLOB NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technician_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technician_id INTEGER NOT NULL,
                    assigned_by INTEGER,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    FOREIGN KEY (technician_id) REFERENCES users(id),
                    FOREIGN KEY (assigned_by) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assignment_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    FOREIGN KEY (assignment_id) REFERENCES technician_assignments(id) ON DELETE CASCADE,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS old_mobiles (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            customer_name TEXT NOT NULL,
                            customer_phone TEXT NOT NULL,
                            customer_email TEXT,
                            aadhar_number TEXT,
                            customer_address TEXT,
                            mobile_brand TEXT NOT NULL,
                            mobile_model TEXT NOT NULL,
                            imei_number TEXT,
                            repair_status TEXT NOT NULL,
                            warranty_status TEXT NOT NULL,
                            repair_description TEXT,
                            estimated_value REAL DEFAULT 0,
                            purchase_date DATE,
                            accessories_included TEXT,
                            notes TEXT,
                            store_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
                        ); 
                           ''')

            cursor.execute("SELECT COUNT(*) FROM stores")
            if cursor.fetchone()[0] == 0:
                self._insert_default_data(cursor)

            conn.commit()
        def _insert_default_data(self, cursor):
            # Step 1: Insert default store
            cursor.execute(
                "INSERT INTO stores (name, location, phone, email) VALUES (?, ?, ?, ?)",
                ("Main Branch", "Head Office", "1234567890", "store@repairpro.com")
            )
            store_id = cursor.lastrowid

            # Step 2: Insert admin user
            admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password, role, full_name, email, store_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("admin", admin_pw, "admin", "System Admin", "admin@repairpro.com", store_id)
            )
            user_id = cursor.lastrowid

            # Step 3: Assign store to admin in user_stores table
            cursor.execute(
                "INSERT INTO user_stores (user_id, store_id, is_primary) VALUES (?, ?, ?)",
                (user_id, store_id, True)
            )


