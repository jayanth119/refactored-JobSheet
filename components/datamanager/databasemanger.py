import sqlite3
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import time
import sys
import os  
class DatabaseManager:
    def __init__(self, db_path="repairpro.db"):
        
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create stores table
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
        
        # Create users table with store association
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'staff',
                store_id INTEGER,
                full_name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES stores (id)
            )
        ''')
        
        # Create customers table with store association
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                address TEXT,
                store_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (store_id) REFERENCES stores (id)
            )
        ''')
        
        # Create jobs table with store association
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                device_model TEXT,
                problem_description TEXT NOT NULL,
                estimated_cost REAL DEFAULT 0,
                actual_cost REAL DEFAULT 0,
                status TEXT DEFAULT 'New',
                technician TEXT,
                store_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (id),
                FOREIGN KEY (store_id) REFERENCES stores (id)
            )
        ''')
        
        # Insert default data if not exists
        cursor.execute("SELECT COUNT(*) FROM stores")
        if cursor.fetchone()[0] == 0:
            default_stores = [
                ("RepairPro Main", "Downtown Plaza", "555-0101", "main@repairpro.com"),
                ("RepairPro North", "North Mall", "555-0102", "north@repairpro.com")
            ]
            cursor.executemany(
                "INSERT INTO stores (name, location, phone, email) VALUES (?, ?, ?, ?)",
                default_stores
            )
        
        # Insert default admin user if not exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password, role, full_name, email) VALUES (?, ?, ?, ?, ?)",
                ("admin", admin_password, "admin", "System Administrator", "admin@repairpro.com")
            )
            
            # Create sample staff users
            staff_password = hashlib.sha256("staff123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, password, role, store_id, full_name, email) VALUES (?, ?, ?, ?, ?, ?)",
                ("staff1", staff_password, "staff", 1, "John Doe", "john@repairpro.com")
            )
            cursor.execute(
                "INSERT INTO users (username, password, role, store_id, full_name, email) VALUES (?, ?, ?, ?, ?, ?)",
                ("staff2", staff_password, "staff", 2, "Jane Smith", "jane@repairpro.com")
            )
        
        conn.commit()
        conn.close()