import mysql.connector  # Changed from sqlite3
import os
from datetime import datetime, timedelta
from tkinter import messagebox

import bcrypt

# No more BASE_DIR, DATA_DIR, DB_FILE since it's remote MySQL

class DatabaseManager:
    """
    Manages all interactions with the MySQL database for the Real Estate Management System.
    """
    def __init__(self, host='localhost', user='root', password='', database='real_estate'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self._create_tables()  # No _create_data_directory needed

    def _create_tables(self):
        """Initializes the database by creating tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 7. Users Table (Moved to top, as it's referenced by others)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INT PRIMARY KEY AUTO_INCREMENT,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        password_hash VARCHAR(255) NOT NULL,
                        is_agent VARCHAR(255) DEFAULT 'no',  # Removed CHECK
                        role VARCHAR(255) DEFAULT 'user'  # Removed CHECK
                    )
                ''')

                # 1. Properties Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS properties (
                        property_id INT PRIMARY KEY AUTO_INCREMENT,
                        property_type VARCHAR(255) NOT NULL,  # Removed CHECK (handle in code if needed)
                        title_deed_number VARCHAR(255) NOT NULL,
                        location VARCHAR(255) NOT NULL,
                        size DOUBLE NOT NULL,
                        description TEXT,
                        owner VARCHAR(255) NOT NULL,
                        contact VARCHAR(255) NOT NULL, -- New column for contact info
                        price DOUBLE NOT NULL,
                        image_paths TEXT,      -- Stores comma-separated paths
                        title_image_paths TEXT, -- Stores comma-separated paths
                        status VARCHAR(255) NOT NULL DEFAULT 'Available',  # Removed CHECK
                        added_by_user_id INT, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')
                               
                # 2. PropertiesForTransfer Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS propertiesForTransfer (
                        property_id INT PRIMARY KEY AUTO_INCREMENT,
                        title_deed_number VARCHAR(255) NOT NULL,
                        location VARCHAR(255) NOT NULL,
                        size DOUBLE NOT NULL,
                        description TEXT,
                        owner VARCHAR(255) NOT NULL,
                        contact VARCHAR(255) NOT NULL, -- New column for contact info
                        image_paths TEXT,      -- Stores comma-separated paths
                        title_image_paths TEXT, -- Stores comma-separated paths
                        added_by_user_id INT, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 3. Clients Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(255) NOT NULL,
                        contact_info VARCHAR(255) UNIQUE NOT NULL, -- Can be phone, email, etc.
                        status VARCHAR(255) NOT NULL DEFAULT 'active',  # Removed CHECK
                        added_by_user_id INT, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 4. Transactions Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INT PRIMARY KEY AUTO_INCREMENT,
                        property_id INT NOT NULL,
                        client_id INT NOT NULL,
                        payment_mode VARCHAR(255) NOT NULL, -- 'Cash', 'Installments'
                        total_amount_paid DOUBLE NOT NULL, -- Total amount paid in this transaction
                        discount DOUBLE DEFAULT 0.0,
                        balance DOUBLE DEFAULT 0.0, -- Remaining balance if 'Installments'
                        transaction_date VARCHAR(255) NOT NULL, --YYYY-MM-DD HH:MM:SS
                        receipt_path TEXT,
                        added_by_user_id INT, -- New column
                        FOREIGN KEY (property_id) REFERENCES properties(property_id),
                        FOREIGN KEY (client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS proposed_lots (
                        lot_id INT PRIMARY KEY AUTO_INCREMENT,
                        parent_block_id INT NOT NULL,
                        size DOUBLE NOT NULL,
                        location VARCHAR(255) NOT NULL,
                        surveyor_name VARCHAR(255) NOT NULL,
                        created_by VARCHAR(255) NOT NULL,
                        title_deed_number VARCHAR(255),
                        price VARCHAR(255) DEFAULT '0.0',
                        status VARCHAR(255) NOT NULL,  # Removed CHECK
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 6. Property transfer Table 
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS property_transfers (
                        transfer_id INT PRIMARY KEY AUTO_INCREMENT,
                        property_id INT NOT NULL,
                        from_client_id INT,
                        to_client_id INT NOT NULL,
                        transfer_price DOUBLE NOT NULL,
                        transfer_date VARCHAR(255) NOT NULL, -- YYYY-MM-DD
                        executed_by_user_id INT NOT NULL,
                        supervising_agent_id INT,
                        transfer_document_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (property_id) REFERENCES properties(property_id),
                        FOREIGN KEY (from_client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (to_client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (executed_by_user_id) REFERENCES users(user_id),
                        FOREIGN KEY (supervising_agent_id) REFERENCES users(user_id)
                    )
                ''')

                # 8. Agents Table - New table for agents
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS agents (
                         agent_id INT PRIMARY KEY AUTO_INCREMENT,
                         name VARCHAR(255) NOT NULL,
                         status VARCHAR(255) DEFAULT 'active',  # Removed CHECK
                         added_by VARCHAR(255) NOT NULL,
                         timestamp DATETIME NOT NULL
                     )
                ''')
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS payment_plans (
                                      plan_id INT PRIMARY KEY AUTO_INCREMENT,
                                      name VARCHAR(255) NOT NULL,
                                      deposit_percentage DOUBLE NOT NULL,  # Removed CHECK
                                      duration_months INT NOT NULL,
                                      interest_rate DOUBLE NOT NULL,
                                      created_by VARCHAR(255) NOT NULL
                                 )
                                 ''')
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS service_clients (
                                      client_id INT PRIMARY KEY AUTO_INCREMENT,
                                      name VARCHAR(255) NOT NULL,
                                      contact VARCHAR(255) UNIQUE NOT NULL,
                                      brought_by VARCHAR(255),
                                      added_by VARCHAR(255) NOT NULL,
                                      timestamp DATETIME NOT NULL
                                )
                               ''')
                cursor.execute('''
               -- NEW TABLE: Links a specific file (e.g., for a land parcel) to a client.
               -- Each client can have multiple files.
                               CREATE TABLE IF NOT EXISTS client_files (
                                      file_id INT PRIMARY KEY AUTO_INCREMENT,
                                      client_id INT NOT NULL,
                                      file_name VARCHAR(255) NOT NULL,
                                      added_by VARCHAR(255) NOT NULL,
                                      timestamp DATETIME NOT NULL,
                                      FOREIGN KEY (client_id) REFERENCES service_clients(client_id)
                             )
                            ''')
                cursor.execute('''
               -- The jobs table now links to a specific file (file_id) instead of the
               -- general client (client_id). This ensures each job is tied to the
               -- correct land project.
                              CREATE TABLE IF NOT EXISTS service_jobs (
                                     job_id INT PRIMARY KEY AUTO_INCREMENT,
                                     file_id INT NOT NULL,
                                     job_description TEXT,
                                     title_name VARCHAR(255) NOT NULL,
                                     title_number VARCHAR(255) NOT NULL,
                                     fee DOUBLE NOT NULL,
                                     amount_paid DOUBLE DEFAULT 0.0,
                                     status VARCHAR(255) NOT NULL DEFAULT 'Ongoing',  # Removed CHECK
                                     added_by VARCHAR(255) NOT NULL,
                                     brought_by VARCHAR(255) NOT NULL,
                                     timestamp DATETIME NOT NULL,
                                     FOREIGN KEY (file_id) REFERENCES client_files(file_id)
                                )
                          ''')
                cursor.execute('''
               -- The payments table correctly links to the job_id, which is now
               -- linked to a specific file.
                              CREATE TABLE IF NOT EXISTS service_payments (
                                     payment_id INT PRIMARY KEY AUTO_INCREMENT,
                                     job_id INT NOT NULL,
                                     amount DOUBLE NOT NULL,
                                     payment_date VARCHAR(255) NOT NULL,
                                     payment_type VARCHAR(255),  # Removed CHECK
                                     status VARCHAR(255) DEFAULT 'unpaid',  # Removed CHECK
                                     FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
               )
            ''')
                cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_dispatch (
                dispatch_id INT PRIMARY KEY AUTO_INCREMENT,
                job_id INT NOT NULL,
                dispatch_date VARCHAR(255) NOT NULL,
                reason_for_dispatch TEXT,
                collected_by VARCHAR(255),
                collector_phone VARCHAR(255),
                sign BLOB, -- Stores the digital signature file.
                          -- Note: For large files, it's often better to store a path/URL
                          -- to a file storage system instead of storing the BLOB directly.
                FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
            )
        ''')


                conn.commit()
            print("Database initialized successfully.")
        except mysql.connector.Error as e:
            print(f"Error creating tables: {e}")

    def _get_connection(self):
        """
        Returns a connection object to the MySQL database.
        """
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def _execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        """
        A helper method to execute SQL queries.
        Returns dicts for SELECT queries.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)  # Returns results as dicts (like sqlite3.Row)
            cursor.execute(query, params)
            conn.commit()  # Explicit commit for DML

            if fetch_one:
                return cursor.fetchone()  # Returns dict or None
            if fetch_all:
                return cursor.fetchall()  # Returns list of dicts or empty list
            
            # For INSERT, return the last row ID
            if query.strip().upper().startswith("INSERT"):
                return cursor.lastrowid
            
            # For UPDATE/DELETE, check if any rows were affected
            if query.strip().upper().startswith(("UPDATE", "DELETE")):
                return cursor.rowcount > 0
            
            return None
        except mysql.connector.IntegrityError as e:
            print(f"Database Integrity Error: {e}. This usually means a unique value constraint was violated.")
            return None
        except mysql.connector.Error as e:
            print(f"Database error: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in _execute_query: {e}")
            return None
        finally:
            if conn:
                conn.close()  # Always close the connection

    ## User Management Methods
    def add_user(self, username, password, is_agent='no',role='user'):
        """
        Adds a new user to the database with a hashed password.
        Returns: The ID of the newly added user, or None on error (e.g., duplicate username).
        """
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            query = "INSERT INTO users (username, password_hash, is_agent,role) VALUES (%s, %s, %s, %s)"
            return self._execute_query(query, (username, hashed_password, is_agent,role))
        except Exception as e:
            print(f"Error adding user: {e}")
            return None

    def authenticate_user(self, username, password):
        """
        Verifies user credentials for login.
        Returns: The user's data (user_id, username, role) as a dict if valid, None otherwise.
        """
        query = "SELECT user_id, username, password_hash, role FROM users WHERE username = %s"
        user_data_row = self._execute_query(query, (username,), fetch_one=True)

        if user_data_row:
            user_data = user_data_row  # Already dict
            stored_password_hash = user_data['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash):
                del user_data['password_hash']
                return user_data
        return None

    def get_user_by_username(self, username):
        """
        Retrieves user data by username without password authentication.
        Returns: The user's data (user_id, username, role) as a dict if found, None otherwise.
        """
        query = "SELECT user_id, username, role FROM users WHERE username = %s"
        user_data_row = self._execute_query(query, (username,), fetch_one=True)
        return user_data_row if user_data_row else None

    def get_user_by_id(self, user_id):
        """
        Retrieves a user by their ID.
        Returns: The user's data (excluding password_hash) as a dict, or None if not found.
        """
        query = "SELECT user_id, username, role FROM users WHERE user_id = %s"
        user_data_row = self._execute_query(query, (user_id,), fetch_one=True)
        return user_data_row if user_data_row else None

    def update_user_password(self, user_id, new_password):
        """
        Updates a user's password.
        Returns: True if the update was successful, False otherwise.
        """
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE users SET password_hash = %s WHERE user_id = %s"
        return self._execute_query(query, (hashed_password, user_id))

    def update_user_role(self, user_id, new_role):
        """
        Updates a user's role.
        Returns: True if the update was successful, False otherwise.
        """
        if new_role not in ['user', 'admin']:
            print("Invalid role specified. Role must be 'user' or 'admin'.")
            return False
        query = "UPDATE users SET role = %s WHERE user_id = %s"
        return self._execute_query(query, (new_role, user_id))

    # --- NEW METHODS FOR USER MANAGEMENT (ADD THESE) ---
    def get_all_users(self):
        """Retrieves all user records from the database."""
        try:
            rows = self._execute_query("SELECT user_id, username, role FROM users", fetch_all=True)
            return rows if rows else []  # Already list of dicts
        except Exception as e:
            print(f"Error fetching all users: {e}")
            return []

    def update_user(self, user_id, new_username=None, new_password=None, new_role=None):
        """Updates an existing user's details."""
        try:
            query_parts = []
            params = []
            if new_username:
                query_parts.append("username = %s")
                params.append(new_username)
            if new_password:
                query_parts.append("password_hash = %s")
                params.append(bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))  # Assuming _hash_password is bcrypt
            if new_role:
                query_parts.append("role = %s")
                params.append(new_role)

            if not query_parts:
                return False  # Nothing to update

            query = "UPDATE users SET " + ", ".join(query_parts) + " WHERE user_id = %s"
            params.append(user_id)

            row_count = self._execute_query(query, tuple(params))
            return row_count is not None and row_count > 0
        except mysql.connector.IntegrityError:
            messagebox.showerror("Error", f"Username '{new_username}' already exists.")
            return False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id):
        """Deletes a user from the database."""
        try:
            row_count = self._execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))
            return row_count is not None and row_count > 0
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def get_username_by_id(self, user_id):
        """
        Fetches the username of a user based on their user ID.

        Args:
            user_id (str): The ID of the user to look up.

        Returns:
            str: The username if found, otherwise None.
        """
        try:
            row = self._execute_query(
                "SELECT username FROM users WHERE user_id = %s",
                (user_id,),
                fetch_one=True
            )
            return row['username'] if row else None
        except Exception as e:
            print(f"Error fetching username for user ID '{user_id}': {e}")
            return None


    ## CRUD Operations for Properties

    def get_properties_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM properties WHERE title_deed_number = %s;"
        results_rows = self._execute_query(query, (title_deed_number,), fetch_all=True)
        return results_rows if results_rows else []

    def add_property(self, property_type, title_deed_number, location, size, description, owner, contact, price, image_paths=None, title_image_paths=None, status='Available', added_by_user_id=None):
        """
        Adds a new property to the database and ensures the owner is in the clients table.
        """
        existing_properties = self.get_properties_by_title_deed(title_deed_number)
        client_status = 'active'

        for prop in existing_properties:
            if prop['status'].lower() == 'available':
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        # --- Logic to add owner to clients table ---
        # Step 1: Check if the client already exists using their contact info (since it's unique).
        client_exists = self.get_client_by_contact_info(contact)
        
        # Step 2: If the client doesn't exist, insert them.
        if not client_exists:
            self.add_client(name=owner, contact_info=contact, status=client_status, added_by_user_id=added_by_user_id)

        # Step 3: Insert the property.
        query = '''INSERT INTO properties (property_type,title_deed_number, location, size, description, owner, contact, price, image_paths, title_image_paths, status, added_by_user_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        return self._execute_query(query, (property_type,title_deed_number, location, size, description, owner, contact, price, image_paths, title_image_paths, status, added_by_user_id))


    def get_propertiesfortransfer_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM propertiesForTransfer WHERE title_deed_number = %s;"
        results_rows = self._execute_query(query, (title_deed_number,), fetch_all=True)
        return results_rows if results_rows else []


    def add_propertyForTransfer(self, title_deed_number, location, size, description, owner, contact,  image_paths=None, title_image_paths=None, added_by_user_id=None):
        """
        Adds a new property to the database and ensures the owner is in the clients table.
        """
        existing_properties = self.get_propertiesfortransfer_by_title_deed(title_deed_number)
        client_status = 'active'

        for prop in existing_properties:
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None


        # --- Logic to add owner to clients table ---
        # Step 1: Check if the client already exists using their contact info (since it's unique).
        client_exists = self.get_client_by_contact_info(contact)
        
        # Step 2: If the client doesn't exist, insert them.
        if not client_exists:
            self.add_client(name=owner, contact_info=contact, status=client_status, added_by_user_id=added_by_user_id)

        # Step 3: Insert the property.
        query = '''INSERT INTO propertiesForTransfer (title_deed_number, location, size, description, owner, contact, image_paths, title_image_paths,  added_by_user_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        return self._execute_query(query, (title_deed_number, location, size, description, owner, contact,  image_paths, title_image_paths, added_by_user_id))
        

    def get_property(self, property_id):
        """
        Retrieves a property by its ID.
        Returns: The property details as a dict, or None if not found.
        """
        query = "SELECT * FROM properties WHERE property_id = %s"
        property_data_row = self._execute_query(query, (property_id,), fetch_one=True)
        return property_data_row if property_data_row else None

    def get_all_properties(self, status=None):
        """
        Retrieves all properties, optionally filtered by status.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = %s"
            params = (status,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return results_rows if results_rows else []
    
    def get_all_properties_lots(self, status=None,property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = %s"
            params = (status,)
        if property_type:
            query += " AND property_type = %s"
            params += (property_type,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return results_rows if results_rows else []
    
    def get_all_properties_blocks(self, status=None,property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = %s"
            params = (status,)
        if property_type:
            query += " AND property_type = %s"
            params += (property_type,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return results_rows if results_rows else []

    def update_property(self, property_id, **kwargs):
        """
        Updates details of an existing property.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in ['title_deed_number', 'location', 'size', 'description', 'price', 'image_paths', 'title_image_paths', 'status']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for property update.")
            return False

        params.append(property_id)
        query = f"UPDATE properties SET {', '.join(set_clauses)} WHERE property_id = %s"
        return self._execute_query(query, params)

    def delete_property(self, property_id):
        """
        Deletes a property from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "DELETE FROM properties WHERE property_id = %s"
        return self._execute_query(query, (property_id,))
    
    def get_total_properties(self):
        """
        Returns the total count of properties.
        Returns: Total number of properties.
        """
        query = "SELECT COUNT(*) FROM properties"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row['COUNT(*)'] if result_row else 0

    def get_all_properties_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        """
        Fetches properties with optional search, size filters, status, and pagination,
        including the username of the user who added the property.
        Returns properties ordered by property_id DESC (newest first).
        
        Returns: A list of dictionaries, each representing a property, including 'added_by_username'.
        """
        query = """
        SELECT
            p.property_id,
            p.property_type,
            p.title_deed_number,
            p.location,
            p.size,
            p.description,
            p.price,
            p.contact,
            p.image_paths,
            p.title_image_paths,
            p.status,
            p.added_by_user_id,
            p.owner,
            u.username AS added_by_username
        FROM
            properties p
        LEFT JOIN
            users u ON p.added_by_user_id = u.user_id
        WHERE 1=1
        """
        params = []

        if search_query:
            query += " AND (p.title_deed_number LIKE %s OR p.location LIKE %s OR p.description LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

        if min_size is not None:
            query += " AND size >= %s"
            params.append(min_size)

        if max_size is not None:
            query += " AND size <= %s"
            params.append(max_size)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY p.property_id DESC"

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)

        return self._execute_query(query, tuple(params), fetch_all=True)

    def get_total_sales_for_date_range(self, start_date, end_date):
        """
        Retrieves the total revenue and number of properties sold within a specified date range.
        """
        try:
            query = """
                SELECT 
                    SUM(t.total_amount_paid) AS total_revenue,
                    COUNT(DISTINCT t.property_id) AS total_properties_sold
                FROM 
                    transactions t
                WHERE 
                    t.transaction_date BETWEEN %s AND CONCAT(%s, ' 23:59:59')
            """
            result_row = self._execute_query(query, (start_date, end_date), fetch_one=True)
            
            return {
                'total_revenue': result_row['total_revenue'] if result_row and result_row['total_revenue'] is not None else 0.0,
                'total_properties_sold': result_row['total_properties_sold'] if result_row and result_row['total_properties_sold'] is not None else 0
            }
        except Exception as e:
            print(f"Error in get_total_sales_for_date_range: {e}")
            return {'total_revenue': 0.0, 'total_properties_sold': 0}

    def get_detailed_sales_transactions_for_date_range(self, start_date, end_date):
        """
        Retrieves detailed sales transactions for the accounting-style report.
        Includes property type (hardcoded to 'Land' for now), title deed, original price,
        amount paid, and balance.
        """
        try:
            query = """
                SELECT 
                    p.title_deed_number AS title_deed,
                    p.price AS actual_price,
                    t.total_amount_paid AS amount_paid,
                    t.balance AS balance
                FROM 
                    transactions t
                JOIN 
                    properties p ON t.property_id = p.property_id
                WHERE 
                    t.transaction_date BETWEEN %s AND CONCAT(%s, ' 23:59:59')
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [{**row, 'property_type': 'Land'} for row in results_rows] if results_rows else []
        except Exception as e:
            print(f"Error in get_detailed_sales_transactions_for_date_range: {e}")
            return []

    def get_sold_properties_for_date_range_detailed(self, start_date, end_date):
        """
        Retrieves detailed information about properties sold within a specified date range.
        """
        try:
            query = """
                SELECT 
                    p.title_deed_number, 
                    p.location, 
                    p.size, 
                    t.transaction_date AS date_sold,
                    t.total_amount_paid,
                    t.balance,
                    c.name AS client_name
                FROM 
                    transactions t
                JOIN 
                    properties p ON t.property_id = p.property_id
                JOIN 
                    clients c ON t.client_id = c.client_id
                WHERE 
                    p.status = 'Sold' AND t.transaction_date BETWEEN %s AND CONCAT(%s, ' 23:59:59')
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return results_rows if results_rows else []
        except Exception as e:
            print(f"Error in get_sold_properties_for_date_range_detailed: {e}")
            return []

    def get_pending_instalments_for_date_range(self, start_date, end_date):
        """
        Retrieves information about transactions with a balance due within a specified date range.
        The date range applies to the transaction_date.
        """
        try:
            query = """
                SELECT 
                    t.transaction_id,
                    t.transaction_date,
                    t.total_amount_paid,
                    t.discount,
                    t.balance,
                    p.title_deed_number,
                    p.price AS original_price,
                    c.name AS client_name,
                    c.contact_info AS client_contact_info
                FROM 
                    transactions t
                JOIN 
                    properties p ON t.property_id = p.property_id
                JOIN 
                    clients c ON t.client_id = c.client_id
                WHERE 
                    t.balance > 0 AND t.transaction_date BETWEEN %s AND CONCAT(%s, ' 23:59:59')
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return results_rows if results_rows else []
        except Exception as e:
            print(f"Error in get_pending_instalments_for_date_range: {e}")
            return []
    
    def get_all_agents(self):
        """Fetches all agent records from the 'agents' table as a list of dictionaries."""
        try:
            rows = self._execute_query(
                "SELECT agent_id, name, status, added_by, timestamp FROM agents",
                fetch_all=True
            )
            return rows if rows else []
        except Exception as e:
            print(f"Error fetching all agents: {e}")
            return []
    
    def add_agent(self, name, added_by):
        """
        Adds a new agent to the database.

        Args:
            name (str): The name of the new agent.
            added_by (str): The username or ID of the user who added the agent.

        Returns:
            bool: True if the agent was added successfully, False otherwise.
        """
        try:
            # Check if an agent with the same name already exists
            existing_agent = self._execute_query(
                "SELECT agent_id FROM agents WHERE name = %s",
                (name,),
                fetch_one=True
            )
            if existing_agent:
                print("Agent with this name already exists.")
                return False

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return self._execute_query(
                "INSERT INTO agents (name, status, added_by, timestamp) VALUES (%s, %s, %s, %s)",
                (name, 'active', added_by, timestamp)
            )
        except Exception as e:
            print(f"Error adding new agent: {e}")
            return False
        
    def get_agent_by_name(self, agent_name):
        """
        Fetches a single agent record from the 'agents' table by name.

        Args:
            agent_name (str): The name of the agent to fetch.

        Returns:
            dict: A dictionary containing the agent's data if found, otherwise None.
        """
        try:
            row = self._execute_query(
                "SELECT agent_id, name, status, added_by, timestamp FROM agents WHERE name = %s",
                (agent_name,),
                fetch_one=True
            )
            return row
        except Exception as e:
            print(f"Error fetching agent by name '{agent_name}': {e}")
            return None


    def update_agent(self, agent_id, new_name=None, new_status=None):
        """
        Updates the name or status of an existing agent.

        Args:
            agent_id (int): The ID of the agent to update.
            new_name (str, optional): The new name for the agent.
            new_status (str, optional): The new status for the agent.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        updates = []
        params = []
        
        if new_name:
            updates.append("name = %s")
            params.append(new_name)
        if new_status:
            updates.append("status = %s")
            params.append(new_status)

        if not updates:
            print("No updates provided.")
            return False

        query = f"UPDATE agents SET {', '.join(updates)} WHERE agent_id = %s"
        params.append(agent_id)

        try:
            return self._execute_query(query, tuple(params))
        except Exception as e:
            print(f"Error updating agent: {e}")
            return False

    def delete_agent(self, agent_id):
        """
        Deletes an agent from the database.

        Args:
            agent_id (int): The ID of the agent to delete.

        Returns:
            bool: True if the agent was deleted, False otherwise.
        """
        try:
            return self._execute_query(
                "DELETE FROM agents WHERE agent_id = %s",
                (agent_id,)
            )
        except Exception as e:
            print(f"Error deleting agent: {e}")
            return False
        
    def check_if_user_is_agent(self, user_id):
        """
        Checks if a user is an agent by looking up their ID in the users table.
        
        Args:
            user_id (int): The ID of the user to check.
            
        Returns:
            bool: True if the user is an agent (is_agent = 'yes'), False otherwise.
        """
        try:
            row = self._execute_query("SELECT is_agent FROM users WHERE user_id = %s", (user_id,), fetch_one=True)
            
            if row and row['is_agent'] == 'yes':
                return True
            return False
            
        except mysql.connector.Error as e:
            print(f"Database error checking if user is an agent: {e}")
            return False
        
    def get_agent_by_user_id(self, user_id):
        """
        Retrieves an agent's data from the users table by their user ID.
        
        Args:
            user_id (int): The ID of the user to retrieve.
            
        Returns:
            dict or None: A dictionary containing the user's data if they are an agent, 
                           otherwise None.
        """
        try:
            row = self._execute_query("SELECT * FROM users WHERE user_id = %s AND is_agent = 'yes'", (user_id,), fetch_one=True)
            return row
            
        except mysql.connector.Error as e:
            print(f"Database error fetching agent data: {e}")
            return None

        
    ############# NEW METHODS FOR PROPOSED LOTS UI ################
        
    def propose_new_lot(self, proposed_lot_data):
        """
        Inserts a new proposed lot record into the proposed_lots table.
        
        Args:
            proposed_lot_data (dict): A dictionary containing the details of the new lot.
        """
        query = '''
            INSERT INTO proposed_lots (parent_block_id, size, location, surveyor_name, created_by, title_deed_number, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = (
            proposed_lot_data['parent_block_id'],
            proposed_lot_data['size'],
            proposed_lot_data['location'],
            proposed_lot_data['surveyor_name'],
            proposed_lot_data['created_by'],
            proposed_lot_data.get('title_deed_number', 'N/A'),
            str(proposed_lot_data.get('price', 0)),
            proposed_lot_data.get('status', 'Proposed')
        )
        return self._execute_query(query, params)

    def create_payment_plan(self, plan_data):
        """
        Inserts a new payment plan record into the payment_plans table.
        
        Args:
            plan_data (dict): A dictionary containing the details of the new plan,
                              including 'name', 'deposit_percentage', 'duration_months', 'interest_rate',
                              and 'created_by'.
        """
        query = """
        INSERT INTO payment_plans (name, deposit_percentage, duration_months, interest_rate, created_by)
        VALUES (%s, %s, %s, %s, %s);
        """
        params = (
            plan_data['name'],
            plan_data['deposit_percentage'],
            plan_data['duration_months'],
            plan_data['interest_rate'],
            plan_data['created_by']
        )
        return self._execute_query(query, params)

    def get_payment_plans(self):
        """
        Retrieves all payment plans from the database.
        
        Returns:
            list: A list of dictionaries, where each dictionary represents a plan.
        """
        query = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans;"
        return self._execute_query(query, fetch_all=True)
    
    def get_plan_by_id(self, plan_id):
        """
        Fetches a single payment plan from the database using its plan_id.
        
        Returns:
            dict: A dictionary of the plan details, or None if not found.
        """
        query = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans WHERE plan_id = %s;"
        return self._execute_query(query, (plan_id,), fetch_one=True)

    def update_payment_plan(self, plan_id, plan_data):
        """
        Updates an existing payment plan using the provided format.
        
        Args:
            plan_id (int): The ID of the plan to update.
            plan_data (dict): A dictionary with the new plan details.
                              Can contain 'name', 'deposit_percentage', 'duration_months', or 'interest_rate'.
        """
        query = '''
            UPDATE payment_plans
            SET name = %s, deposit_percentage = %s, duration_months = %s, interest_rate = %s
            WHERE plan_id = %s
        '''
        params = (
            plan_data.get('name'),
            plan_data.get('deposit_percentage'),
            plan_data.get('duration_months'),
            plan_data.get('interest_rate'),
            plan_id
        )
        return self._execute_query(query, params)

    def delete_payment_plan(self, plan_id):
        """
        Deletes a payment plan based on its ID using the new, simple format.
        
        Args:
            plan_id (int): The ID of the plan to delete.
        """
        query = '''
            DELETE FROM payment_plans WHERE plan_id = %s
        '''
        return self._execute_query(query, (plan_id,))


    def update_block_size(self, block_id, new_size):
        """
        Updates the size of a parent block in the properties table.
        """
        query = '''
            UPDATE properties
            SET size = %s
            WHERE property_id = %s
        '''
        return self._execute_query(query, (new_size, block_id))

    def get_proposed_lots_with_details(self):
        """
        Retrieves all proposed lots with details from both tables.
        """
        query = '''
            SELECT 
                p.title_deed_number,
                pl.lot_id,
                pl.size,
                pl.location,
                pl.surveyor_name,
                pl.created_by,
                pl.status
            FROM proposed_lots pl
            INNER JOIN properties p ON pl.parent_block_id = p.property_id
        '''
        return self._execute_query(query, fetch_all=True)
    
    def get_lots_for_update(self):
        """
        Retrieves proposed or confirmed lots for potential updates.
        """
        query = '''
            SELECT lot_id, title_deed_number, size, status, location
            FROM proposed_lots
            WHERE status IN ('Proposed')
        '''
        return self._execute_query(query, fetch_all=True)

    def get_lot_details_for_rejection(self, lot_id):        
        query = """
        SELECT parent_block_id, size
        FROM proposed_lots
        WHERE lot_id = %s
        """
        row = self._execute_query(query, (lot_id,), fetch_one=True)
        return row if row else None

    def finalize_lot(self, lot_id):
        """
        Updates the status of a proposed lot to 'Confirmed'.
        """
        query = '''
            UPDATE proposed_lots
            SET status = 'Confirmed'
            WHERE lot_id = %s
        '''
        return self._execute_query(query, (lot_id,))

    def reject_lot(self, lot_id):
        """
        Updates the status of a proposed lot to 'Rejected'.
        """
        query = '''
            UPDATE proposed_lots
            SET status = 'Rejected'
            WHERE lot_id = %s
        '''
        return self._execute_query(query, (lot_id,))

    def return_size_to_block(self, block_id, size_to_add):
        """
        Adds a specified size back to a parent block and updates its status if needed.

        Args:
            block_id (int): The ID of the parent block to update.
            size_to_add (float): The size to be added back.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Get current block size and status
            cursor.execute("SELECT size, status FROM properties WHERE property_id = %s", (block_id,))
            result = cursor.fetchone()
            
            if result:
                current_size = result['size']
                current_status = result['status']
                new_size = current_size + size_to_add
                # If the status was unavailable, change it back to available
                new_status = 'Available' if current_status == 'Unavailable' else current_status
                
                # 2. Update the block with the new size and status
                cursor.execute("UPDATE properties SET size = %s, status = %s WHERE property_id = %s", (new_size, new_status, block_id))
                conn.commit()
                print(f"Size {size_to_add} successfully returned to block {block_id}. New size: {new_size}. New status: {new_status}.")
            else:
                print(f"Block with ID {block_id} not found.")

        except mysql.connector.Error as e:
            print(f"Database error occurred: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def update_block_status(self, block_id, status):
        """
        Updates the status of a block in the properties table.
        
        Args:
            block_id (int): The unique ID of the block to update.
            status (str): The new status to be set (e.g., 'Unavailable').
        """
        query = "UPDATE properties SET status = %s WHERE property_id = %s"
        return self._execute_query(query, (status, block_id))

    #NEW
    def get_client_properties(self, client_id):
        """
        Retrieves properties associated with a specific client.
        This assumes properties are linked to clients via transactions.
        """
        query = """
            SELECT p.property_id, p.title_deed_number, p.location, p.size, p.price, p.status,
                   t.transaction_date, t.total_amount_paid
            FROM properties p
            JOIN transactions t ON p.property_id = t.property_id
            WHERE t.client_id = %s
            ORDER BY t.transaction_date DESC
        """
        rows = self._execute_query(query, (client_id,), fetch_all=True)
        return rows if rows else []
    

    def get_client_survey_jobs(self, client_id):
        """
        Retrieves all survey jobs for a specific client.
        """
        query = """
            SELECT job_id, property_location, job_description, fee, amount_paid, balance,
                   deadline, status, created_at
            FROM survey_jobs
            WHERE client_id = %s
            ORDER BY created_at DESC
        """
        rows = self._execute_query(query, (client_id,), fetch_all=True)
        return rows if rows else []
    
    def get_all_propertiesForTransfer_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        """
        Fetches properties from 'properties' and 'propertiesForTransfer' with optional search,
        size filters, status, and pagination, including the username of the user who added them.
        Returns properties ordered by property_id DESC (newest first).
        Returns: A list of dictionaries, each representing a property.
        """
        query_parts = []

        # Query for properties from the 'properties' table
        main_props_query = """
        SELECT
            p.property_id,
            p.title_deed_number,
            p.location,
            p.size,
            p.description,
            p.price,
            p.contact,
            p.image_paths,
            p.title_image_paths,
            p.status,
            p.added_by_user_id,
            p.owner,
            u.username AS added_by_username,
            'Main' AS source_table -- Add this line
        FROM properties p
        LEFT JOIN users u ON p.added_by_user_id = u.user_id
        """
        query_parts.append(main_props_query)
        # Query for properties from the 'propertiesForTransfer' table
        transfer_props_query = """
        SELECT
            pt.property_id,
            pt.title_deed_number,
            pt.location,
            pt.size,
            pt.description,
            NULL AS price, -- This table doesn't have a price column
            pt.contact,
            pt.image_paths,
            pt.title_image_paths,
            NULL AS status, -- This table doesn't have a status column
            pt.added_by_user_id,
            pt.owner,
            u.username AS added_by_username,
            'Transfer' AS source_table -- Add this line
        FROM propertiesForTransfer pt
        LEFT JOIN users u ON pt.added_by_user_id = u.user_id
        """
        query_parts.append(transfer_props_query)
        # Combine queries with UNION ALL
        combined_query = " UNION ALL ".join(query_parts)
        # Add WHERE clause and filters
        full_query = f"SELECT * FROM ({combined_query}) AS combined_results WHERE 1=1"
        params = []

        if search_query:
            full_query += " AND (title_deed_number LIKE %s OR location LIKE %s OR description LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

        if min_size is not None:
            full_query += " AND size >= %s"
            params.append(min_size)

        if max_size is not None:
            full_query += " AND size <= %s"
            params.append(max_size)
        
        if status:
            # Note: Status filter only applies to properties with a status column
            full_query += " AND status = %s"
            params.append(status)

        full_query += " ORDER BY property_id DESC"
        if limit is not None:
            full_query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            full_query += " OFFSET %s"
            params.append(offset)
        results_rows = self._execute_query(full_query, tuple(params), fetch_all=True)
        return results_rows if results_rows else []

    def get_property_by_source(self, property_id, source_table):
        """
        Fetches a single property from either the 'properties' or 'propertiesForTransfer' table
        based on its property ID and source table.
        """
        if source_table == 'Main':
           query = """
           SELECT
               p.property_id, p.title_deed_number, p.location, p.size, p.description,
               p.price, p.contact, p.image_paths, p.title_image_paths, p.status,
               p.added_by_user_id, p.owner, u.username AS added_by_username
           FROM properties p
           LEFT JOIN users u ON p.added_by_user_id = u.user_id
           WHERE p.property_id = %s
           """
           results_row = self._execute_query(query, (property_id,), fetch_one=True)
        elif source_table == 'Transfer':
           query = """
           SELECT
               pt.property_id, pt.title_deed_number, pt.location, pt.size, pt.description,
               NULL AS price, pt.contact, pt.image_paths, pt.title_image_paths, NULL AS status,
               pt.added_by_user_id, pt.owner, u.username AS added_by_username
           FROM propertiesForTransfer pt
           LEFT JOIN users u ON pt.added_by_user_id = u.user_id
           WHERE pt.property_id = %s
           """
           results_row = self._execute_query(query, (property_id,), fetch_one=True)
        else:
            results_row = None
    
        return results_row if results_row else None

    def execute_property_transfer(self, property_id, from_client_id, to_client_id, transfer_price, transfer_date, executed_by_user_id, supervising_agent_id, document_path, source_table):
        """
        Executes a property transfer transaction:
        1. Updates the owner in the correct table (properties or propertiesForTransfer).
        2. Records the transfer details in the property_transfers table.
        
        Returns: True on success, False on failure.
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Fetch the name of the new owner from the clients table
            cursor.execute("SELECT name FROM clients WHERE client_id = %s", (to_client_id,))
            new_owner_name = cursor.fetchone()
            
            if new_owner_name:
                new_owner_name = new_owner_name['name']
            else:
                raise ValueError(f"Client with ID {to_client_id} not found.")

            # 2. Update the property owner in the correct source table
            if source_table == 'Main':
                cursor.execute("UPDATE properties SET owner = %s WHERE property_id = %s", (new_owner_name, property_id))
            elif source_table == 'Transfer':
                cursor.execute("UPDATE propertiesForTransfer SET owner = %s WHERE property_id = %s", (new_owner_name, property_id))
            else:
                raise ValueError(f"Invalid source table: {source_table}")

            # 3. Insert a record into the 'property_transfers' table
            transfer_record_query = """
            INSERT INTO property_transfers (
                property_id, from_client_id, to_client_id, transfer_price,
                transfer_date, executed_by_user_id, supervising_agent_id,
                transfer_document_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(transfer_record_query, (
                property_id, from_client_id, to_client_id, transfer_price,
                transfer_date, executed_by_user_id, supervising_agent_id,
                document_path
            ))

            conn.commit()
            return True

        except Exception as e:
            print(f"Database error during property transfer: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    # Add any missing methods here if they were in the truncated part.
    # For example, if there are methods like get_client_by_contact_info, add_client, etc., define them similarly.
    # Assuming they exist in the original, here's an example for add_client (referenced but not shown):

    def add_client(self, name, contact_info, status='active', added_by_user_id=None):
        query = "INSERT INTO clients (name, contact_info, status, added_by_user_id) VALUES (%s, %s, %s, %s)"
        return self._execute_query(query, (name, contact_info, status, added_by_user_id))

    def get_client_by_contact_info(self, contact_info):
        query = "SELECT * FROM clients WHERE contact_info = %s"
        return self._execute_query(query, (contact_info,), fetch_one=True)