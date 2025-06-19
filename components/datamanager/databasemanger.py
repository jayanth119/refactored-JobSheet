# Enhanced DatabaseManager with corrected start button functionality
import sqlite3
import hashlib
import os
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
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS user_stores (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            store_id INTEGER NOT NULL,
                            is_primary BOOLEAN DEFAULT 0,
                            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
                            UNIQUE(user_id, store_id)
                        )
                           """)
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
                    raw_cost REAL DEFAULT 0,
                    actual_cost REAL DEFAULT 0,
                    status TEXT DEFAULT 'New',
                    store_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    started_at TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE SET NULL
                )
            ''')

            # === JOB_NOTES TABLE (Added for better tracking) ===
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS job_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            ''')

            # Add columns if they don't exist (for existing databases)
            columns_to_add = [
                ("raw_cost", "REAL DEFAULT 0"),
                ("started_at", "TIMESTAMP"),
            ]
            
            for column_name, column_def in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_def}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

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
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    FOREIGN KEY (technician_id) REFERENCES users(id),
                    FOREIGN KEY (assigned_by) REFERENCES users(id)
                )
            ''')

            # Add columns to technician_assignments if they don't exist
            assignment_columns = [
                ("started_at", "TIMESTAMP"),
                ("completed_at", "TIMESTAMP")
            ]
            
            for column_name, column_def in assignment_columns:
                try:
                    cursor.execute(f"ALTER TABLE technician_assignments ADD COLUMN {column_name} {column_def}")
                except sqlite3.OperationalError:
                    pass

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
                self._insert_default_data(cursor)

            conn.commit()

    def _insert_default_data(self, cursor):
        """Insert default data for new installations"""
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

        # Store-technician assignments
        store_technicians = [
            (1, 5), (1, 6), (2, 7), (2, 8), (3, 9), (3, 10),
            (1, 7), (2, 6)  # multi-store assignments
        ]
        cursor.executemany("INSERT INTO store_technicians (store_id, technician_id) VALUES (?, ?)", store_technicians)

        # Sample customers
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

    def handle_start_button_click(self, job_id, raw_cost=None, actual_cost=None):
        """
        Handle start button click - transitions status from New to In Progress or In Progress to Completed
        Updates costs if provided and manages timestamps in both jobs and technician_assignments tables
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Get current job status
                cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
                result = cursor.fetchone()
                
                if not result:
                    return {"success": False, "message": "Job not found"}
                
                current_status = result[0]
                
                if current_status == "New":
                    # Transition from New to In Progress
                    new_status = "In Progress"
                    
                    # Build the update query dynamically based on provided parameters
                    update_fields = ["status = ?", "started_at = CURRENT_TIMESTAMP", "updated_at = CURRENT_TIMESTAMP"]
                    params = [new_status]
                    
                    if raw_cost is not None:
                        update_fields.append("raw_cost = ?")
                        params.append(raw_cost)
                    
                    if actual_cost is not None:
                        update_fields.append("actual_cost = ?")
                        params.append(actual_cost)
                    
                    params.append(job_id)  # for WHERE clause
                    
                    cursor.execute(f'''
                        UPDATE jobs 
                        SET {", ".join(update_fields)}
                        WHERE id = ?
                    ''', params)
                    
                    # Update technician_assignments table
                    cursor.execute('''
                        UPDATE technician_assignments 
                        SET started_at = CURRENT_TIMESTAMP, status = 'in_progress'
                        WHERE id IN (
                            SELECT ta.id FROM technician_assignments ta
                            JOIN assignment_jobs aj ON ta.id = aj.assignment_id
                            WHERE aj.job_id = ? AND ta.status = 'active'
                        )
                    ''', (job_id,))
                    
                    conn.commit()
                    return {"success": True, "message": f"Job started successfully. Status changed to {new_status}", "new_status": new_status}
                
                elif current_status == "In Progress":
                    # Transition from In Progress to Completed
                    new_status = "Completed"
                    
                    # Build the update query dynamically
                    update_fields = ["status = ?", "completed_at = CURRENT_TIMESTAMP", "updated_at = CURRENT_TIMESTAMP"]
                    params = [new_status]
                    
                    if raw_cost is not None:
                        update_fields.append("raw_cost = ?")
                        params.append(raw_cost)
                    
                    if actual_cost is not None:
                        update_fields.append("actual_cost = ?")
                        params.append(actual_cost)
                    
                    params.append(job_id)  # for WHERE clause
                    
                    cursor.execute(f'''
                        UPDATE jobs 
                        SET {", ".join(update_fields)}
                        WHERE id = ?
                    ''', params)
                    
                    # Update technician_assignments table
                    cursor.execute('''
                        UPDATE technician_assignments 
                        SET completed_at = CURRENT_TIMESTAMP, status = 'completed'
                        WHERE id IN (
                            SELECT ta.id FROM technician_assignments ta
                            JOIN assignment_jobs aj ON ta.id = aj.assignment_id
                            WHERE aj.job_id = ? AND ta.status = 'in_progress'
                        )
                    ''', (job_id,))
                    
                    conn.commit()
                    return {"success": True, "message": f"Job completed successfully. Status changed to {new_status}", "new_status": new_status}
                
                else:
                    return {"success": False, "message": f"Cannot start job with status '{current_status}'. Job must be 'New' or 'In Progress'"}
                    
            except sqlite3.Error as e:
                conn.rollback()
                return {"success": False, "message": f"Database error: {str(e)}"}

    def update_job_status_and_cost(self, job_id, new_status, actual_cost=None, raw_cost=None):
        """Update job status and costs (enhanced legacy method)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Build dynamic update query
                update_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
                params = [new_status]
                
                if actual_cost is not None:
                    update_fields.append("actual_cost = ?")
                    params.append(actual_cost)
                
                if raw_cost is not None:
                    update_fields.append("raw_cost = ?")
                    params.append(raw_cost)
                
                # Set completed_at if status is Completed
                if new_status == 'Completed':
                    update_fields.append("completed_at = CURRENT_TIMESTAMP")
                
                # Set started_at if status is In Progress and not already set
                if new_status == 'In Progress':
                    update_fields.append("started_at = COALESCE(started_at, CURRENT_TIMESTAMP)")
                
                params.append(job_id)  # for WHERE clause
                
                cursor.execute(f'''
                    UPDATE jobs 
                    SET {", ".join(update_fields)}
                    WHERE id = ?
                ''', params)
                
                # Update technician assignments
                if new_status == 'Completed':
                    cursor.execute('''
                        UPDATE technician_assignments 
                        SET completed_at = CURRENT_TIMESTAMP, status = 'completed'
                        WHERE id IN (
                            SELECT ta.id FROM technician_assignments ta
                            JOIN assignment_jobs aj ON ta.id = aj.assignment_id
                            WHERE aj.job_id = ?
                        )
                    ''', (job_id,))
                elif new_status == 'In Progress':
                    cursor.execute('''
                        UPDATE technician_assignments 
                        SET started_at = COALESCE(started_at, CURRENT_TIMESTAMP), status = 'in_progress'
                        WHERE id IN (
                            SELECT ta.id FROM technician_assignments ta
                            JOIN assignment_jobs aj ON ta.id = aj.assignment_id
                            WHERE aj.job_id = ?
                        )
                    ''', (job_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
            except sqlite3.Error as e:
                conn.rollback()
                raise e

    def get_job_details(self, job_id):
        """Get complete job details including customer info"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
            SELECT 
                j.id,
                j.created_at,
                j.updated_at,
                j.completed_at,
                j.started_at,
                j.device_type,
                j.device_model,
                j.device_password_type,
                j.device_password,
                j.notification_methods,
                j.problem_description,
                j.status,
                j.estimated_cost,
                j.raw_cost,
                j.actual_cost,
                c.name AS customer_name,
                c.phone AS customer_phone,
                c.email AS customer_email,
                c.address AS customer_address,
                s.name AS store_name,
                s.location AS store_location,
                u.full_name AS technician_name,
                ta.status AS assignment_status,
                ta.started_at AS assignment_started_at,
                ta.completed_at AS assignment_completed_at
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            LEFT JOIN stores s ON j.store_id = s.id
            LEFT JOIN assignment_jobs aj ON aj.job_id = j.id
            LEFT JOIN technician_assignments ta ON ta.id = aj.assignment_id
            LEFT JOIN users u ON u.id = ta.technician_id
            WHERE j.id = ?
            '''
            
            cursor.execute(query, (job_id,))
            return cursor.fetchone()

    def get_job_current_status(self, job_id):
        """Get current status of a job"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_start_button_text(self, job_id):
        """Get appropriate text for start button based on current status"""
        status = self.get_job_current_status(job_id)
        if status == "New":
            return "Start Job"
        elif status == "In Progress":
            return "Complete Job"
        else:
            return "Job Completed"

    def can_start_job(self, job_id):
        """Check if job can be started (status is New or In Progress)"""
        status = self.get_job_current_status(job_id)
        return status in ["New", "In Progress"]

    def insert_job_photos(self, job_id, image_paths):
        """Insert job photos with duplicate prevention"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for image_path in image_paths:
                if not os.path.exists(image_path):
                    continue
                    
                try:
                    with open(image_path, 'rb') as f:
                        photo_blob = f.read()

                    photo_hash = hashlib.sha256(photo_blob).hexdigest()

                    # Check for duplicates
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
                except (IOError, OSError) as e:
                    print(f"Error reading image {image_path}: {e}")
                    continue

            conn.commit()

    def get_photos_for_job(self, job_id):
        """Extract photos for a job to files"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id, photo FROM job_photos WHERE job_id = ?", (job_id,))
            photos = cursor.fetchall()

            photo_files = []
            for photo_id, blob in photos:
                filename = f"job_{job_id}_photo_{photo_id}.jpg"
                try:
                    with open(filename, "wb") as f:
                        f.write(blob)
                    photo_files.append(filename)
                except (IOError, OSError) as e:
                    print(f"Error writing photo {filename}: {e}")
                    
            return photo_files

    def add_job_note(self, job_id, note):
        """Add a note to a job"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO job_notes (job_id, note, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (job_id, note))
            conn.commit()
            return cursor.lastrowid

    def get_job_notes(self, job_id):
        """Get all notes for a job"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note, created_at
                FROM job_notes
                WHERE job_id = ?
                ORDER BY created_at DESC
            ''', (job_id,))
            return cursor.fetchall()


