import mysql.connector
import os
from datetime import datetime
from tkinter import messagebox
import bcrypt
import sys

# Define the path for the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

# MySQL database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'real_estate_db'
}

class DatabaseManager:
    """
    Manages all interactions with the MySQL database for the Real Estate Management System.
    """
    def __init__(self, db_config=db_config):
        self.db_config = db_config
        self._create_reports_directory()
        self._create_tables() 

    def _create_reports_directory(self):
        """Ensures the 'reports' directory exists."""
        if not os.path.exists(REPORTS_DIR):
            os.makedirs(REPORTS_DIR)
            print(f"Created reports directory: {REPORTS_DIR}")

    def _get_connection(self):
        """
        Returns a connection object to the database.
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            return conn
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL database: {err}")
            return None
    
    def _execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        """
        A helper method to execute SQL queries.
        Can fetch one, fetch all, or just execute (for INSERT, UPDATE, DELETE).
        Returns dictionary-like objects for SELECT queries.
        """
        conn = self._get_connection()
        if not conn:
            return None

        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                
                # Check if the query is a SELECT statement and fetch results
                if query.strip().upper().startswith("INSERT"):
                    conn.commit()
                    return cursor.lastrowid
                
                if query.strip().upper().startswith(("UPDATE", "DELETE")):
                    conn.commit()
                    return cursor.rowcount > 0
                
                # For SELECT, fetch and return the results
                if fetch_one:
                    return cursor.fetchone()
                
                if fetch_all:
                    return cursor.fetchall()
                
                return None
        except mysql.connector.Error as err:
            print(f"Database error: {err}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"An unexpected error occurred in _execute_query: {e}", file=sys.stderr)
            return None
        finally:
            if conn and conn.is_connected():
                conn.close()

    def _execute_transaction(self, *queries_and_params):
        conn = None
        try:
            conn = self._get_connection()
            if not conn:
                return False
            with conn.cursor() as cursor:
                for query, params in queries_and_params:
                    cursor.execute(query, params)
                conn.commit()
                return True
        except mysql.connector.Error as err:
            print(f"Database transaction error: {err}", file=sys.stderr)
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            print(f"An unexpected error occurred in _execute_transaction: {e}", file=sys.stderr)
            if conn:
               conn.rollback()
            return False
        finally:
            if conn and conn.is_connected():
                conn.close()

    def _create_tables(self):
        """Initializes the database by creating tables if they don't exist."""
        try:
            queries = [
                '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT PRIMARY KEY AUTO_INCREMENT,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    is_agent VARCHAR(255) DEFAULT 'no',
                    role VARCHAR(255) DEFAULT 'user'
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS properties (
                    property_id INT PRIMARY KEY AUTO_INCREMENT,
                    property_type VARCHAR(255) NOT NULL,
                    title_deed_number VARCHAR(255) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    size FLOAT NOT NULL,
                    description TEXT,
                    owner VARCHAR(255) NOT NULL,
                    telephone_number VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    price FLOAT NOT NULL,
                    image_paths TEXT,
                    title_image_paths TEXT,
                    status VARCHAR(255) NOT NULL DEFAULT 'Available',
                    added_by_user_id INT,
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS propertiesForTransfer (
                    property_id INT PRIMARY KEY AUTO_INCREMENT,
                    title_deed_number VARCHAR(255) NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    size FLOAT NOT NULL,
                    description TEXT,
                    owner VARCHAR(255) NOT NULL,
                    telephone_number VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    image_paths TEXT,
                    title_image_paths TEXT,
                    added_by_user_id INT,
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS clients (
                    client_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    telephone_number VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL,
                    status VARCHAR(255) NOT NULL DEFAULT 'active',
                    added_by_user_id INT,
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS daily_clients (
                visit_id INT PRIMARY KEY AUTO_INCREMENT,
                client_id INT NOT NULL,
                purpose VARCHAR(255),
                brought_by VARCHAR(255),
                added_by_user_id INT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients(client_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS buyers (
                    buyer_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    contact VARCHAR(255) NOT NULL,
                    added_by_user_id INT,
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
                    property_id INT NOT NULL,
                    client_id INT NOT NULL,
                    payment_mode VARCHAR(255) NOT NULL,
                    total_amount_paid FLOAT NOT NULL,
                    discount FLOAT DEFAULT 0.0,
                    balance FLOAT DEFAULT 0.0,
                    transaction_date DATETIME NOT NULL,
                    receipt_path TEXT,
                    added_by_user_id INT,
                    FOREIGN KEY (property_id) REFERENCES properties(property_id),
                    FOREIGN KEY (client_id) REFERENCES clients(client_id),
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS proposed_lots (
                    lot_id INT PRIMARY KEY AUTO_INCREMENT,
                    parent_block_id INT NOT NULL,
                    size FLOAT NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    surveyor_name VARCHAR(255) NOT NULL,
                    created_by VARCHAR(255) NOT NULL,
                    title_deed_number VARCHAR(255),
                    price VARCHAR(255) DEFAULT '0.0',
                    status VARCHAR(255) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS property_transfers (
                    transfer_id INT PRIMARY KEY AUTO_INCREMENT,
                    property_id INT NOT NULL,
                    from_client_id INT,
                    to_client_id INT NOT NULL,
                    transfer_price FLOAT NOT NULL,
                    transfer_date DATE NOT NULL,
                    executed_by_user_id INT NOT NULL,
                    supervising_agent_id INT,
                    transfer_document_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (property_id) REFERENCES properties(property_id),
                    FOREIGN KEY (from_client_id) REFERENCES clients(client_id),
                    FOREIGN KEY (to_client_id) REFERENCES clients(client_id),
                    FOREIGN KEY (executed_by_user_id) REFERENCES users(user_id),
                    FOREIGN KEY (supervising_agent_id) REFERENCES users(user_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    status VARCHAR(255) DEFAULT 'active',
                    added_by VARCHAR(255) NOT NULL,
                    timestamp DATETIME NOT NULL
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS payment_plans (
                    plan_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    deposit_percentage FLOAT NOT NULL,
                    duration_months INT NOT NULL,
                    interest_rate FLOAT NOT NULL,
                    created_by VARCHAR(255) NOT NULL
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS service_clients (
                    client_id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(255) NOT NULL,
                    telephone_number VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL,
                    brought_by VARCHAR(255),
                    added_by VARCHAR(255) NOT NULL,
                    timestamp DATETIME NOT NULL
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS client_files (
                    file_id INT PRIMARY KEY AUTO_INCREMENT,
                    client_id INT NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    added_by VARCHAR(255) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (client_id) REFERENCES service_clients(client_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS service_jobs (
                    job_id INT PRIMARY KEY AUTO_INCREMENT,
                    file_id INT NOT NULL,
                    job_description TEXT,
                    title_name VARCHAR(255) NOT NULL,
                    title_number VARCHAR(255) NOT NULL,
                    fee FLOAT NOT NULL,
                    status VARCHAR(255) NOT NULL DEFAULT 'Ongoing',
                    added_by VARCHAR(255) NOT NULL,
                    brought_by VARCHAR(255) DEFAULT 'self',
                    timestamp DATETIME NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES client_files(file_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS service_payments (
                    payment_id INT PRIMARY KEY AUTO_INCREMENT,
                    job_id INT NOT NULL UNIQUE,
                    fee FLOAT NOT NULL,
                    amount FLOAT NOT NULL,
                    balance FLOAT NOT NULL,
                    payment_date VARCHAR(255) NOT NULL,
                    status VARCHAR(255) DEFAULT 'unpaid',
                    FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS service_payments_history (
                    history_id INT PRIMARY KEY AUTO_INCREMENT,
                    payment_id INT NOT NULL,
                    payment_amount FLOAT NOT NULL,
                    payment_type VARCHAR(255),
                    payment_date VARCHAR(255) NOT NULL,
                    FOREIGN KEY (payment_id) REFERENCES service_payments(payment_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS service_dispatch (
                    dispatch_id INT PRIMARY KEY AUTO_INCREMENT,
                    job_id INT NOT NULL,
                    dispatch_date DATE NOT NULL,
                    reason_for_dispatch TEXT,
                    collected_by VARCHAR(255),
                    collector_phone VARCHAR(255),
                    sign BLOB,
                    FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id INT PRIMARY KEY AUTO_INCREMENT,
                    timestamp DATETIME NOT NULL,
                    user_id INT NOT NULL,
                    action_type VARCHAR(255) NOT NULL,
                    details TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                '''
            ]
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for query in queries:
                    cursor.execute(query)
                conn.commit()
            print("Database initialized successfully.")
        except mysql.connector.Error as err:
            print(f"Error creating tables: {err}")

    ## User Management Methods
    def add_user(self, username, password, is_agent='no',role='user'):
        """
        Adds a new user to the database with a hashed password.
        Returns: The ID of the newly added user, or None on error (e.g., duplicate username).
        """
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            query = "INSERT INTO users (username, password_hash, is_agent, role) VALUES (%s, %s, %s, %s)"
            return self._execute_query(query, (username, hashed_password, is_agent, role))
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
            stored_password_hash = user_data_row['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash):
                del user_data_row['password_hash']
                return user_data_row
        return None

    def get_user_by_username(self, username):
        """
        Retrieves user data by username without password authentication.
        Returns: The user's data (user_id, username, role) as a dict if found, None otherwise.
        """
        query = "SELECT user_id, username, role FROM users WHERE username = %s"
        return self._execute_query(query, (username,), fetch_one=True)

    def get_user_by_id(self, user_id):
        """
        Retrieves a user by their ID.
        Returns: The user's data (excluding password_hash) as a dict, or None if not found.
        """
        query = "SELECT user_id, username, role FROM users WHERE user_id = %s"
        return self._execute_query(query, (user_id,), fetch_one=True)

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

    def get_all_users(self):
        """Retrieves all user records from the database."""
        try:
            rows = self._execute_query("SELECT user_id, username, role FROM users", fetch_all=True)
            return rows if rows else []
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
                params.append(bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))
            if new_role:
                query_parts.append("role = %s")
                params.append(new_role)

            if not query_parts:
                return False

            query = "UPDATE users SET " + ", ".join(query_parts) + " WHERE user_id = %s"
            params.append(user_id)

            return self._execute_query(query, tuple(params))
        except mysql.connector.IntegrityError:
            messagebox.showerror("Error", f"Username '{new_username}' already exists.")
            return False
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id):
        """Deletes a user from the database."""
        try:
            return self._execute_query("DELETE FROM users WHERE user_id = %s", (user_id,))
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def get_username_by_id(self, user_id):
        """
        Fetches the username of a user based on their user ID.
        """
        try:
            row = self._execute_query("SELECT username FROM users WHERE user_id = %s", (user_id,), fetch_one=True)
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
        return self._execute_query(query, (title_deed_number,), fetch_all=True)

    def add_property(self, property_type, title_deed_number, location, size, description, owner, telephone_number, email, price, image_paths=None, title_image_paths=None, status='Available', added_by_user_id=None):
        """
        Adds a new property to the database and ensures the owner is in the clients table.
        """
        existing_properties = self.get_properties_by_title_deed(title_deed_number)
        client_status = 'active'
        
        for prop in existing_properties:
            if prop['status'].lower() == 'available':
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        client_exists = self.get_client_by_contact_info(telephone_number)
        
        if not client_exists:
            self.add_client(name=owner, telephone_number=telephone_number, email=email, status=client_status, added_by_user_id=added_by_user_id)

        query = '''INSERT INTO properties (property_type, title_deed_number, location, size, description, owner, telephone_number, email, price, image_paths, title_image_paths, status, added_by_user_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        return self._execute_query(query, (property_type, title_deed_number, location, size, description, owner, telephone_number, email, price, image_paths, title_image_paths, status, added_by_user_id))

    def get_propertiesfortransfer_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM propertiesForTransfer WHERE title_deed_number = %s;"
        return self._execute_query(query, (title_deed_number,), fetch_all=True)

    def add_propertyForTransfer(self, title_deed_number, location, size, description, owner, telephone_number, email,  image_paths=None, title_image_paths=None, added_by_user_id=None):
        """
        Adds a new property to the database and ensures the owner is in the clients table.
        """
        existing_properties = self.get_propertiesfortransfer_by_title_deed(title_deed_number)
        client_status = 'active'
        
       

        for prop in existing_properties:
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        client_exists = self.get_client_by_contact_info(telephone_number)
        
        if not client_exists:
            self.add_client(name=owner, telephone_number=telephone_number, email=email,   status=client_status,  added_by_user_id=added_by_user_id)

        query = '''INSERT INTO propertiesForTransfer (title_deed_number, location, size, description, owner, telephone_number, email, image_paths, title_image_paths,  added_by_user_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        return self._execute_query(query, (title_deed_number, location, size, description, owner, telephone_number, email, image_paths, title_image_paths, added_by_user_id))
        
    def get_property(self, property_id):
        """
        Retrieves a property by its ID.
        Returns: The property details as a dict, or None if not found.
        """
        query = "SELECT * FROM properties WHERE property_id = %s"
        return self._execute_query(query, (property_id,), fetch_one=True)

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
        return self._execute_query(query, params, fetch_all=True)
    
    def get_all_properties_lots(self, status=None, property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = []
        if status:
            query += " WHERE status = %s"
            params.append(status)
        if property_type:
            query += " AND property_type = %s"
            params.append(property_type)
        return self._execute_query(query, params, fetch_all=True)
    
    def get_all_properties_blocks(self, status=None, property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = []
        if status:
            query += " WHERE status = %s"
            params.append(status)
        if property_type:
            query += " AND property_type = %s"
            params.append(property_type)
        return self._execute_query(query, params, fetch_all=True)

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
            p.telephone_number,
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
            query += " AND p.size >= %s"
            params.append(min_size)
        
        if max_size is not None:
            query += " AND p.size <= %s"
            params.append(max_size)

        if status: 
            query += " AND p.status = %s"
            params.append(status)

        query += " ORDER BY p.property_id DESC"

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)

        return self._execute_query(query, tuple(params), fetch_all=True)
    
    def add_buyer(self, name, contact, added_by_user_id=None):
        query = "INSERT INTO buyers (name, contact, added_by_user_id) VALUES (%s, %s, %s)"
        return self._execute_query(query, (name, contact, added_by_user_id))
    

    ## CRUD Operations for Clients
    def add_client(self, name, telephone_number, email,  status,  added_by_user_id=None):
        """
        Adds a new client to the database, tracking the user who added them.
        Returns: The ID of the new client, or None on error/duplicate contact_info.
        """
        check_query = "SELECT client_id, status FROM clients WHERE telephone_number = %s"
        existing_client = self._execute_query(check_query, (telephone_number,), fetch_one=True)

        if existing_client:
            client_id = existing_client['client_id']
            current_status = existing_client['status']
            if current_status == 'inactive':
                update_query = "UPDATE clients SET name = %s, email = %s,  status = 'active',  added_by_user_id = %s WHERE client_id = %s"
                self._execute_query(update_query, (name, email, added_by_user_id, client_id))
                return client_id
            else:
                print(f"Error: A client with the telephone number {telephone_number} already exists and is active.")
                return None
        else:
            query = "INSERT INTO clients (name, telephone_number, email,  status,  added_by_user_id) VALUES (%s, %s, %s, %s, %s)"
            return self._execute_query(query, (name, telephone_number, email,  status,  added_by_user_id))

    def get_client(self, client_id):
        """
        Retrieves a client by their ID.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE client_id = %s"
        return self._execute_query(query, (client_id,), fetch_one=True)
    
    def get_client_by_contact_info(self, contact_info):
        """
        Retrieves a client by their contact information.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE telephone_number = %s"
        return self._execute_query(query, (contact_info,), fetch_one=True)

    def get_client_by_telephone_number(self, telephone_number, email):
        """
        Retrieves a client by their contact information.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE telephone_number = %s AND email = %s"
        return self._execute_query(query, (telephone_number, email), fetch_one=True)
    
    def get_all_clients(self):
        """
        Retrieves all clients from the database, including the username of the user who added them.
        Returns: A list of dictionaries representing clients.
        """
        query = """
        SELECT
            c.client_id,
            c.name,
            c.telephone_number,
            c.email,
            c.status,
            c.added_by_user_id,
            u.username AS added_by_username
        FROM
            clients c
        LEFT JOIN
            users u ON c.added_by_user_id = u.user_id
        WHERE
            c.status = 'active'
        ORDER BY c.name ASC
        """
        return self._execute_query(query, fetch_all=True)

    def get_all_clients_fortransferform(self):
        """
        Retrieves all clients from the database, including the username of the user who added them.
        Returns: A list of dictionaries representing clients.
        """
        query = """
        SELECT
            c.client_id,
            c.name,
            c.telephone_number,
            c.status,
            c.added_by_user_id,
            u.username AS added_by_username
        FROM
            clients c
        LEFT JOIN
            users u ON c.added_by_user_id = u.user_id
        ORDER BY c.name ASC
        """
        return self._execute_query(query, fetch_all=True)

    def update_client(self, client_id, **kwargs):
        """
        Updates details of an existing client.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in ['name', 'telephone_number','email']:
                set_clauses.append(f"{key} = %s")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for client update.")
            return False

        params.append(client_id)
        query = f"UPDATE clients SET {', '.join(set_clauses)} WHERE client_id = %s"
        return self._execute_query(query, params)

    def delete_client(self, client_id):
        """s
        Deletes a client from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "UPDATE clients SET status = 'inactive' WHERE client_id = %s"
        return self._execute_query(query, (client_id,))

    def get_total_clients(self):
        """
        Returns the total count of clients.
        Returns: Total number of clients.
        """
        query = "SELECT COUNT(*) FROM clients WHERE status = 'active'"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row['COUNT(*)'] if result_row else 0

    def get_client_by_id(self, client_id):
        """
        Retrieves client details by ID, formatted as a dictionary.
        """
        try:
            query = "SELECT * FROM clients WHERE client_id = %s"
            return self._execute_query(query, (client_id,), fetch_one=True)
        except Exception as e:
            print(f"Error getting client by ID: {e}")
            return None

    ## CRUD Operations for Transactions
    def add_transaction(self, property_id, client_id, payment_mode, total_amount_paid, discount=0.0, balance=0.0, receipt_path=None, added_by_user_id=None):
        """ Adds a new sales transaction. """
        transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = '''INSERT INTO transactions (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
        return self._execute_query(query, (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id))

    def get_transaction(self, transaction_id):
        """ Retrieves a transaction by its ID. """
        query = "SELECT * FROM transactions WHERE transaction_id = %s"
        return self._execute_query(query, (transaction_id,), fetch_one=True)

    def get_transactions_by_property(self, property_id):
        """ Retrieves all transactions related to a specific property. """
        query = "SELECT * FROM transactions WHERE property_id = %s"
        return self._execute_query(query, (property_id,), fetch_all=True)

    def get_transactions_by_client(self, client_id):
        """ Retrieves all transactions related to a specific client. """
        query = "SELECT * FROM transactions WHERE client_id = %s"
        return self._execute_query(query, (client_id,), fetch_all=True)

    def get_all_transactions(self):
        """ Retrieves all transactions from the database. """
        query = "SELECT * FROM transactions"
        return self._execute_query(query, fetch_all=True)

    def get_total_pending_sales_payments(self):
        """ Calculates the sum of outstanding balances from property transactions. """
        query = "SELECT SUM(balance) FROM transactions WHERE balance > 0"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row['SUM(balance)'] if result_row and result_row['SUM(balance)'] is not None else 0.0

    def update_transaction(self, transaction_id, **kwargs):
        """ Updates details of an existing transaction. """
        set_clauses = []
        params = []
        allowed_columns = ['property_id', 'client_id', 'payment_mode', 'total_amount_paid', 'discount', 'balance', 'transaction_date', 'receipt_path', 'added_by_user_id']
        for key, value in kwargs.items():
            if key in allowed_columns:
                set_clauses.append(f"{key} = %s")
                params.append(value)
            else:
                print(f"Warning: Attempted to update disallowed column: {key}")
        
        if not set_clauses:
            print("No valid columns provided for transaction update.")
            return False

        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(set_clauses)} WHERE transaction_id = %s"
        return self._execute_query(query, params)

    def get_transactions_with_details(self, status=None, start_date=None, end_date=None, payment_mode=None, client_name_search=None, property_search=None, client_contact_search=None):
        """ Retrieves transactions with details from linked properties and clients, allowing for various filtering options, including client contact info. """
        query = """
        SELECT
            t.transaction_id,
            t.transaction_date,
            t.payment_mode,
            t.total_amount_paid,
            t.discount,
            t.balance,
            t.receipt_path,
            c.name AS client_name,
            c.telephone_number AS client_contact_info,
            p.property_id,
            p.title_deed_number,
            p.location,
            p.size,
            p.price AS property_price,
            p.status AS property_status
        FROM
            transactions t
        JOIN
            clients c ON t.client_id = c.client_id
        JOIN
            properties p ON t.property_id = p.property_id
        WHERE 1=1
        """
        params = []
        if status == 'complete':
            query += " AND t.balance = 0"
        elif status == 'pending':
            query += " AND t.balance > 0"
        if start_date:
            query += " AND t.transaction_date >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= %s"
            params.append(f"{end_date} 23:59:59")
        if payment_mode:
            query += " AND t.payment_mode = %s"
            params.append(payment_mode)
        if client_name_search:
            query += " AND c.name LIKE %s"
            params.append(f"%{client_name_search}%")
        if property_search:
            query += " AND (p.title_deed_number LIKE %s OR p.location LIKE %s)"
            params.append(f"%{property_search}%")
            params.append(f"%{property_search}%")
        if client_contact_search:
            query += " AND c.telephone_number LIKE %s"
            params.append(f"%{client_contact_search}%")
        query += " ORDER BY t.transaction_date DESC"
        return self._execute_query(query, params, fetch_all=True)

    ## NEW METHODS FOR SOLD PROPERTIES UI
    def get_total_sold_properties_count(self, start_date=None, end_date=None):
        """ Returns the total count of properties with 'Sold' status, optionally filtered by transaction date. """
        query = "SELECT COUNT(*) FROM properties p JOIN transactions t ON p.property_id = t.property_id WHERE p.status = 'Sold'"
        params = []
        if start_date:
            query += " AND t.transaction_date >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= %s"
            params.append(f"{end_date} 23:59:59")
        result_row = self._execute_query(query, params, fetch_one=True)
        return result_row['COUNT(*)'] if result_row else 0

    def get_sold_properties_paginated(self, limit, offset, start_date=None, end_date=None):
        """ Retrieves sold properties along with their transaction and client details, supporting pagination and date filtering. """
        query = """
        SELECT
            p.property_id,
            p.title_deed_number,
            p.location,
            p.size,
            p.price AS original_price,
            t.transaction_id,
            t.transaction_date AS date_sold,
            t.total_amount_paid,
            t.discount,
            t.balance,
            c.name AS name,
            c.telephone_number AS client_contact_info
        FROM
            properties p
        JOIN
            transactions t ON p.property_id = t.property_id
        JOIN
            clients c ON t.client_id = c.client_id
        WHERE p.status = 'Sold'
        """
        params = []
        if start_date:
            query += " AND t.transaction_date >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= %s"
            params.append(f"{end_date} 23:59:59")
        query += """
        ORDER BY t.transaction_date DESC, p.title_deed_number ASC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        return self._execute_query(query, params, fetch_all=True)

    def count_available_properties(self):
        """Returns the count of properties with 'Available' status."""
        query = "SELECT COUNT(*) FROM properties WHERE status = 'Available'"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row['COUNT(*)'] if result_row else 0

    def add_service_client(self, name, telephone_number, email, brought_by, added_by):
        """ Adds a new client to the database. """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = ''' INSERT INTO service_clients (name, telephone_number, email, brought_by, added_by, timestamp) VALUES (%s, %s, %s, %s, %s, %s) '''
        return self._execute_query(query, (name, telephone_number, email, brought_by, added_by, timestamp))

    def add_client_file(self, client_id, file_name, added_by):
        """ Adds a new file for an existing client. """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = ''' INSERT INTO client_files (client_id, file_name, added_by, timestamp) VALUES (%s, %s, %s, %s) '''
        return self._execute_query(query, (client_id, file_name, added_by, timestamp))

    def get_all_client_files(self):
        """ Retrieves all client files from the database, joining with the service_clients table to include client names and contact info. """
        query = """ SELECT cf.file_id, cf.file_name, sc.name AS client_name, sc.telephone_number AS telephone_number FROM client_files cf JOIN service_clients sc ON cf.client_id = sc.client_id ORDER BY sc.name """
        return self._execute_query(query, fetch_all=True)

    def get_client_file_details(self, file_id):
        """ Retrieves a single client file's details. """
        query = "SELECT * FROM client_files WHERE file_id = %s"
        return self._execute_query(query, (file_id,), fetch_one=True)

    def add_service_job(self, file_id, job_description, title_name, title_number, fee, status, added_by, brought_by):
        """ Adds a new job for a client's file. """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = '''
            INSERT INTO service_jobs (file_id, job_description, title_name, title_number, fee, status, added_by, brought_by, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        return self._execute_query(query, (file_id, job_description, title_name, title_number, fee, status, added_by, brought_by, timestamp))

    def get_service_job_by_file_id(self, file_id):
        """ Retrieves all jobs related to a specific file. """
        query = "SELECT * FROM service_jobs WHERE file_id = %s"
        return self._execute_query(query, (file_id,), fetch_all=True)

    def get_all_service_jobs_paginated(self, limit=None, offset=None, search_query=None):
        """ Retrieves paginated list of all service jobs with client details. """
        query = """
            SELECT
                sj.job_id, sj.job_description, sj.title_name, sj.title_number, sj.fee, sj.status, sj.added_by, sj.brought_by, sj.timestamp,
                cf.file_name, sc.name as client_name, sc.telephone_number
            FROM service_jobs sj
            JOIN client_files cf ON sj.file_id = cf.file_id
            JOIN service_clients sc ON cf.client_id = sc.client_id
            WHERE 1=1
        """
        params = []
        if search_query:
            query += " AND (sj.title_name LIKE %s OR sj.title_number LIKE %s OR sj.job_description LIKE %s OR sc.name LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
        
        query += " ORDER BY sj.timestamp DESC"
        
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
        
        return self._execute_query(query, tuple(params), fetch_all=True)

    def add_payment(self, job_id, amount, fee, balance):
        """ Adds a new service payment record. """
        payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = '''
            INSERT INTO service_payments (job_id, amount, fee, balance, payment_date)
            VALUES (%s, %s, %s, %s, %s)
        '''
        params = (job_id, amount, fee, balance, payment_date)
        return self._execute_query(query, params)
    

    def get_service_payment_by_job_id(self, job_id):
        """ Retrieves a service payment record by job ID. """
        query = "SELECT * FROM service_payments WHERE job_id = %s"
        return self._execute_query(query, (job_id,), fetch_one=True)

    def update_service_payment(self, payment_id, **kwargs):
        """ Updates a service payment record. """
        set_clauses = []
        params = []
        allowed_cols = ['fee', 'amount', 'balance', 'payment_date', 'status']
        for key, value in kwargs.items():
            if key in allowed_cols:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses: return False
        
        params.append(payment_id)
        query = f"UPDATE service_payments SET {', '.join(set_clauses)} WHERE payment_id = %s"
        return self._execute_query(query, params)

    def add_payment_history(self, payment_id, payment_amount, payment_type):
        """ Adds a payment history entry for a service payment. """
        payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = '''
            INSERT INTO service_payments_history (payment_id, payment_amount, payment_type, payment_date)
            VALUES (%s, %s, %s, %s)
        '''
        return self._execute_query(query, (payment_id, payment_amount, payment_type, payment_date))

    def get_payment_history_by_payment_id(self, payment_id):
        """ Retrieves payment history entries for a specific service payment. """
        query = "SELECT * FROM service_payments_history WHERE payment_id = %s ORDER BY payment_date ASC"
        return self._execute_query(query, (payment_id,), fetch_all=True)

    def add_service_dispatch_record(self, job_id, reason_for_dispatch, collected_by, collector_phone, sign):
        """ Adds a new dispatch record for a completed job. """
        dispatch_date = datetime.now().strftime('%Y-%m-%d')
        query = '''
            INSERT INTO service_dispatch (job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone, sign)
            VALUES (%s, %s, %s, %s, %s, %s)
        '''
        return self._execute_query(query, (job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone, sign))

    def get_service_dispatch_by_job_id(self, job_id):
        """ Retrieves a dispatch record for a specific job ID. """
        query = "SELECT * FROM service_dispatch WHERE job_id = %s"
        return self._execute_query(query, (job_id,), fetch_one=True)
    
    def get_total_survey_jobs(self):
        query = "SELECT COUNT(*) FROM service_jobs"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row['COUNT(*)'] if result_row else 0
    
    def get_all_agents(self):
        try:
            rows = self._execute_query(
                "SELECT agent_id, name, status, added_by, timestamp FROM agents",
                fetch_all=True
            )
            if rows:
                return rows
            return []
        except Exception as e:
           print(f"Error fetching all agents: {e}")
           return []
        
    def add_agent(self, name, added_by):
        try:
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
        
    def delete_agent(self, agent_id):
        query = "DELETE FROM agents WHERE agent_id = %s"
        params = (agent_id,)
        return self._execute_query(query, params)
        
    def check_if_user_is_agent(self, user_id):
        query = "SELECT is_agent FROM users WHERE user_id = %s"
        params = (user_id,)
        result = self._execute_query(query, params, fetch_one=True)
        if result and result.get('is_agent') == 1:
            return True
        return False
    
    def get_agent_by_user_id(self, user_id):
        query = "SELECT * FROM users WHERE user_id = %s AND is_agent = 1"
        params = (user_id,)
        return self._execute_query(query, params, fetch_one=True)
        
    def get_agent_by_name(self, agent_name):
        try:
            query = "SELECT agent_id, name, status, added_by, timestamp FROM agents WHERE name = %s"
            row = self._execute_query(query, (agent_name,), fetch_one=True)
            return row
        except Exception as e:
            print(f"Error fetching agent by name '{agent_name}': {e}")
            return None
    def update_agent(self, agent_id, new_name=None, new_status=None):
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
        return self._execute_query(query, tuple(params))
        
    def get_all_propertiesForTransfer_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        params = []
        main_props_query = """
        SELECT
            p.property_id,
            p.title_deed_number,
            p.location,
            p.size,
            p.description,
            p.price,
            p.telephone_number,
            p.image_paths,
            p.title_image_paths,
            p.status,
            p.added_by_user_id,
            p.owner,
            u.username AS added_by_username,
            'Main' AS source_table
        FROM properties p
        LEFT JOIN users u ON p.added_by_user_id = u.user_id
        """
        transfer_props_query = """
        SELECT
            pt.property_id,
            pt.title_deed_number,
            pt.location,
            pt.size,
            pt.description,
            NULL AS price,
            pt.telephone_number,
            pt.image_paths,
            pt.title_image_paths,
            NULL AS status,
            pt.added_by_user_id,
            pt.owner,
            u.username AS added_by_username,
            'Transfer' AS source_table
        FROM propertiesForTransfer pt
        LEFT JOIN users u ON pt.added_by_user_id = u.user_id
        """

        combined_query = f"({main_props_query}) UNION ALL ({transfer_props_query})"
        full_query = f"SELECT * FROM ({combined_query}) AS combined_results WHERE 1=1"
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
            full_query += " AND (status = %s OR status IS NULL)"
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
        if source_table == 'Main':
            query = """
            SELECT
                p.property_id, p.title_deed_number, p.location, p.size, p.description,
                p.price, p.telephone_number, p.image_paths, p.title_image_paths, p.status,
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
                NULL AS price, pt.telephone_number, pt.image_paths, pt.title_image_paths, NULL AS status,
                pt.added_by_user_id, pt.owner, u.username AS added_by_username
            FROM propertiesForTransfer pt
            LEFT JOIN users u ON pt.added_by_user_id = u.user_id
            WHERE pt.property_id = %s
            """
            results_row = self._execute_query(query, (property_id,), fetch_one=True)
        else:
            results_row = None
        return results_row if results_row else None
    
    def get_proposed_lots_with_details(self):
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
    
    def propose_new_lot(self, proposed_lot_data):
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
        self._execute_query(query, params)

    def get_lot_details_for_rejection(self, lot_id):        
        query = """
        SELECT parent_block_id, size
        FROM proposed_lots
        WHERE lot_id = ?
        """
        row = self._execute_query(query, (lot_id,), fetch_one=True)
        if row:
            return dict(row)
        return None
    
    def finalize_lot(self, lot_id):
        query = '''
            UPDATE proposed_lots
            SET status = 'Confirmed'
            WHERE lot_id = %s
        '''
        self._execute_query(query, (lot_id,))

    def reject_lot(self, lot_id):
        query = '''
            UPDATE proposed_lots
            SET status = 'Rejected'
            WHERE lot_id = %s
        '''
        self._execute_query(query, (lot_id,))

    def return_size_to_block(self, block_id, size_to_add):
        try:
            query_select = "SELECT size, status FROM properties WHERE property_id = %s"
            result = self._execute_query(query_select, (block_id,), fetch_one=True)
            if result:
                current_size = result['size']
                current_status = result['status']
                new_size = current_size + size_to_add
                new_status = 'Available' if current_status == 'Unavailable' else current_status
                query_update = "UPDATE properties SET size = %s, status = %s WHERE property_id = %s"
                success = self._execute_query(query_update, (new_size, new_status, block_id))
                if success:
                    print(f"Size {size_to_add} successfully returned to block {block_id}. New size: {new_size}. New status: {new_status}.")
                else:
                    print(f"Failed to update block with ID {block_id}.")
            else:
                print(f"Block with ID {block_id} not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def update_block_status(self, block_id, status):
        query = "UPDATE properties SET status = %s WHERE property_id = %s"
        self._execute_query(query, (status, block_id))
        print(f"Status for block {block_id} successfully updated to '{status}'.")

    def update_block_size(self, block_id, new_size):
        query = '''
            UPDATE properties
            SET size = %s
            WHERE property_id = %s
        '''
        self._execute_query(query, (new_size, block_id))

    def get_lots_for_update(self):
        query = '''
            SELECT lot_id, title_deed_number, size, status, location
            FROM proposed_lots
            WHERE status IN ('Proposed')
        '''
        return self._execute_query(query, fetch_all=True)
    
    def get_all_jobs(self):
        query = """
            SELECT
                sj.*,
                cf.file_name,
                sc.name AS client_name,
                sc.telephone_number AS telephone_number
            FROM
                service_jobs sj
            JOIN
                client_files cf ON sj.file_id = cf.file_id
            JOIN
                service_clients sc ON cf.client_id = sc.client_id
            ORDER BY
                sj.timestamp DESC
        """
        return self._execute_query(query, fetch_all=True)
    
    def get_file_by_id(self, file_id):
        query = "SELECT * FROM client_files WHERE file_id = %s"
        return self._execute_query(query, (file_id,), fetch_one=True)
    
    def get_filtered_payments(self, filters, page=1, page_size=20):
        base_query = """
                FROM service_payments AS sp
                JOIN service_jobs AS sj ON sp.job_id = sj.job_id
                JOIN client_files AS cf ON sj.file_id = cf.file_id
                JOIN service_clients AS sc ON cf.client_id = sc.client_id
        """
        conditions = []
        params = []
        if 'status' in filters and filters['status'] != 'All':
            conditions.append("sp.status = %s")
            params.append(filters['status'])
        if 'payment_mode' in filters and filters['payment_mode']:
            conditions.append("sp.payment_type = %s")
            params.append(filters['payment_mode'])
        if 'client_name' in filters and filters['client_name']:
            conditions.append("sc.name LIKE %s")
            params.append(f"%{filters['client_name']}%")
        if 'file_name' in filters and filters['file_name']:
            conditions.append("cf.file_name LIKE %s")
            params.append(f"%{filters['file_name']}%")
        if 'title_number' in filters and filters['title_number']:
            conditions.append("sj.title_number LIKE %s")
            params.append(f"%{filters['title_number']}%")
        if 'from_date' in filters and filters['to_date']:
            from_date = filters['from_date']
            to_date = filters['to_date']
            from_date_str = from_date.strftime('%Y-%m-%d 00:00:00')
            to_date_str = to_date.strftime('%Y-%m-%d 23:59:59')
            conditions.append("sp.payment_date BETWEEN %s AND %s")
            params.append(from_date_str)
            params.append(to_date_str)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        count_query = f"SELECT COUNT(*) {base_query}{where_clause}"
        count_result = self._execute_query(count_query, tuple(params), fetch_one=True)
        total_count = count_result['COUNT(*)'] if count_result else 0

        data_query = f"""
            SELECT
                sp.payment_id,
                sc.name AS client_name,
                cf.file_name,
                sj.job_description,
                sj.title_number,
                sp.fee,
                sp.amount,
                sp.balance,
                sp.payment_date
            {base_query}{where_clause}
            ORDER BY sp.payment_date DESC
            LIMIT %s OFFSET %s
        """
        offset = (page - 1) * page_size
        data_params = params + [page_size, offset]
        payments = self._execute_query(data_query, tuple(data_params), fetch_all=True)
        return payments if payments else [], total_count
    
    def update_payment_record(self, payment_id, new_status, final_payment_amount, payment_type):
        select_query = "SELECT amount, balance FROM service_payments WHERE payment_id = %s"
        result = self._execute_query(select_query, (payment_id,), fetch_one=True)
        if not result:
            print(f"Error: Payment record with ID {payment_id} not found.")
            return False
        current_amount = float(result['amount'])
        current_balance = float(result['balance'])
        new_amount = current_amount + final_payment_amount
        new_balance = current_balance - final_payment_amount

        update_query = "UPDATE service_payments SET status = %s, amount = %s, balance = %s WHERE payment_id = %s"

        update_params = (new_status, new_amount, new_balance, payment_id)
        update_successful = self._execute_query(update_query, update_params)

        if not update_successful:
            print("Update failed, returning early.")
            return False
        
        insert_query = "INSERT INTO service_payments_history (payment_id, payment_amount, payment_type, payment_date) VALUES (%s, %s, %s, %s)"
        payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_params = (payment_id, final_payment_amount, payment_type, payment_date)
        insert_successful = self._execute_query(insert_query, insert_params)

        return insert_successful
    
    def get_payment_history(self, payment_id):
        query = """
            SELECT history_id, payment_amount, payment_type, payment_date 
            FROM service_payments_history 
            WHERE payment_id = %s 
            ORDER BY payment_date DESC
        """
        params = (payment_id,)
        history_records = self._execute_query(query, params, fetch_all=True)
        return history_records if history_records else []
    
    def get_job_details(self, job_id):
        query = """
            SELECT
                sj.job_id,
                sj.job_description,
                sj.title_name,
                sj.title_number,
                cf.file_name,
                sc.name AS client_name
            FROM service_jobs sj
            JOIN client_files cf ON sj.file_id = cf.file_id
            JOIN service_clients sc ON cf.client_id = sc.client_id
            WHERE sj.job_id = %s
        """
        params = (job_id,)
        return self._execute_query(query, params, fetch_one=True)
    
    def save_dispatch_details(self, job_id, dispatch_date, reason, collected_by, phone, sign_blob):
        insert_query = """
            INSERT INTO service_dispatch (job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone, sign)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        insert_params = (job_id, dispatch_date, reason, collected_by, phone, sign_blob)
        update_query = """
            UPDATE service_jobs
            SET status = 'Dispatched'
            WHERE job_id = %s
        """
        update_params = (job_id,)
        return self._execute_transaction((insert_query, insert_params), (update_query, update_params))



    
    def add_job(self, file_id, job_description, title_name, title_number, fee, added_by, brought_by):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = '''
            INSERT INTO service_jobs (file_id, job_description, title_name, title_number, fee, added_by, brought_by, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = (file_id, job_description, title_name, title_number, fee, added_by, brought_by, timestamp)
        return self._execute_query(query, params)

    def update_job_status(self, job_id, new_status):
        """
        Updates only the status of a specific job.
        
        This method uses the more general update_job function, making it
        more specific and easier to use for this particular task.
        
        Args:
            job_id (int): The unique ID of the job.
            new_status (str): The new status for the job (e.g., 'Ongoing', 'Completed').
            
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        new_data = {'status': new_status}
        return self.update_job(job_id, new_data)
    
    def update_job(self, job_id, new_data):
        if not new_data:
            return False
        set_clause = ', '.join([f"{key} = %s" for key in new_data.keys()])
        values = list(new_data.values())
        values.append(job_id)
        query = f'UPDATE service_jobs SET {set_clause} WHERE job_id = %s'
        return self._execute_query(query, tuple(values))
    
    def get_jobs_by_file_id(self, file_id):
        query = "SELECT * FROM service_jobs WHERE file_id = %s"
        return self._execute_query(query, (file_id,), fetch_all=True)



    
    def get_completed_jobs(self):
        query = """
            SELECT 
                sj.job_id,
                sj.timestamp,
                sj.job_description,
                sj.title_name,
                sj.title_number,
                cf.file_name,
                sc.name AS client_name,
                sj.status
            FROM 
                service_jobs sj
            JOIN 
                client_files cf ON sj.file_id = cf.file_id
            JOIN 
                service_clients sc ON cf.client_id = sc.client_id
            WHERE 
                sj.status = 'Completed'
        """
        return self._execute_query(query, fetch_all=True)
    
    def get_service_client_by_id(self, client_id):
        query = 'SELECT * FROM service_clients WHERE client_id = %s'
        return self._execute_query(query, (client_id,), fetch_one=True)
    def get_all_service_clients(self):
        query = 'SELECT client_id, name, telephone_number, email FROM service_clients ORDER BY name'
        clients = self._execute_query(query, fetch_all=True)
        return clients
        

    
    def get_survey_job_status_counts(self):
        query = "SELECT status, COUNT(*) AS count FROM service_jobs GROUP BY status"
        results_rows = self._execute_query(query, fetch_all=True)
        return {row['status']: row['count'] for row in results_rows} if results_rows else {}

    def add_activity_log(self, user_id, action_type, details=None):
        """ Logs a user activity. """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = "INSERT INTO activity_logs (timestamp, user_id, action_type, details) VALUES (%s, %s, %s, %s)"
        self._execute_query(query, (timestamp, user_id, action_type, details))
            
    def get_activity_logs(self, limit=100, offset=0, user_id=None, action_type=None, start_date=None, end_date=None):
        """
        Retrieves a list of activity logs with optional filters,
        joining with the users table to get the username.
        Returns: A list of dictionaries, each representing an activity log.
        """
        query = """
        SELECT
            l.log_id,
            l.timestamp,
            l.action_type,
            l.details,
            u.username
        FROM
            activity_logs l
        LEFT JOIN
            users u ON l.user_id = u.user_id
        WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND l.user_id = %s"
            params.append(user_id)
        if action_type:
            query += " AND l.action_type = %s"
            params.append(action_type)
        if start_date:
            query += " AND l.timestamp >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND l.timestamp <= %s"
            params.append(f"{end_date} 23:59:59")

        query += " ORDER BY l.timestamp DESC"

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)

        return self._execute_query(query, tuple(params), fetch_all=True)
    
    def get_dispatch_records(self, filters=None):
        """
        Fetches dispatch records from the database, joining with service_jobs to get job details.
        Applies filters if they are provided.
        Returns: A list of dictionaries, each representing a dispatch record.
        """
        query = """
            SELECT
                sd.job_id,
                sd.dispatch_date,
                sj.title_name,
                sj.title_number,
                sj.job_description,
                sd.collected_by,
                sd.collector_phone,
                sd.reason_for_dispatch,
                sd.sign
            FROM
                service_dispatch AS sd
            INNER JOIN
                service_jobs AS sj ON sd.job_id = sj.job_id
            WHERE 1=1
        """
        params = []
        
        if filters:
            if 'from_date' in filters and filters['from_date']:
                query += " AND DATE(sd.dispatch_date) >= %s"
                params.append(filters['from_date'])
            if 'to_date' in filters and filters['to_date']:
                query += " AND DATE(sd.dispatch_date) <= %s"
                params.append(filters['to_date'])
            if 'title_number' in filters and filters['title_number']:
                query += " AND sj.title_number LIKE %s"
                params.append(f"%{filters['title_number']}%")
            if 'collected_by' in filters and filters['collected_by']:
                query += " AND sd.collected_by LIKE %s"
                params.append(f"%{filters['collected_by']}%")
                
        return self._execute_query(query, params=params, fetch_all=True)

    def get_signature_by_job_id(self, job_id):
        """
        Retrieves the signature BLOB for a given job ID.
        Returns: A dictionary with the signature data, or None.
        """
        query = "SELECT sign FROM service_dispatch WHERE job_id = %s"
        params = (job_id,)
        return self._execute_query(query, params=params, fetch_one=True)
    
    def create_payment_plan(self, plan_data):
        sql = """
        INSERT INTO payment_plans (name, deposit_percentage, duration_months, interest_rate, created_by)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (
            plan_data['name'],
            plan_data['deposit_percentage'],
            plan_data['duration_months'],
            plan_data['interest_rate'],
            plan_data['created_by']
        )
        return self._execute_query(sql, params)
    
    def get_payment_plans(self):
        sql = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans;"
        return self._execute_query(sql, fetch_all=True)
    
    def get_plan_by_id(self, plan_id):
        sql = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans WHERE plan_id = %s;"
        return self._execute_query(sql, (plan_id,), fetch_one=True)

    def update_payment_plan(self, plan_id, plan_data):
        sql = """
        UPDATE payment_plans
        SET name = %s, deposit_percentage = %s, duration_months = %s, interest_rate = %s
        WHERE plan_id = %s
        """
        params = (
            plan_data.get('name'),
            plan_data.get('deposit_percentage'),
            plan_data.get('duration_months'),
            plan_data.get('interest_rate'),
            plan_id
        )
        return self._execute_query(sql, params)
    
    def delete_payment_plan(self, plan_id):
        sql = "DELETE FROM payment_plans WHERE plan_id = %s"
        return self._execute_query(sql, (plan_id,))
    def add_daily_client(self, client_id, purpose, brought_by, user_id):
        """Adds a new daily client entry for an existing client."""
        query = "INSERT INTO daily_clients (client_id, purpose, brought_by, added_by_user_id) VALUES (%s, %s, %s, %s)"
        params = (client_id, purpose, brought_by, user_id)
        
        visit_id = self._execute_query(query, params)
        if visit_id:
            self.log_activity('Add Daily Visit', f'Added daily visit for client ID: {client_id}', user_id)
            return visit_id
        else:
            messagebox.showerror("Error", "Failed to add daily visit details.")
            return None

    def get_daily_clients(self, start_date=None, end_date=None, purpose=None):
        """
        Retrieves daily client details with optional date filters and purpose,
        joining with the clients table.
        """
        query = """
        SELECT
            dc.visit_id,
            c.name,
            c.telephone_number,
            c.email,
            dc.purpose,
            dc.brought_by,
            dc.timestamp
        FROM daily_clients dc
        JOIN clients c ON dc.client_id = c.client_id
        WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND dc.timestamp >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND dc.timestamp <= %s"
            params.append(f"{end_date} 23:59:59")
        if purpose:
            query += " AND dc.purpose = %s"
            params.append(purpose)
        
        query += " ORDER BY dc.timestamp DESC"
        
        return self._execute_query(query, params, fetch_all=True) or []
    
    def log_activity(self, action_type, details, user_id):
        """
        Logs a user action in the activity_logs table.
        """
        query = "INSERT INTO activity_logs (timestamp, user_id, action_type, details) VALUES (%s, %s, %s, %s)"
        params = (datetime.now(), user_id, action_type, details)
        self._execute_query(query, params)

    def get_all_daily_clients_survey(self):
        """
        Retrieves all daily client visits for the current day with a purpose of 'survey'.
        """
        today = datetime.now().date()
        return self.get_daily_clients(start_date=today, end_date=today, purpose='survey')
    
    def get_all_daily_clients_lands(self):
        """
        Retrieves all daily client visits for the current day with a purpose of 'land sales'.
        """
        today = datetime.now().date()
        return self.get_daily_clients(start_date=today, end_date=today, purpose='land sales')


    def get_service_sales_summary(self, period="daily", start_date=None, end_date=None):
        """
        Get total gross and net service sales from service_payments.
        - period: "daily", "monthly", or "custom"
        - start_date / end_date: required if period="custom"
        Returns: list of dicts with {date, total_gross, total_net}
        """
        query = ""
        params = []

        if period == "daily":
            query = """
                SELECT DATE(payment_date) AS date,
                    SUM(fee) AS total_gross,
                    SUM(amount) AS total_net
                FROM service_payments
                GROUP BY DATE(payment_date)
                ORDER BY DATE(payment_date) DESC
            """
        elif period == "monthly":
            query = """
                SELECT DATE_FORMAT(payment_date, '%%Y-%%m') AS date,
                    SUM(fee) AS total_gross,
                    SUM(amount) AS total_net
                FROM service_payments
                GROUP BY DATE_FORMAT(payment_date, '%%Y-%%m')
                ORDER BY DATE_FORMAT(payment_date, '%%Y-%%m') DESC
            """
        elif period == "custom" and start_date and end_date:
            query = """
                SELECT DATE(payment_date) AS date,
                    SUM(fee) AS total_gross,
                    SUM(amount) AS total_net
                FROM service_payments
                WHERE payment_date BETWEEN %s AND %s
                GROUP BY DATE(payment_date)
                ORDER BY DATE(payment_date) DESC
            """
            params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
        else:
            raise ValueError("Invalid period. Use 'daily', 'monthly', or 'custom' with start_date & end_date.")

        return self._execute_query(query, tuple(params), fetch_all=True)

    def get_service_jobs_for_report(self, start_date=None, end_date=None, status=None):
        """
        Retrieves service jobs along with their payment details for reporting.
        Can filter by date range (payment_date) and job status.
        
        Returns: A list of dictionaries with job and payment details.
        """
        query = """
        SELECT
            sj.job_id,
            sj.job_description,
            sj.title_name,
            sj.title_number,
            sj.fee AS job_fee,
            sj.status AS job_status,
            sj.timestamp AS job_created,
            sp.payment_id,
            sp.amount AS amount_paid,
            sp.balance,
            sp.fee AS agreed_fee,
            sp.payment_date,
            sp.status AS payment_status
        FROM service_jobs sj
        LEFT JOIN service_payments sp ON sj.job_id = sp.job_id
        WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND DATE(sp.payment_date) >= %s"
            params.append(start_date)

        if end_date:
            query += " AND DATE(sp.payment_date) <= %s"
            params.append(end_date)

        if status:
            query += " AND sj.status = %s"
            params.append(status)

        query += " ORDER BY sp.payment_date DESC"

        return self._execute_query(query, tuple(params), fetch_all=True)
