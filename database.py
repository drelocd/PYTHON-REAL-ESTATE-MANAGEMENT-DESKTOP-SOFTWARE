import mysql.connector
import os
from datetime import datetime
from tkinter import messagebox
import bcrypt

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
                if query.strip().upper().startswith("SELECT"):
                    if fetch_one:
                        return cursor.fetchone()
                    if fetch_all:
                        return cursor.fetchall()
                
                # Commit changes for INSERT, UPDATE, and DELETE
                conn.commit()
                
                # Return last inserted ID for INSERT
                if query.strip().upper().startswith("INSERT"):
                    return cursor.lastrowid
                
                # Return True/False for UPDATE/DELETE success
                if query.strip().upper().startswith(("UPDATE", "DELETE")):
                    return cursor.rowcount > 0
                
                return None
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in _execute_query: {e}")
            return None
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
                    purpose VARCHAR(255) NOT NULL,
                    status VARCHAR(255) NOT NULL DEFAULT 'active',
                    added_by_user_id INT,
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
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
                    brought_by VARCHAR(255) NOT NULL,
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
            self.add_client(name=owner, telephone_number=telephone_number, email=email, purpose='Property Owner', status=client_status, added_by_user_id=added_by_user_id)

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
        purpose = 'Land Sales'

        for prop in existing_properties:
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        client_exists = self.get_client_by_contact_info(telephone_number)
        
        if not client_exists:
            self.add_client(name=owner, telephone_number=telephone_number, email=email, purpose=purpose,  status=client_status, added_by_user_id=added_by_user_id)

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
    def add_client(self, name, telephone_number, email, purpose, status, added_by_user_id=None):
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
                update_query = "UPDATE clients SET name = %s, email = %s, purpose = %s, status = 'active', added_by_user_id = %s WHERE client_id = %s"
                self._execute_query(update_query, (name, email, purpose, added_by_user_id, client_id))
                return client_id
            else:
                print(f"Error: A client with the telephone number {telephone_number} already exists and is active.")
                return None
        else:
            query = "INSERT INTO clients (name, telephone_number, email, purpose, status, added_by_user_id) VALUES (%s, %s, %s, %s, %s, %s)"
            return self._execute_query(query, (name, telephone_number, email, purpose, status, added_by_user_id))

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
            c.purpose,
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
            if key in ['name', 'contact_info']:
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

    def get_all_service_clients(self):
        """
        Retrieves all clients from the database (now only client info, not files).
        """
        # Assuming self._get_connection() is adapted to return a MySQL connection
        conn = self._get_connection() 
        cursor = conn.cursor()
        
        try:
            # The SQL query itself is compatible with MySQL
            query = 'SELECT client_id, name, telephone_number, email FROM service_clients ORDER BY name'
            cursor.execute(query)
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Get column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            
            # Convert results to a list of dictionaries
            clients = [dict(zip(columns, row)) for row in rows]
            
            return clients
            
        except Exception as e: # Catch a general exception or a specific MySQL error
            print(f"Database error: {e}")
            return []
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_all_client_files(self):
        """ Retrieves all client files from the database, joining with the service_clients table to include client names and contact info. """
        query = """ SELECT cf.file_id, cf.file_name, sc.name AS client_name, sc.telephone_number AS telephone_number FROM client_files cf JOIN service_clients sc ON cf.client_id = sc.client_id ORDER BY sc.name """
        return self._execute_query(query, fetch_all=True)

    def get_file_by_id(self, file_id):
        """
        Retrieves a single client file from the database by its ID.
        
        Args:
            file_id (int): The ID of the file to retrieve.
        """
        conn = self._get_connection()
        if conn is None:
            return None

        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM client_files WHERE file_id = %s"
        
        try:
            cursor.execute(query, (file_id,))
            file_data = cursor.fetchone()
            return file_data
        except mysql.connector.Error as err:
            print(f"Database query error: {err}")
            return None
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    def get_service_client_by_id(self, client_id):
        """
        Retrieves a single client from the database by their ID.

        Args:
            client_id (int): The ID of the client to retrieve.
        """
        conn = self._get_connection()
        if conn is None:
            return None
        
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM service_clients WHERE client_id = %s"
        
        try:
            cursor.execute(query, (client_id,))
            client_data = cursor.fetchone()
            return client_data
        except mysql.connector.Error as err:
            print(f"Database query error: {err}")
            return None
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
    
    def update_service_client(self, client_id, new_data):
        """
        Updates a client's information in the database.

        Args:
            client_id (int): The ID of the client to update.
            new_data (dict): A dictionary of key-value pairs representing the
                             columns and new values to set.
        """
        conn = self._get_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        
        set_clause = ', '.join([f"{key} = %s" for key in new_data.keys()])
        query = f'UPDATE service_clients SET {set_clause} WHERE client_id = %s'
        
        values = list(new_data.values())
        values.append(client_id)

        try:
            cursor.execute(query, tuple(values))
            conn.commit()
            return cursor.rowcount > 0
        except mysql.connector.Error as err:
            print(f"Database update error: {err}")
            conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
    
    def delete_service_client(self, client_id):
        """
        Deletes a client and all associated files, jobs, and payments.
        Uses a transaction to ensure all deletions are successful or none are.
        """
        conn = self._get_connection()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Note: MySQL's default is to have foreign keys enabled.
            # If your table schemas are set up with ON DELETE CASCADE,
            # a single DELETE FROM service_clients will be sufficient.
            # The manual approach below is safer if not, or to be explicit.
            
            # Delete payments associated with the client's jobs
            query_payments = """
                DELETE FROM service_payments WHERE job_id IN (
                    SELECT job_id FROM service_jobs WHERE file_id IN (
                        SELECT file_id FROM client_files WHERE client_id = %s
                    )
                )
            """
            cursor.execute(query_payments, (client_id,))
            
            # Delete jobs associated with the client's files
            query_jobs = """
                DELETE FROM service_jobs WHERE file_id IN (
                    SELECT file_id FROM client_files WHERE client_id = %s
                )
            """
            cursor.execute(query_jobs, (client_id,))
            
            # Delete client files
            query_files = "DELETE FROM client_files WHERE client_id = %s"
            cursor.execute(query_files, (client_id,))
            
            # Finally, delete the client
            query_client = "DELETE FROM service_clients WHERE client_id = %s"
            cursor.execute(query_client, (client_id,))
            
            conn.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Database deletion error: {err}")
            conn.rollback()
            return False
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
    
    def get_client_file_details(self, file_id):
        """ Retrieves a single client file's details. """
        query = "SELECT * FROM client_files WHERE file_id = %s"
        return self._execute_query(query, (file_id,), fetch_one=True)

    # --- CRUD for Service Jobs ---

    def add_job(self, file_id, job_description, title_name, title_number, fee, added_by, brought_by):
        """
        Adds a new job for a specific file. This method now takes 'file_id'
        instead of 'client_id'.
        """
        conn = self._get_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            query = """
                INSERT INTO service_jobs (file_id, job_description, title_name, title_number, fee, added_by, brought_by, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (file_id, job_description, title_name, title_number, fee, added_by, brought_by, timestamp)
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"Database insertion error: {err}")
            conn.rollback()
            return None
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
    
    def get_all_jobs(self):
        """
        Retrieves all jobs, joining with the client_files and service_clients
        tables to include client and file information.
        """
        conn = self._get_connection()
        if conn is None:
            return []
        
        cursor = conn.cursor(dictionary=True)
        
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
        
        try:
            cursor.execute(query)
            jobs = cursor.fetchall()
            return jobs
        except mysql.connector.Error as err:
            print(f"Database query error: {err}")
            return []
        finally:
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    def get_jobs_by_file_id(self, file_id):
        """
        Retrieves all jobs for a specific client file. This method replaces
        the old get_jobs_by_client_id.
        """
        conn = self._get_connection() # Assuming this method correctly establishes a MySQL connection
        cursor = conn.cursor()
        try:
            # Use %s as the placeholder for MySQL
            cursor.execute('SELECT * FROM service_jobs WHERE file_id = %s', (file_id,))
            
            # Fetch column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            
            # Construct a list of dictionaries, mapping column names to row values
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return jobs
        finally:
            conn.close()

    def get_job_details(self, job_id):
        """
        Fetches detailed information for a single job, including client and file info.
        This method now matches the requested format for MySQL.
        """
        conn = self._get_connection()  # Assuming this method returns a MySQL connection object
        cursor = conn.cursor()
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
        try:
            # Use %s as the placeholder for MySQL
            cursor.execute(query, (job_id,))
            row = cursor.fetchone()
            if row:
                # Fetch column names from cursor description
                columns = [desc[0] for desc in cursor.description]
                # Create a dictionary from column names and row data
                return dict(zip(columns, row))
            return None
        # Catch MySQL-specific errors
        except mysql.connector.Error as e:
            print(f"Error fetching job details for ID {job_id}: {e}")
            return None
        finally:
            # Ensure the connection is closed
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def update_job(self, job_id, new_data):
        """Updates a job's information."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Dynamically build the SET clause for the UPDATE statement
            set_clauses = []
            values = []
            for key, value in new_data.items():
                set_clauses.append(f"{key} = %s") # MySQL uses %s for placeholders
                values.append(value)

            set_clause = ', '.join(set_clauses)
            values.append(job_id) # Add job_id for the WHERE clause

            query = f"UPDATE service_jobs SET {set_clause} WHERE job_id = %s" # MySQL uses %s
            cursor.execute(query, tuple(values)) # Pass values as a tuple
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e: # It's good practice to catch specific exceptions if possible
            print(f"Error updating job {job_id}: {e}")
            conn.rollback() # Rollback changes if an error occurs
            return False
        finally:
            conn.close()
    
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

    def delete_job(self, job_id):
        """Deletes a job and its associated payments."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # In MySQL, foreign key constraints are typically handled at the database level
            # and don't require explicit PRAGMA commands like in SQLite.
            # If you have ON DELETE CASCADE set up for your foreign keys,
            # deleting the job will automatically delete associated payments.
            # Otherwise, you might need to delete from service_payments first.

            # Example assuming ON DELETE CASCADE is configured for service_payments.job_id
            cursor.execute('DELETE FROM service_jobs WHERE job_id = %s', (job_id,))

            # If ON DELETE CASCADE is NOT configured, uncomment the following lines:
            # cursor.execute('DELETE FROM service_payments WHERE job_id = %s', (job_id,))
            # cursor.execute('DELETE FROM service_jobs WHERE job_id = %s', (job_id,))

            conn.commit()
            # Check if any rows were affected by the delete operation
            return cursor.rowcount > 0
        except mysql.connector.Error as e:
            print(f"An error occurred: {e}")
            conn.rollback() # Rollback changes if an error occurs
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_completed_jobs(self):
        """
        Retrieves all service jobs from the database that have a 'Completed' status.
        The result includes the file name and client name by joining tables.
        
        Returns:
            list: A list of dictionaries, where each dictionary represents a 'Completed' job.
                Returns an empty list on failure.
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()  # Assumes this method returns a mysql.connector.connection_pooling.PooledMySQLConnection
            cursor = conn.cursor(dictionary=True) # Use dictionary=True to get results as dictionaries

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
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except mysql.connector.Error as e:
            print(f"An error occurred while fetching data: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_dispatched_jobs(self):
        """
        Fetches all records from the dispatch table.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        query = """
        SELECT dispatch_id, job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone
        FROM service_dispatch
        ORDER BY dispatch_date DESC
        """
        try:
            cursor.execute(query)
            # Fetch column names from cursor description
            columns = [desc[0] for desc in cursor.description]
            # Use a list comprehension to convert rows to dictionaries
            dispatched_jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return dispatched_jobs
        except mysql.connector.Error as e:
            print(f"Error fetching dispatch records: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def save_dispatch_details(self, job_id, dispatch_date, reason, collected_by, phone, sign_blob):
        """
        Inserts new dispatch details into the service_dispatch table and updates job status.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO service_dispatch (job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone, sign)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        update_query = """
        UPDATE service_jobs
        SET status = 'Dispatched'
        WHERE job_id = %s
        """
        try:
            cursor.execute(insert_query, (job_id, dispatch_date, reason, collected_by, phone, sign_blob))
            cursor.execute(update_query, (job_id,))
            conn.commit()
            return True
        except mysql.connector.Error as e: # Assuming you are using mysql.connector
            print(f"Error saving dispatch details: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # --- CRUD for Service Payments ---

    def add_payment(self, job_id, amount, fee, balance):
        """Records a new payment for a job and updates the job's balance."""
        conn = self._get_connection()  # Assuming this method returns a MySQL connection
        cursor = conn.cursor()
        payment_date = datetime.now().strftime('%Y-%m-%d')
        try:
            # For MySQL, the placeholder is %s, not ?
            insert_query = """
                INSERT INTO service_payments (job_id, amount, fee, balance, payment_date)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (job_id, amount, fee, balance, payment_date))
            conn.commit()
            # For MySQL, use cursor.lastrowid to get the ID of the last inserted row
            return cursor.lastrowid
        except mysql.connector.Error as e:
            print(f"An error occurred: {e}")
            conn.rollback() # Rollback changes if an error occurs
            return None
        finally:
            cursor.close()
            conn.close()
        
    def get_payments_by_job_id(self, job_id):
        """Retrieves all payments for a specific job."""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM service_payments WHERE job_id = %s', (job_id,))
            columns = [desc[0] for desc in cursor.description]
            payments = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return payments
        except mysql.connector.Error as err:
            print(f"Error fetching payments for job ID {job_id}: {err}")
            return [] # Return empty list on error
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_all_payments(self):
        """
        Retrieves all payments with detailed information from related tables.
        Returns a list of dictionaries.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)  # Use dictionary=True for dictionary results
        try:
            query = """
                SELECT
                    sp.payment_id,
                    sc.name AS client_name,
                    cf.file_name,
                    sj.job_description,
                    sj.title_number,
                    sp.amount,
                    sp.status AS payment_status,
                    sp.payment_type,
                    sp.payment_date
                FROM service_payments AS sp
                JOIN service_jobs AS sj ON sp.job_id = sj.job_id
                JOIN client_files AS cf ON sj.file_id = cf.file_id
                JOIN service_clients AS sc ON cf.client_id = sc.client_id
                ORDER BY sp.payment_date DESC;
            """
            cursor.execute(query)
            return cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error fetching payments: {e}")
            return []
        finally:
            conn.close()

    def get_filtered_payments(self, filters, page=1, page_size=20):
        """
        Retrieves a filtered and paginated list of payments from a MySQL database.

        Args:
            filters (dict): Dictionary of filters (e.g., 'status', 'client_name').
            page (int): The current page number (1-based).
            page_size (int): The number of items per page.

        Returns:
            tuple: A tuple containing a list of payment records (as dictionaries)
                and the total count of matching records.
                Returns ([], 0) on error.
        """
        conn = self._get_connection()  # Assumes this method returns a MySQL connection
        if not conn:
            return [], 0

        try:
            base_query_part = """
            FROM service_payments AS sp
            JOIN service_jobs AS sj ON sp.job_id = sj.job_id
            JOIN client_files AS cf ON sj.file_id = cf.file_id
            JOIN service_clients AS sc ON cf.client_id = sc.client_id
            """

            conditions = []
            params = []

            # Add filtering conditions dynamically
            if 'status' in filters and filters['status'] != 'All':
                conditions.append("sp.status = %(status)s")
                params.append({'status': filters['status']})

            if 'payment_mode' in filters and filters['payment_mode']:
                conditions.append("sp.payment_type = %(payment_mode)s")
                params.append({'payment_mode': filters['payment_mode']})

            if 'client_name' in filters and filters['client_name']:
                conditions.append("sc.name LIKE %(client_name)s")
                params.append({'client_name': f"%{filters['client_name']}%"})

            if 'file_name' in filters and filters['file_name']:
                conditions.append("cf.file_name LIKE %(file_name)s")
                params.append({'file_name': f"%{filters['file_name']}%"})

            if 'title_number' in filters and filters['title_number']:
                conditions.append("sj.title_number LIKE %(title_number)s")
                params.append({'title_number': f"%{filters['title_number']}%"})

            if 'from_date' in filters and filters['to_date']:
                conditions.append("sp.payment_date BETWEEN %(from_date)s AND %(to_date)s")
                params.append({'from_date': filters['from_date'], 'to_date': filters['to_date']})

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            # Prepare parameters for named placeholders
            query_params = {}
            for param_dict in params:
                query_params.update(param_dict)

            # First, get the total count for pagination
            count_query = f"SELECT COUNT(*) {base_query_part}{where_clause}"
            cursor = conn.cursor(dictionary=True) # Use dictionary=True for dict-like rows
            cursor.execute(count_query, query_params)
            total_count = cursor.fetchone()['COUNT(*)']

            # Then, get the paginated data
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
            {base_query_part}{where_clause}
            ORDER BY sp.payment_date DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """
            offset = (page - 1) * page_size
            query_params['limit'] = page_size
            query_params['offset'] = offset

            cursor.execute(data_query, query_params)
            payments_rows = cursor.fetchall()

            # Convert fetched rows (dictionaries) to the desired format if needed,
            # but cursor(dictionary=True) already provides dictionaries.
            # If you need a list of dicts, `payments_rows` is already that.

            return payments_rows, total_count

        except mysql.connector.Error as e:
            print(f"Error fetching filtered payments: {e}")
            return [], 0
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def update_payment_record(self, payment_id, new_status, final_payment_amount, payment_type):
        """
        Updates the status, amount, and balance of a specific payment and records the transaction in history.

        Args:
            payment_id (int): The ID of the payment to update.
            new_status (str): The new status ('paid' or 'unpaid').
            final_payment_amount (float): The amount of this specific payment.
            payment_type (str): The method of payment ('cash', 'mpesa', 'bank').

        Returns:
            bool: True on success, False on failure.
        """
        conn = self._get_connection()
        if not conn:
            print("Error: Database connection not established.")
            return False

        try:
            cursor = conn.cursor()

            # Step 1: Fetch current payment details
            cursor.execute("SELECT amount, balance FROM service_payments WHERE payment_id = %s", (payment_id,))
            result = cursor.fetchone()
            if result is None:
                print(f"Error: Payment record with ID {payment_id} not found.")
                return False

            current_amount, current_balance = result
            current_amount = float(current_amount)
            current_balance = float(current_balance)

            # Step 2: Calculate new amounts and update the service_payments table
            # In MySQL, you might directly update the balance based on the payment amount if it represents a new payment towards a total.
            # If 'final_payment_amount' is the new total amount paid for this record, adjust logic accordingly.
            # Assuming final_payment_amount is the amount being *added* in this transaction:
            new_amount = current_amount + final_payment_amount
            new_balance = current_balance - final_payment_amount # Assuming balance decreases with payment

            # Ensure balance does not go below zero if that's a business rule
            if new_balance < 0:
                new_balance = 0 # Or handle as per your application's logic

            update_payment_query = """
            UPDATE service_payments
            SET status = %s, amount = %s, balance = %s
            WHERE payment_id = %s
            """
            cursor.execute(update_payment_query, (new_status, new_amount, new_balance, payment_id))

            # Step 3: Insert a new record into the service_payments_history table
            payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            insert_history_query = """
            INSERT INTO service_payments_history (payment_id, payment_amount, payment_type, payment_date)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_history_query, (payment_id, final_payment_amount, payment_type, payment_date))

            conn.commit() # Commit the transaction
            return True

        except mysql.connector.Error as e:
            print(f"Error during payment update transaction: {e}")
            if conn:
                conn.rollback() # Rollback the transaction on error
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_payment_history(self, payment_id):
        """
        Fetches all payment history records for a given payment ID.

        Args:
            payment_id (int): The ID of the parent payment record.

        Returns:
            list: A list of tuples, where each tuple is a payment history record.
        """
        conn = self._get_connection() # Assuming this method returns a MySQL connection
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            # In MySQL, placeholders are typically '%s' instead of '?'
            cursor.execute(
                "SELECT history_id, payment_amount, payment_type, payment_date "
                "FROM service_payments_history WHERE payment_id = %s ORDER BY payment_date DESC",
                (payment_id,)
            )
            history_records = cursor.fetchall()
            return history_records
        except mysql.connector.Error as e:
            print(f"Error fetching payment history: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def get_total_survey_jobs(self):
        """
        Returns the total count of survey jobs from a MySQL database.

        Returns:
            int: Total number of survey jobs. Returns 0 if an error occurs.
        """
        conn = self._get_connection()
        if not conn:
            return 0

        cursor = conn.cursor()
        try:
            # MySQL uses %s as the placeholder for parameters, not ?
            query = "SELECT COUNT(*) FROM service_jobs"
            cursor.execute(query)
            result_row = cursor.fetchone() # fetchone() is standard across many DB APIs

            # The result_row will be a tuple. The count is the first element.
            return result_row[0] if result_row else 0
        except mysql.connector.Error as e:
            print(f"Error fetching total survey jobs: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_survey_job_status_counts(self):
        """ Returns a dictionary of survey job status counts. """
        conn = self._get_connection()
        if not conn:
            return {}
        try:
            with conn.cursor(dictionary=True) as cursor:
                query = "SELECT status, COUNT(*) FROM service_jobs GROUP BY status"
                cursor.execute(query)
                results_rows = cursor.fetchall()
                return {row['status']: row['COUNT(*)'] for row in results_rows}
        except mysql.connector.Error as err:
            print(f"Database error in get_survey_job_status_counts: {err}")
            return {}
        finally:
            if conn.is_connected():
                conn.close()
    
    ## NEW REPORTING METHODS (FOR SalesReportsForm)

    def get_total_sales_for_date_range(self, start_date, end_date):
        """
        Retrieves total revenue and total properties sold within a specified date range.
        Assumes 'transaction_date' in 'transactions' table is stored as YYYY-MM-DD HH:MM:SS.
        """
        try:
            # In MySQL, DATE() function can be used to extract date part for comparison.
            # We also use DATE_ADD for the end date to include the entire day.
            query = """
                SELECT
                    SUM(t.total_amount_paid + t.balance) AS total_revenue, -- Total sales value (paid + balance)
                    COUNT(DISTINCT t.property_id) AS total_properties_sold
                FROM
                    transactions t
                WHERE
                    DATE(t.transaction_date) BETWEEN %s AND %s
            """
            # MySQL uses %s as placeholders, and date comparison is usually done this way.
            # The execute method in mysql.connector typically handles date formatting.
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
                    t.transaction_date BETWEEN %s AND DATE_ADD(%s, INTERVAL 23 HOUR + 59 MINUTE + 59 SECOND)
                ORDER BY t.transaction_date ASC
            """
            
            # Ensure end_date includes the full day
            end_date_with_time = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            
            # Adjust parameters for the MySQL query
            params = (start_date, end_date_with_time) 
            
            # Assuming _execute_query handles the connection and cursor management
            # and returns results in a dictionary-like format or list of dictionaries.
            # If it returns tuples, you'll need to adapt the conversion below.
            results_rows = self._execute_query(query, params, fetch_all=True)
            
            # Convert results to a list of dictionaries, adding the hardcoded 'property_type'
            detailed_transactions = []
            if results_rows:
                for row in results_rows:
                    transaction_data = dict(row) # Assuming _execute_query returns dict-like rows
                    transaction_data['property_type'] = 'Land'
                    detailed_transactions.append(transaction_data)
            
            return detailed_transactions

        except mysql.connector.Error as err:
            print(f"MySQL Error in get_detailed_sales_transactions_for_date_range: {err}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

    def get_sold_properties_for_date_range_detailed(self, start_date, end_date):
        """
        Retrieves detailed information about properties sold within a specified date range.
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
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
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"Error in get_sold_properties_for_date_range_detailed: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_pending_instalments_for_date_range(self, start_date, end_date):
        """
        Retrieves information about transactions with a balance due within a specified date range.
        The date range applies to the transaction_date.
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor(dictionary=True)
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
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"Error in get_pending_instalments_for_date_range: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
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
        """
        Adds a new agent to the database.

        Args:
            name (str): The name of the new agent.
            added_by (str): The username or ID of the user who added the agent.

        Returns:
            bool: True if the agent was added successfully, False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Check if an agent with the same name already exists
            cursor.execute(
                "SELECT agent_id FROM agents WHERE name = %s",
                (name,)
            )
            existing_agent = cursor.fetchone()
            if existing_agent:
                print("Agent with this name already exists.")
                return False

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                "INSERT INTO agents (name, status, added_by, timestamp) VALUES (%s, %s, %s, %s)",
                (name, 'active', added_by, timestamp)
            )
            conn.commit()
            return True

        except Error as e:
            print(f"Error adding new agent: {e}")
            conn.rollback()
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_agent_by_name(self, agent_name):
        """
        Fetches a single agent record from the 'agents' table by name.

        Args:
            agent_name (str): The name of the agent to fetch.

        Returns:
            dict: A dictionary containing the agent's data if found, otherwise None.
        """
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT agent_id, name, status, added_by, timestamp 
                FROM agents 
                WHERE name = %s
            """
            cursor.execute(query, (agent_name,))
            agent = cursor.fetchone()
            return agent
        except Error as e:
            print(f"Error fetching agent by name '{agent_name}': {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
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
        conn = self._get_connection()
        if not conn:
            return False

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
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error updating agent: {e}")
            conn.rollback()
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def delete_agent(self, agent_id):
        """
        Deletes an agent from the database.

        Args:
            agent_id (int): The ID of the agent to delete.

        Returns:
            bool: True if the agent was deleted, False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            query = "DELETE FROM agents WHERE agent_id = %s"
            cursor.execute(query, (agent_id,))
            conn.commit()
            # Check if any row was affected by the delete operation
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error deleting agent with ID {agent_id}: {e}")
            if conn and conn.is_connected():
                conn.rollback() # Rollback changes if an error occurs
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def check_if_user_is_agent(self, user_id):
        """
        Checks if a user is an agent by looking up their ID in the users table.
        
        Args:
            user_id (int): The ID of the user to check.
            
        Returns:
            bool: True if the user is an agent (is_agent = 1), False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            query = "SELECT is_agent FROM users WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                return True
            return False
            
        except Error as e:
            print(f"Database error checking if user is an agent: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_agent_by_user_id(self, user_id):
        """
        Retrieves an agent's data from the users table by their user ID.
        
        Args:
            user_id (int): The ID of the user to retrieve.
            
        Returns:
            dict or None: A dictionary containing the user's data if they are an agent, 
                        otherwise None.
        """
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM users 
                WHERE user_id = %s AND is_agent = 1
            """
            cursor.execute(query, (user_id,))
            agent_data = cursor.fetchone()
            return agent_data
        except Error as e:
            print(f"Database error fetching agent data for user ID {user_id}: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    ## NEW METHODS FOR PROPOSED LOTS UI ##

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

    def create_payment_plan(self, plan_data):
        """
        Inserts a new payment plan record into the payment_plans table.
        
        Args:
            plan_data (dict): A dictionary containing the details of the new plan,
                            including 'name', 'deposit_percentage', 'duration_months', 
                            'interest_rate', and 'created_by'.
        
        Returns:
            int: The ID of the newly created payment plan, or None if an error occurred.
        """
        sql = """
        INSERT INTO payment_plans (name, deposit_percentage, duration_months, interest_rate, created_by)
        VALUES (%s, %s, %s, %s, %s);
        """
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (
                plan_data['name'],
                plan_data['deposit_percentage'],
                plan_data['duration_months'],
                plan_data['interest_rate'],
                plan_data['created_by']
            ))
            conn.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error creating payment plan: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
    
    def get_payment_plans(self):
        """
        Retrieves all payment plans from the database.
        
        Returns:
            list: A list of dictionaries, where each dictionary represents a plan.
        """
        conn = None
        plans = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True) # Use dictionary=True for dict results
            sql = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans;"
            cursor.execute(sql)
            plans = cursor.fetchall()
            return plans
        except Error as e:
            print(f"Error retrieving payment plans: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_plan_by_id(self, plan_id):
        """
        Fetches a single payment plan from the database using its plan_id.
        
        Returns:
            dict: A dictionary of the plan details, or None if not found.
        """
        conn = None
        plan_data = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT 
                    plan_id, 
                    name, 
                    deposit_percentage, 
                    duration_months, 
                    interest_rate, 
                    created_by 
                FROM 
                    payment_plans 
                WHERE 
                    plan_id = %s;
            """
            cursor.execute(sql, (plan_id,))
            plan_data = cursor.fetchone()
        except Error as e:
            print(f"Database error while fetching plan with ID {plan_id}: {e}")
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
        return plan_data
    
    def update_payment_plan(self, plan_id, plan_data):
        """
        Updates an existing payment plan using the provided format.
        
        Args:
            plan_id (int): The ID of the plan to update.
            plan_data (dict): A dictionary with the new plan details.
                            Can contain 'name', 'deposit_percentage', 'duration_months', or 'interest_rate'.
        """
        conn = self._get_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            
            # Constructing the SET clause dynamically based on provided data
            set_clauses = []
            params = []

            if 'name' in plan_data and plan_data['name'] is not None:
                set_clauses.append("name = %s")
                params.append(plan_data['name'])
            
            if 'deposit_percentage' in plan_data and plan_data['deposit_percentage'] is not None:
                set_clauses.append("deposit_percentage = %s")
                params.append(plan_data['deposit_percentage'])

            if 'duration_months' in plan_data and plan_data['duration_months'] is not None:
                set_clauses.append("duration_months = %s")
                params.append(plan_data['duration_months'])

            if 'interest_rate' in plan_data and plan_data['interest_rate'] is not None:
                set_clauses.append("interest_rate = %s")
                params.append(plan_data['interest_rate'])

            if not set_clauses:
                print("No update data provided for the payment plan.")
                return

            # Add the plan_id to the parameters for the WHERE clause
            params.append(plan_id)

            # Construct the final query
            query = f"UPDATE payment_plans SET {', '.join(set_clauses)} WHERE plan_id = %s"
            
            cursor.execute(query, tuple(params))
            conn.commit()
            print(f"Payment plan with ID {plan_id} updated successfully.")

        except Error as e:
            print(f"Error updating payment plan with ID {plan_id}: {e}")
            conn.rollback() # Rollback changes if an error occurs
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def delete_payment_plan(self, plan_id):
        """
        Deletes a payment plan based on its ID.
        
        Args:
            plan_id (int): The ID of the plan to delete.
        
        Returns:
            bool: True if the plan was deleted successfully, False otherwise.
        """
        conn = self._get_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            query = "DELETE FROM payment_plans WHERE plan_id = %s"
            cursor.execute(query, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"Error deleting payment plan: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def update_block_size(self, block_id, new_size):
        query = '''
            UPDATE properties
            SET size = %s
            WHERE property_id = %s
        '''
        self._execute_query(query, (new_size, block_id))

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

    def get_lots_for_update(self):
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

    def get_client_properties(self, client_id):
        """
        Retrieves properties associated with a specific client.
        This assumes properties are linked to clients via transactions.
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT p.property_id, p.title_deed_number, p.location, p.size, p.price, p.status,
                    t.transaction_date, t.total_amount_paid
                FROM properties p
                JOIN transactions t ON p.property_id = t.property_id
                WHERE t.client_id = %s
                ORDER BY t.transaction_date DESC
            """
            cursor.execute(query, (client_id,))
            rows = cursor.fetchall()
            return rows if rows else []
        except Error as e:
            print(f"Error fetching client properties: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def get_client_survey_jobs(self, client_id):
        """
        Retrieves all survey jobs for a specific client.
        """
        conn = self._get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT job_id, property_location, job_description, fee, amount_paid, balance,
                    deadline, status, created_at
                FROM survey_jobs
                WHERE client_id = %s
                ORDER BY created_at DESC
            """
            cursor.execute(query, (client_id,))
            rows = cursor.fetchall()
            return rows if rows else []
        except Error as e:
            print(f"Error fetching client survey jobs: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_all_propertiesForTransfer_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        """
        Fetches properties from 'properties' and 'propertiesForTransfer' with optional search,
        size filters, status, and pagination, including the username of the user who added them.
        Returns properties ordered by property_id DESC (newest first).
        
        Returns: A list of dictionaries, each representing a property.
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)
            
            query_parts = []
            params = []

            # Query for properties from the 'properties' table
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
            query_parts.append(main_props_query)

            # Query for properties from the 'propertiesForTransfer' table
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
            query_parts.append(transfer_props_query)

            # Combine queries with UNION ALL
            combined_query = " UNION ALL ".join(query_parts)

            # Add WHERE clause and filters
            full_query = f"SELECT * FROM ({combined_query}) AS combined_results WHERE 1=1"
            where_params = []
            
            if search_query:
                full_query += " AND (title_deed_number LIKE %s OR location LIKE %s OR description LIKE %s)"
                where_params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

            if min_size is not None:
                full_query += " AND size >= %s"
                where_params.append(min_size)

            if max_size is not None:
                full_query += " AND size <= %s"
                where_params.append(max_size)
            
            if status:
                full_query += " AND status = %s"
                where_params.append(status)

            full_query += " ORDER BY property_id DESC"
            
            if limit is not None:
                full_query += " LIMIT %s"
                where_params.append(limit)
            
            if offset is not None:
                full_query += " OFFSET %s"
                where_params.append(offset)
                
            cursor.execute(full_query, tuple(where_params))
            results = cursor.fetchall()
            
            return results
        except Error as e:
            print(f"Error fetching properties: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_property_by_source(self, property_id, source_table):
        """
        Fetches a single property from either the 'properties' or 'propertiesForTransfer' table
        based on its property ID and source table.
        """
        conn = self._get_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor(dictionary=True)
            results_row = None
            
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
                cursor.execute(query, (property_id,))
                results_row = cursor.fetchone()
                
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
                cursor.execute(query, (property_id,))
                results_row = cursor.fetchone()
                
            return results_row
            
        except Error as e:
            print(f"Error fetching property: {e}")
            return None
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
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
            # Disable autocommit to manage the transaction manually
            conn.autocommit = False
            cursor = conn.cursor()
            
            # 1. Fetch the name of the new owner from the clients table
            cursor.execute("SELECT name FROM clients WHERE client_id = %s", (to_client_id,))
            new_owner_name = cursor.fetchone()
            
            if new_owner_name:
                new_owner_name = new_owner_name[0]
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

            # Commit the transaction
            conn.commit()
            return True

        except Error as e:
            if conn:
                conn.rollback()
            print(f"Database error during property transfer: {e}")
            return False
        except ValueError as e:
            if conn:
                conn.rollback()
            print(f"Error: {e}")
            return False
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_service_jobs_for_report(self, start_date, end_date, status=None):
        """
        Retrieves service jobs for a specified date range and optional status.

        Args:
            start_date (str): The start date of the report range in 'YYYY-MM-DD' format.
            end_date (str): The end date of the report range in 'YYYY-MM-DD' format.
            status (str, optional): The status to filter by (e.g., 'Completed'). Defaults to None.

        Returns:
            list: A list of dictionaries, where each dictionary represents a service job
                record. Returns an empty list on error.
        """
        conn = self._get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM service_jobs
                WHERE completion_date BETWEEN %s AND %s
            """
            params = [start_date, end_date]
            if status:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY completion_date"
            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            return results
        except Error as e:
            print(f"Database error retrieving service jobs for report: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    ##Activity Log##

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
    
    def get_all_users_for_log_viewer(self):
        """
        Retrieves a list of usernames to populate the user filter.
        Returns: A list of usernames.
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT username FROM users ORDER BY username ASC"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [row['username'] for row in rows] if rows else []
        except Error as e:
            print(f"Error fetching users for log viewer: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_all_action_types(self):
        """
        Retrieves a list of unique action types from the activity logs to populate the filter.
        Returns: A list of unique action type strings.
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT DISTINCT action_type FROM activity_logs ORDER BY action_type ASC"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [row['action_type'] for row in rows] if rows else []
        except Error as e:
            print(f"Error fetching action types: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_total_activity_logs_count(self, user_id=None, action_type=None, start_date=None, end_date=None):
        """
        Returns the total count of activity logs, with optional filters.
        """
        conn = self._get_connection()
        if not conn:
            return 0
        
        try:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM activity_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            if action_type:
                query += " AND action_type = %s"
                params.append(action_type)
            if start_date:
                query += " AND timestamp >= %s"
                params.append(f"{start_date} 00:00:00")
            if end_date:
                query += " AND timestamp <= %s"
                params.append(f"{end_date} 23:59:59")
                
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            
            return result[0] if result else 0
        except Error as e:
            print(f"Error fetching activity log count: {e}")
            return 0
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_activity_logs_paginated(self, user_id=None, action_type=None, start_date=None, end_date=None,
                                limit=None, offset=None):
        """
        Fetches a paginated list of activity logs with optional filters,
        joining with the users table to get the username.
        Returns: A list of dictionaries, each representing an activity log.
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
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

            cursor.execute(query, tuple(params))
            results = cursor.fetchall()
            
            return results
        except Error as e:
            print(f"Error fetching paginated activity logs: {e}")
            return []
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()
    
    
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

    def add_service_payment(self, job_id, fee, amount, balance, payment_date):
        """ Adds a new service payment record. """
        query = '''
            INSERT INTO service_payments (job_id, fee, amount, balance, payment_date)
            VALUES (%s, %s, %s, %s, %s)
        '''
        return self._execute_query(query, (job_id, fee, amount, balance, payment_date))

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
    

          
     

    