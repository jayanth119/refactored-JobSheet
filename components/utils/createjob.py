import streamlit as st 
import hashlib 
def create_job_in_database(conn, db, user, job_data, uploaded_photos):
    """Create job in database using only schema-compatible fields with proper photo handling"""
    try:
        cursor = conn.cursor()
        store_id = user.get('store_id')
        
        # Check if customers table has address column
        cursor.execute("PRAGMA table_info(customers)")
        customer_columns = [col[1] for col in cursor.fetchall()]
        has_customer_address = 'address' in customer_columns
        
        # Handle customer creation/update
        if job_data['existing_customer_id']:
            customer_id = job_data['existing_customer_id']
            # Update existing customer
            if has_customer_address:
                cursor.execute('''
                    UPDATE customers SET 
                        name = ?, email = ?, address = ?
                    WHERE id = ?
                ''', (
                    job_data['customer_name'],
                    job_data['customer_email'],
                    job_data['customer_address'],
                    customer_id
                ))
            else:
                cursor.execute('''
                    UPDATE customers SET 
                        name = ?, email = ?
                    WHERE id = ?
                ''', (
                    job_data['customer_name'],
                    job_data['customer_email'],
                    customer_id
                ))
        else:
            # Create new customer
            if has_customer_address:
                cursor.execute('''
                    INSERT INTO customers (name, phone, email, address, store_id, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    job_data['customer_name'],
                    job_data['customer_phone'],
                    job_data['customer_email'],
                    job_data['customer_address'],
                    store_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO customers (name, phone, email, store_id, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    job_data['customer_name'],
                    job_data['customer_phone'],
                    job_data['customer_email'],
                    store_id
                ))
            customer_id = cursor.lastrowid
        
        # Create job using only schema-compatible fields
        cursor.execute('''
            INSERT INTO jobs (
                customer_id, store_id, device_type, device_model,
                device_password_type, device_password,
                problem_description, estimated_cost, actual_cost,
                notification_methods, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            customer_id, store_id, job_data['device_type'], job_data['device_model'],
            job_data['device_password_type'], job_data['device_password'],
            job_data['problem_description'], job_data['estimated_cost'], 
            job_data['actual_cost'], ','.join(job_data['notification_methods'])
        ))
        
        job_id = cursor.lastrowid
        
        # Assign technician if selected
        if job_data['technician_id']:
            cursor.execute('''
                INSERT INTO technician_assignments 
                (technician_id, assigned_by, status, notes, assigned_at)
                VALUES (?, ?, 'active', 'Initial assignment', CURRENT_TIMESTAMP)
            ''', (job_data['technician_id'], user['id']))
            assignment_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO assignment_jobs (assignment_id, job_id)
                VALUES (?, ?)
            ''', (assignment_id, job_id))
        
        # Commit the main transaction first
        conn.commit()
        
        # Handle photo uploads AFTER committing the job
        if uploaded_photos and len(uploaded_photos) > 0:
            try:
                st.info(f"📸 Processing {len(uploaded_photos)} photos...")
                
                # Create a new cursor for photo operations
                photo_cursor = conn.cursor()
                
                for i, photo in enumerate(uploaded_photos):
                    try:
                        # Read the photo data directly from the uploaded file
                        photo_data = photo.getvalue()
                        
                        # Validate photo data
                        if len(photo_data) == 0:
                            st.warning(f"⚠️ Photo {photo.name} is empty, skipping...")
                            continue
                        
                        # Check for duplicates using hash
                        photo_hash = hashlib.sha256(photo_data).hexdigest()
                        
                        photo_cursor.execute('''
                            SELECT COUNT(*) FROM job_photos 
                            WHERE job_id = ? AND hex(photo) = ?
                        ''', (job_id, photo_hash.upper()))
                        
                        if photo_cursor.fetchone()[0] > 0:
                            st.info(f"📸 Photo {photo.name} already exists, skipping duplicate...")
                            continue
                        
                        # Insert photo into database
                        photo_cursor.execute('''
                            INSERT INTO job_photos (job_id, photo, uploaded_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        ''', (job_id, photo_data))
                        
                        st.success(f"✅ Photo {i+1}/{len(uploaded_photos)} saved: {photo.name}")
                        
                    except Exception as photo_error:
                        st.error(f"❌ Error saving photo {photo.name}: {str(photo_error)}")
                        continue
                
                # Commit photo transactions
                conn.commit()
                
                # Verify photos were saved
                photo_cursor.execute("SELECT COUNT(*) FROM job_photos WHERE job_id = ?", (job_id,))
                photo_count = photo_cursor.fetchone()[0]
                
                if photo_count > 0:
                    st.success(f"✅ Successfully saved {photo_count} photos for Job #{job_id}")
                else:
                    st.warning("⚠️ No photos were saved")
                    
            except Exception as photo_error:
                st.error(f"❌ Error processing photos: {str(photo_error)}")
                # Don't fail the entire job creation if photos fail
                pass
        
        return True, job_id
        
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Error creating job: {str(e)}")
        return False, None