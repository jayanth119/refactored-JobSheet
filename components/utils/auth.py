import streamlit as st
import sqlite3
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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.datamanager.databasemanger import DatabaseManager
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def authenticate_user(username, password):
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.username, u.role, u.store_id, u.full_name, u.email, s.name as store_name
        FROM users u
        LEFT JOIN stores s ON u.store_id = s.id
        WHERE u.username = ? AND u.password = ?
    """, (username, hash_password(password)))
    
    user = cursor.fetchone()
    
    if user:
        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user[0],))
        conn.commit()
        
        user_data = {
            "id": user[0],
            "username": user[1],
            "role": user[2],
            "store_id": user[3],
            "full_name": user[4],
            "email": user[5],
            "store_name": user[6] if user[6] else "All Stores"
        }
        conn.close()
        return user_data
    
    conn.close()
    return None

def create_user(username, password, role, store_id, full_name, email):
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role, store_id, full_name, email) VALUES (?, ?, ?, ?, ?, ?)",
            (username, hash_password(password), role, store_id, full_name, email)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False