import sqlite3
import os
from datetime import datetime, timedelta
from tkinter import messagebox

import bcrypt

# Define the path for the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'real_estate.db')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')


class DatabaseManager:
    """
    Manages all interactions with the SQLite database for the Real Estate Management System.
    """
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self._create_data_directory()
        self._create_tables() 

    def _create_data_directory(self):
        """Ensures the 'data' directory exists."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"Created data directory: {DATA_DIR}")

        if not os.path.exists(REPORTS_DIR):
            os.makedirs(REPORTS_DIR)
            print(f"Created reports directory: {REPORTS_DIR}")

    def _create_tables(self):
        """Initializes the database by creating tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Properties Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS properties (
                        property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        property_type TEXT NOT NULL CHECK(property_type IN ('Block', 'Lot')),
                        title_deed_number TEXT NOT NULL,
                        location TEXT NOT NULL,
                        size REAL NOT NULL,
                        description TEXT,
                        owner TEXT NOT NULL,
                        telephone_number TEXT NOT NULL,
                        email TEXT NOT NULL, -- New column for contact info
                        price REAL NOT NULL,
                        image_paths TEXT,      -- Stores comma-separated paths
                        title_image_paths TEXT, -- Stores comma-separated paths
                        status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available','Unavailable', 'Sold')),
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')
                               
                # 2. PropertiesForTransfer Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS propertiesForTransfer (
                        property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title_deed_number TEXT NOT NULL,
                        location TEXT NOT NULL,
                        size REAL NOT NULL,
                        description TEXT,
                        owner TEXT NOT NULL,
                        telephone_number TEXT NOT NULL,
                        email TEXT NOT NULL, -- New column for contact info
                        image_paths TEXT,      -- Stores comma-separated paths
                        title_image_paths TEXT, -- Stores comma-separated paths
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 3. Clients Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        telephone_number TEXT NOT NULL UNIQUE,
                        email TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 4. Transactions Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        property_id INTEGER NOT NULL,
                        client_id INTEGER NOT NULL,
                        payment_mode TEXT NOT NULL, -- 'Cash', 'Installments'
                        total_amount_paid REAL NOT NULL, -- Total amount paid in this transaction
                        discount REAL DEFAULT 0.0,
                        balance REAL DEFAULT 0.0, -- Remaining balance if 'Installments'
                        transaction_date TEXT NOT NULL, --YYYY-MM-DD HH:MM:SS
                        receipt_path TEXT,
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (property_id) REFERENCES properties(property_id),
                        FOREIGN KEY (client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS proposed_lots (
                        lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        parent_block_id INTEGER NOT NULL,
                        size REAL NOT NULL,
                        location TEXT NOT NULL,
                        surveyor_name TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        title_deed_number TEXT,
                        price TEXT DEFAULT '0.0',
                        status TEXT NOT NULL CHECK(status IN ('Proposed', 'Confirmed', 'Rejected')),
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 6. Property transfer Table 
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS property_transfers (
                        transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        property_id INTEGER NOT NULL,
                        from_client_id INTEGER,
                        to_client_id INTEGER NOT NULL,
                        transfer_price REAL NOT NULL,
                        transfer_date TEXT NOT NULL, -- YYYY-MM-DD
                        executed_by_user_id INTEGER NOT NULL,
                        supervising_agent_id INTEGER,
                        transfer_document_path TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (property_id) REFERENCES properties(property_id),
                        FOREIGN KEY (from_client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (to_client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (executed_by_user_id) REFERENCES users(user_id),
                        FOREIGN KEY (supervising_agent_id) REFERENCES users(user_id)
                    )
                ''')

                # 7. Users Table (No change needed here for new columns, it's the target)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        is_agent TEXT DEFAULT 'no' CHECK(is_agent IN ('yes', 'no')),
                        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin','accountant','property_manager','sales_agent'))
                    )
                ''')
                # 8. Agents Table - New table for agents
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS agents (
                         agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                         name TEXT NOT NULL,
                         status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
                         added_by TEXT NOT NULL,
                         timestamp DATETIME NOT NULL
                     )
                ''')
                # 9. Payment Plan
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS payment_plans (
                                      plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      name TEXT NOT NULL,
                                      deposit_percentage REAL NOT NULL CHECK(deposit_percentage >= 0 AND deposit_percentage <= 100),
                                      duration_months INTEGER NOT NULL,
                                      interest_rate REAL NOT NULL,
                                      created_by TEXT NOT NULL
                                 )
                                 ''')
                # 10. Service Client
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS service_clients (
                                      client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      name TEXT NOT NULL,
                                      telephone_number TEXT NOT NULL UNIQUE,
                                      email TEXT NOT NULL,
                                      brought_by TEXT,
                                      added_by TEXT NOT NULL,
                                      timestamp DATETIME NOT NULL
                                )
                               ''')
                # 11. Client files
                cursor.execute('''
               -- NEW TABLE: Links a specific file (e.g., for a land parcel) to a client.
               -- Each client can have multiple files.
                               CREATE TABLE IF NOT EXISTS client_files (
                                      file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      client_id INTEGER NOT NULL,
                                      file_name TEXT NOT NULL,
                                      added_by TEXT NOT NULL,
                                      timestamp DATETIME NOT NULL,
                                      FOREIGN KEY (client_id) REFERENCES service_clients(client_id)
                             )
                            ''')
                # 12. Job File
                cursor.execute('''
               -- The jobs table now links to a specific file (file_id) instead of the
               -- general client (client_id). This ensures each job is tied to the
               -- correct land project.
                              CREATE TABLE IF NOT EXISTS service_jobs (
                                     job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     file_id INTEGER NOT NULL,
                                     job_description TEXT,
                                     title_name TEXT NOT NULL,
                                     title_number TEXT NOT NULL,
                                     fee REAL NOT NULL,
                                     amount_paid REAL DEFAULT 0.0,
                                     status TEXT NOT NULL DEFAULT 'Ongoing' CHECK(status IN ('Ongoing', 'Completed', 'Dispatched')),
                                     added_by TEXT NOT NULL,
                                     brought_by TEXT NOT NULL,
                                     timestamp DATETIME NOT NULL,
                                     FOREIGN KEY (file_id) REFERENCES client_files(file_id)
                                )
                          ''')
                # 13. Job Payment
                cursor.execute('''
               -- The payments table correctly links to the job_id, which is now
               -- linked to a specific file.
                              CREATE TABLE IF NOT EXISTS service_payments (
                                     payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     job_id INTEGER NOT NULL,
                                     amount REAL NOT NULL,
                                     payment_date TEXT NOT NULL,
                                     payment_type TEXT CHECK (payment_type IN ('cash','bank','mpesa')),
                                     status TEXT DEFAULT 'unpaid' CHECK (status IN ('paid', 'unpaid')),
                                     FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
               )
            ''')
                #14. Service Dispatch
                cursor.execute('''
                             CREATE TABLE IF NOT EXISTS service_dispatch (
                                     dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     job_id INTEGER NOT NULL,
                                     dispatch_date TEXT NOT NULL,
                                     reason_for_dispatch TEXT,
                                     collected_by TEXT,
                                     collector_phone TEXT,
                                     sign BLOB, -- Stores the digital signature file.
                                              -- Note: For large files, it's often better to store a path/URL
                                              -- to a file storage system instead of storing the BLOB directly.
                                     FOREIGN KEY (job_id) REFERENCES service_jobs(job_id)
                )
            ''')

                # 15. Activity Log Table
                cursor.execute('''
                                    CREATE TABLE IF NOT EXISTS activity_logs (
                                        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        timestamp TEXT NOT NULL,
                                        user_id INTEGER NOT NULL,
                                        action_type TEXT NOT NULL,
                                        details TEXT,
                                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                                    )
                                ''')


                conn.commit()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error creating tables: {e}")

    def _get_connection(self):
        """
        Returns a connection object to the database.
        Sets row_factory to sqlite3.Row for dictionary-like access to columns.
        """
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row # Ensures results can be accessed by column name (like dict)
        return conn

    def _execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        """
        A helper method to execute SQL queries.
        Can fetch one, fetch all, or just execute (for INSERT, UPDATE, DELETE).
        Returns sqlite3.Row objects (or lists of them) for SELECT queries.
        Conversion to standard dicts is handled by calling methods if needed.
        """
        try:
            with self._get_connection() as conn: # Use _get_connection for new connection with row_factory
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit() # Commit changes for DML operations

                if fetch_one:
                    return cursor.fetchone() # Returns sqlite3.Row or None
                if fetch_all:
                    return cursor.fetchall() # Returns list of sqlite3.Row or empty list
                
                # For INSERT, return the last row ID
                if query.strip().upper().startswith("INSERT"):
                    return cursor.lastrowid
                
                # For UPDATE/DELETE, check if any rows were affected
                if query.strip().upper().startswith(("UPDATE", "DELETE")):
                    return cursor.rowcount > 0
                
                return None # Default return for other non-fetch operations if no specific return is needed
        except sqlite3.IntegrityError as e:
            print(f"Database Integrity Error: {e}. This usually means a unique value constraint was violated.")
            return None
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in _execute_query: {e}")
            return None

    ## User Management Methods
    def add_user(self, username, password, is_agent='no',role='user'):
        """
        Adds a new user to the database with a hashed password.
        Returns: The ID of the newly added user, or None on error (e.g., duplicate username).
        """
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            query = "INSERT INTO users (username, password_hash, is_agent,role) VALUES (?, ?, ?, ?)"
            return self._execute_query(query, (username, hashed_password, is_agent,role))
        except Exception as e:
            print(f"Error adding user: {e}")
            return None

    def authenticate_user(self, username, password):
        """
        Verifies user credentials for login.
        Returns: The user's data (user_id, username, role) as a dict if valid, None otherwise.
        """
        query = "SELECT user_id, username, password_hash, role FROM users WHERE username = ?"
        user_data_row = self._execute_query(query, (username,), fetch_one=True)

        if user_data_row:
            user_data = dict(user_data_row) # Explicitly convert to dict here
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
        query = "SELECT user_id, username, role FROM users WHERE username = ?"
        user_data_row = self._execute_query(query, (username,), fetch_one=True)
        return dict(user_data_row) if user_data_row else None

    def get_user_by_id(self, user_id):
        """
        Retrieves a user by their ID.
        Returns: The user's data (excluding password_hash) as a dict, or None if not found.
        """
        query = "SELECT user_id, username, role FROM users WHERE user_id = ?"
        user_data_row = self._execute_query(query, (user_id,), fetch_one=True)
        return dict(user_data_row) if user_data_row else None # Explicitly convert to dict

    def update_user_password(self, user_id, new_password):
        """
        Updates a user's password.
        Returns: True if the update was successful, False otherwise.
        """
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE users SET password_hash = ? WHERE user_id = ?"
        return self._execute_query(query, (hashed_password, user_id))

    def update_user_role(self, user_id, new_role):
        """
        Updates a user's role.
        Returns: True if the update was successful, False otherwise.
        """
        if new_role not in ['user', 'admin']:
            print("Invalid role specified. Role must be 'user' or 'admin'.")
            return False
        query = "UPDATE users SET role = ? WHERE user_id = ?"
        return self._execute_query(query, (new_role, user_id))

        # --- NEW METHODS FOR USER MANAGEMENT (ADD THESE) ---
    def get_all_users(self):
            """Retrieves all user records from the database."""
            try:
                rows = self._execute_query("SELECT user_id, username, role FROM users", fetch_all=True)
                if rows:
                    return [{"user_id": row[0], "username": row[1], "role": row[2]} for row in rows]
                return []
            except Exception as e:
                print(f"Error fetching all users: {e}")
                return []

    def update_user(self, user_id, new_username=None, new_password=None, new_role=None):
            """Updates an existing user's details."""
            try:
                query_parts = []
                params = []
                if new_username:
                    query_parts.append("username = ?")
                    params.append(new_username)
                if new_password:
                    query_parts.append("password_hash = ?")
                    params.append(self._hash_password(new_password))
                if new_role:
                    query_parts.append("role = ?")
                    params.append(new_role)

                if not query_parts:
                    return False  # Nothing to update

                query = "UPDATE users SET " + ", ".join(query_parts) + " WHERE user_id = ?"
                params.append(user_id)

                row_count = self._execute_query(query, tuple(params))
                return row_count is not None and row_count > 0
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", f"Username '{new_username}' already exists.")
                return False
            except Exception as e:
                print(f"Error updating user: {e}")
                return False

    def delete_user(self, user_id):
            """Deletes a user from the database."""
            try:
                row_count = self._execute_query("DELETE FROM users WHERE user_id = ?", (user_id,))
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
            # Assumes the 'users' table has a 'user_id' and a 'username' column
            row = self._execute_query(
                "SELECT username FROM users WHERE user_id = ?",
                (user_id,),
                fetch_one=True
            )
            # Return the username directly from the tuple
            if row:
                return row[0]
            return None
        except Exception as e:
            print(f"Error fetching username for user ID '{user_id}': {e}")
            return None


    ## CRUD Operations for Properties

    def get_properties_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM properties WHERE title_deed_number = ?;"
        results_rows = self._execute_query(query, (title_deed_number,), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

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

        # --- Logic to add owner to clients table ---
        # Step 1: Check if the client already exists using their contact info (since it's unique).
        client_exists = self.get_client_by_contact_info(telephone_number)
        client_status = 'active'
        
        # Step 2: If the client doesn't exist, insert them.
        if not client_exists:
            # You must have an 'add_client' method in your class to do this.
            self.add_client(name=owner, contact_info=telephone_number, status=client_status, added_by_user_id=added_by_user_id)

        # Step 3: Insert the property.
        # This part remains the same after the client is handled.
        query = '''INSERT INTO properties (property_type,title_deed_number, location, size, description, owner, telephone_number, email, price, image_paths, title_image_paths, status, added_by_user_id)
                     VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (property_type,title_deed_number, location, size, description, owner, telephone_number, email, price, image_paths, title_image_paths, status, added_by_user_id))


    def get_propertiesfortransfer_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM propertiesForTransfer WHERE title_deed_number = ?;"
        results_rows = self._execute_query(query, (title_deed_number,), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert


    def add_propertyForTransfer(self, title_deed_number, location, size, description, owner, telephone_number, email,  image_paths=None, title_image_paths=None, added_by_user_id=None):
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
        client_exists = self.get_client_by_contact_info(telephone_number)
        
        # Step 2: If the client doesn't exist, insert them.
        if not client_exists:
            # You must have an 'add_client' method in your class to do this.
            self.add_client(name=owner, contact_info=telephone_number, status=client_status, added_by_user_id=added_by_user_id)

        # Step 3: Insert the property.
        # This part remains the same after the client is handled.
        query = '''INSERT INTO propertiesForTransfer (title_deed_number, location, size, description, owner, telephone_number, email, image_paths, title_image_paths,  added_by_user_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (title_deed_number, location, size, description, owner, telephone_number, email, image_paths, title_image_paths, added_by_user_id))
        

    def get_property(self, property_id):
        """
        Retrieves a property by its ID.
        Returns: The property details as a dict, or None if not found.
        """
        query = "SELECT * FROM properties WHERE property_id = ?"
        property_data_row = self._execute_query(query, (property_id,), fetch_one=True)
        return dict(property_data_row) if property_data_row else None # Explicitly convert

    def get_all_properties(self, status=None):
        """
        Retrieves all properties, optionally filtered by status.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert
    
    def get_all_properties_lots(self, status=None,property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        if property_type:
            query += " AND property_type = ?"
            params += (property_type,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []
    
    def get_all_properties_blocks(self, status=None,property_type=None):
        """
        Retrieves all properties, optionally filtered by status and property type.
        Returns: A list of dictionaries representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        if property_type:
            query += " AND property_type = ?"
            params += (property_type,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []

    def update_property(self, property_id, **kwargs):
        """
        Updates details of an existing property.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in ['title_deed_number', 'location', 'size', 'description', 'price', 'image_paths', 'title_image_paths', 'status']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for property update.")
            return False

        params.append(property_id)
        query = f"UPDATE properties SET {', '.join(set_clauses)} WHERE property_id = ?"
        return self._execute_query(query, params)

    def delete_property(self, property_id):
        """
        Deletes a property from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "DELETE FROM properties WHERE property_id = ?"
        return self._execute_query(query, (property_id,))
    
    def get_total_properties(self):
        """
        Returns the total count of properties.
        Returns: Total number of properties.
        """
        query = "SELECT COUNT(*) FROM properties"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0 # No dict conversion needed for single scalar value

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
            query += " AND (p.title_deed_number LIKE ? OR p.location LIKE ? OR p.description LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])
        
        if min_size is not None:
            query += " AND p.size >= ?"
            params.append(min_size)
        
        if max_size is not None:
            query += " AND p.size <= ?"
            params.append(max_size)

        if status: 
            query += " AND p.status = ?"
            params.append(status)

        query += " ORDER BY p.property_id DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)

        results_rows = self._execute_query(query, tuple(params), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert
    



    ## CRUD Operations for Clients

    def add_client(self, name, telephone_number, email, purpose, status, added_by_user_id=None):
        """
        Adds a new client to the database, tracking the user who added them.
        Returns: The ID of the new client, or None on error/duplicate contact_info.
        """
        check_query = "SELECT client_id, status FROM clients WHERE telephone_number = ?"
        existing_client = self._execute_query(check_query, (telephone_number,), fetch_one=True)

        if existing_client:
            client_id, current_status = existing_client
            if current_status == 'inactive':
                update_query = "UPDATE clients SET name = ?, email = ?, purpose = ?, status = 'active', added_by_user_id = ? WHERE client_id = ?"
                self._execute_query(update_query, (name, email, purpose, added_by_user_id, client_id))
                return client_id
            else:
                print(f"Error: A client with the telephone number {telephone_number} already exists and is active.")
                return None
            

        else:
            query = "INSERT INTO clients (name, telephone_number, email, purpose,status, added_by_user_id) VALUES (?, ?, ?, ?, ?, ?)"
            return self._execute_query(query, (name, telephone_number, email, purpose, status, added_by_user_id))


    def get_client(self, client_id):
        """
        Retrieves a client by their ID.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE client_id = ?"
        client_data_row = self._execute_query(query, (client_id,), fetch_one=True)
        return dict(client_data_row) if client_data_row else None # Explicitly convert

    def get_client_by_telephone_number(self, telephone_number):
        """
        Retrieves a client by their contact information.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE telephone_number = ?"
        client_data_row = self._execute_query(query, (telephone_number,), fetch_one=True)
        return dict(client_data_row) if client_data_row else None # Explicitly convert

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
        results_rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []

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
        results_rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []

    def update_client(self, client_id, **kwargs):
        """
        Updates details of an existing client.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        for key, value in kwargs.items():
            if key in ['name', 'contact_info']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for client update.")
            return False

        params.append(client_id)
        query = f"UPDATE clients SET {', '.join(set_clauses)} WHERE client_id = ?"
        return self._execute_query(query, params)

    def delete_client(self, client_id):
        """s
        Deletes a client from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "UPDATE clients SET status = 'inactive' WHERE client_id = ?"
        print(f"Executing query for client ID {client_id}: {query}")
        return self._execute_query(query, (client_id,))

    def get_total_clients(self):
        """
        Returns the total count of clients.
        Returns: Total number of clients.
        """
        query = "SELECT COUNT(*) FROM clients WHERE status = 'active'"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0 # No dict conversion needed for scalar

    def get_client_by_id(self, client_id):
        """
        Retrieves client details by ID, formatted as a dictionary.
        (Duplicate method, kept for consistency, but `get_client` is preferred)
        """
        try:
            query = "SELECT * FROM clients WHERE client_id = ?"
            client_data_row = self._execute_query(query, (client_id,), fetch_one=True)
            return dict(client_data_row) if client_data_row else None # Explicitly convert
        except Exception as e:
            print(f"Error getting client by ID: {e}")
            return None

    ## CRUD Operations for Transactions

    def add_transaction(self, property_id, client_id, payment_mode, total_amount_paid, discount=0.0, balance=0.0, receipt_path=None, added_by_user_id=None):
        """
        Adds a new sales transaction.
        Returns: The ID of the newly added transaction, or None on error.
        """
        transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        query = '''INSERT INTO transactions (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id))

    def get_transaction(self, transaction_id):
        """
        Retrieves a transaction by its ID.
        Returns: The transaction details as a dict, or None if not found.
        """
        query = "SELECT * FROM transactions WHERE transaction_id = ?"
        transaction_data_row = self._execute_query(query, (transaction_id,), fetch_one=True)
        return dict(transaction_data_row) if transaction_data_row else None # Explicitly convert

    def get_transactions_by_property(self, property_id):
        """
        Retrieves all transactions related to a specific property.
        Returns: A list of dictionaries representing transactions.
        """
        query = "SELECT * FROM transactions WHERE property_id = ?"
        results_rows = self._execute_query(query, (property_id,), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert
    
    def get_transactions_by_client(self, client_id):
        """
        Retrieves all transactions related to a specific client.
        Returns: A list of dictionaries representing transactions.
        """
        query = "SELECT * FROM transactions WHERE client_id = ?"
        results_rows = self._execute_query(query, (client_id,), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

    def get_all_transactions(self):
        """
        Retrieves all transactions from the database.
        Returns: A list of dictionaries representing transactions.
        """
        query = "SELECT * FROM transactions"
        results_rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

    def get_total_pending_sales_payments(self):
        """
        Calculates the sum of outstanding balances from property transactions.
        Returns: Total pending amount from sales, or 0.0 if none.
        """
        query = "SELECT SUM(balance) FROM transactions WHERE balance > 0"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row and result_row[0] is not None else 0.0 # No dict conversion needed for scalar

    def update_transaction(self, transaction_id, **kwargs):
        """
        Updates details of an existing transaction.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        allowed_columns = [
            'property_id', 'client_id', 'payment_mode', 'total_amount_paid',
            'discount', 'balance', 'transaction_date', 'receipt_path', 'added_by_user_id' 
        ]

        for key, value in kwargs.items():
            if key in allowed_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            else:
                print(f"Warning: Attempted to update disallowed column: {key}")
        
        if not set_clauses:
            print("No valid columns provided for transaction update.")
            return False

        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(set_clauses)} WHERE transaction_id = ?"
        
        return self._execute_query(query, params)

    def get_transactions_with_details(self, status=None, start_date=None, end_date=None, payment_mode=None, client_name_search=None, property_search=None, client_contact_search=None):
        """
        Retrieves transactions with details from linked properties and clients,
        allowing for various filtering options, including client contact info.
        
        Returns: A list of dictionaries, where each dictionary contains combined
                    transaction, client, and property details.
        """
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
            c.contact_info AS client_contact_info,
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
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")
            
        if payment_mode:
            query += " AND t.payment_mode = ?"
            params.append(payment_mode)
            
        if client_name_search:
            query += " AND c.name LIKE ?"
            params.append(f"%{client_name_search}%")
            
        if property_search:
            query += " AND (p.title_deed_number LIKE ? OR p.location LIKE ?)"
            params.append(f"%{property_search}%")
            params.append(f"%{property_search}%")

        if client_contact_search:
            query += " AND c.contact_info LIKE ?"
            params.append(f"%{client_contact_search}%")
            
        query += " ORDER BY t.transaction_date DESC"

        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

    ## NEW METHODS FOR SOLD PROPERTIES UI

    def get_total_sold_properties_count(self, start_date=None, end_date=None):
        """
        Returns the total count of properties with 'Sold' status, optionally filtered by transaction date.
        Returns: Total number of sold properties matching criteria.
        """
        query = "SELECT COUNT(*) FROM properties p JOIN transactions t ON p.property_id = t.property_id WHERE p.status = 'Sold'"
        params = []

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")
        
        result_row = self._execute_query(query, params, fetch_one=True)
        return result_row[0] if result_row else 0 # No dict conversion for scalar

    def get_sold_properties_paginated(self, limit, offset, start_date=None, end_date=None):
        """
        Retrieves sold properties along with their transaction and client details,
        supporting pagination and date filtering.
        
        Returns: A list of dictionaries, each containing details for a sold property.
        """
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
            c.contact_info AS client_contact_info
        FROM
            properties p
        JOIN
            transactions t ON p.property_id = t.property_id
        JOIN
            clients c ON t.client_id = c.client_id
        WHERE
            p.status = 'Sold'
        """
        params = []

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")
            
        query += """
        ORDER BY
            t.transaction_date DESC, p.title_deed_number ASC
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

    def count_available_properties(self):
        """Returns the count of properties with 'Available' status."""
        query = "SELECT COUNT(*) FROM properties WHERE status = 'Available'"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0


    def add_service_client(self, name, telephone_number, email, brought_by, added_by):
        """
        Adds a new client to the database. The 'file_name' is now handled
        separately in the `client_files` table.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            cursor.execute('''
                INSERT INTO service_clients (name, telephone_number, email, brought_by, added_by, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, telephone_number, email, brought_by, added_by, timestamp))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None # Returns None on duplicate contact
        finally:
            conn.close()

    def add_client_file(self, client_id, file_name, added_by):
        """
        Adds a new file for an existing client.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            cursor.execute('''
                INSERT INTO client_files (client_id, file_name, added_by, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (client_id, file_name, added_by, timestamp))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None # Returns None on duplicate file_name
        finally:
            conn.close()

    def get_all_client_files(self):
        """
        Retrieves all client files from the database, joining with the
        service_clients table to include client names and contact info.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = """
                SELECT
                    cf.file_id,
                    cf.file_name,
                    sc.name AS client_name,
                    sc.telephone_number AS telephone_number
                FROM
                    client_files cf
                JOIN
                    service_clients sc ON cf.client_id = sc.client_id
                ORDER BY
                    sc.name
            """
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            files = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return files
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            conn.close()

    def get_all_service_clients(self):
        """
        Retrieves all clients from the database (now only client info, not files).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT client_id, name, telephone_number, email FROM service_clients ORDER BY name')
        clients = [{'client_id': row[0], 'name': row[1], 'telephone_number': row[2], 'email': row[3]}
                   for row in cursor.fetchall()]
        return clients

    def get_file_by_id(self, file_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
           cursor.execute("SELECT * FROM client_files WHERE file_id = ?", (file_id,))
           file_data = cursor.fetchone()
           if file_data:
               columns = [desc[0] for desc in cursor.description]
               return dict(zip(columns, file_data))
           return None
        finally:
            conn.close()
    
         

    def get_service_client_by_id(self, client_id):
        """Retrieves a single client by their ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM service_clients WHERE client_id = ?', (client_id,))
            client_data = cursor.fetchone()
            if client_data:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, client_data))
            return None
        finally:
            conn.close()

    def update_service_client(self, client_id, new_data):
        """Updates a client's information."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            set_clause = ', '.join([f"{key} = ?" for key in new_data.keys()])
            values = list(new_data.values())
            values.append(client_id)
            cursor.execute(f'UPDATE service_clients SET {set_clause} WHERE client_id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_service_client(self, client_id):
        """Deletes a client and all associated files, jobs, and payments."""
        conn = self._get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Deletes from service_clients will cascade to client_files
            # which will in turn cascade to service_jobs and service_payments
            # if the foreign key constraints are set with ON DELETE CASCADE.
            # A manual approach is safer to ensure all records are deleted.
            
            # Find all file_ids for this client
            file_ids = [row[0] for row in cursor.execute('SELECT file_id FROM client_files WHERE client_id = ?', (client_id,)).fetchall()]
            
            # Delete payments and jobs associated with each file
            for file_id in file_ids:
                job_ids = [row[0] for row in cursor.execute('SELECT job_id FROM service_jobs WHERE file_id = ?', (file_id,)).fetchall()]
                for job_id in job_ids:
                    cursor.execute('DELETE FROM service_payments WHERE job_id = ?', (job_id,))
                cursor.execute('DELETE FROM service_jobs WHERE file_id = ?', (file_id,))
            
            # Delete client files
            cursor.execute('DELETE FROM client_files WHERE client_id = ?', (client_id,))
            
            # Finally, delete the client
            cursor.execute('DELETE FROM service_clients WHERE client_id = ?', (client_id,))
            
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return False
        finally:
            conn.close()

    # --- CRUD for Service Jobs ---

    def add_job(self, file_id, job_description, title_name, title_number, fee, amount_paid, added_by,brought_by):
        """
        Adds a new job for a specific file. This method now takes 'file_id'
        instead of 'client_id'.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            cursor.execute('''
                INSERT INTO service_jobs (file_id, job_description, title_name, title_number,fee, amount_paid, added_by, brought_by, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_id, job_description, title_name, title_number, fee, amount_paid , added_by, brought_by, timestamp))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_all_jobs(self):
        """
        Retrieves all jobs, joining with the client_files and service_clients
        tables to include client and file information.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
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
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jobs
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
        finally:
            conn.close()

    def get_jobs_by_file_id(self, file_id):
        """
        Retrieves all jobs for a specific client file. This method replaces
        the old get_jobs_by_client_id.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM service_jobs WHERE file_id = ?', (file_id,))
            columns = [desc[0] for desc in cursor.description]
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jobs
        finally:
            conn.close()

    def get_job_details(self, job_id):
        """
        Fetches detailed information for a single job, including client and file info.
        This method now matches the requested format.
        """
        conn = self._get_connection()
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
        WHERE sj.job_id = ?
        """
        try:
            cursor.execute(query, (job_id,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
        except sqlite3.Error as e:
            print(f"Error fetching job details for ID {job_id}: {e}")
            return None
        finally:
            conn.close()

    def update_job(self, job_id, new_data):
        """Updates a job's information."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            set_clause = ', '.join([f"{key} = ?" for key in new_data.keys()])
            values = list(new_data.values())
            values.append(job_id)
            cursor.execute(f'UPDATE service_jobs SET {set_clause} WHERE job_id = ?', values)
            conn.commit()
            return cursor.rowcount > 0
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
        cursor.execute("PRAGMA foreign_keys = ON")
        try:
            cursor.execute('DELETE FROM service_payments WHERE job_id = ?', (job_id,))
            cursor.execute('DELETE FROM service_jobs WHERE job_id = ?', (job_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return False
        finally:
            conn.close()

    def get_completed_jobs(self):
        """
        Retrieves all service jobs from the database that have a 'Completed' status.
        The result includes the file name and client name by joining tables.
        
        Returns:
            list: A list of rows (as sqlite3.Row objects), where each row is a 'Completed' job.
                  Returns an empty list on failure.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Query joins the three tables to get all the required information
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
        except sqlite3.Error as e:
            print(f"An error occurred while fetching data: {e}")
            return []
        finally:
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
            # Use a list comprehension to convert rows to dictionaries
            columns = [desc[0] for desc in cursor.description]
            dispatched_jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return dispatched_jobs
        except sqlite3.Error as e:
            print(f"Error fetching dispatch records: {e}")
            return []
        finally:
            conn.close()
    
    def save_dispatch_details(self, job_id, dispatch_date, reason, collected_by, phone, sign_blob):
        """
        Inserts new dispatch details into the service_dispatch table.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO service_dispatch (job_id, dispatch_date, reason_for_dispatch, collected_by, collector_phone, sign)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        update_query = """
        UPDATE service_jobs
        SET status = 'Dispatched'
        WHERE job_id = ?
        """
        try:
            cursor.execute(insert_query, (job_id, dispatch_date, reason, collected_by, phone, sign_blob))
            cursor.execute(update_query, (job_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error saving dispatch details: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    

    # --- CRUD for Service Payments ---

    def add_payment(self, job_id, amount):
        """Records a new payment for a job and updates the job's balance."""
        conn = self._get_connection()
        cursor = conn.cursor()
        payment_date = datetime.now().strftime('%Y-%m-%d')
        try:
            cursor.execute('''
                INSERT INTO service_payments (job_id, amount, payment_date)
                VALUES (?, ?, ?)
            ''', (job_id, amount, payment_date))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            conn.close()

    def get_payments_by_job_id(self, job_id):
        """Retrieves all payments for a specific job."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM service_payments WHERE job_id = ?', (job_id,))
            columns = [desc[0] for desc in cursor.description]
            payments = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return payments
        finally:
            conn.close()

    def get_all_payments(self):
        """
        Retrieves all payments with detailed information from related tables.
        Returns a list of tuples.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
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
        except sqlite3.Error as e:
            print(f"Error fetching payments: {e}")
            return []
        finally:
            conn.close()

    def get_filtered_payments(self, filters, page=1, page_size=20):
        """
        Retrieves a filtered and paginated list of payments.

        Args:
            filters (dict): Dictionary of filters (e.g., 'status', 'client_name').
            page (int): The current page number (1-based).
            page_size (int): The number of items per page.

        Returns:
            tuple: A tuple containing a list of payment records and the total count.
        """
        conn = self._get_connection()
        if not conn:
            return [], 0

        try:
            base_query = """
                FROM service_payments AS sp
                JOIN service_jobs AS sj ON sp.job_id = sj.job_id
                JOIN client_files AS cf ON sj.file_id = cf.file_id
                JOIN service_clients AS sc ON cf.client_id = sc.client_id
            """
            
            conditions = []
            params = []
            
            # Add filtering conditions dynamically
            if 'status' in filters and filters['status'] != 'All':
                conditions.append("sp.status = ?")
                params.append(filters['status'])
                
            if 'payment_mode' in filters and filters['payment_mode']:
                conditions.append("sp.payment_type = ?")
                params.append(filters['payment_mode'])
            
            if 'client_name' in filters and filters['client_name']:
                conditions.append("sc.name LIKE ?")
                params.append(f"%{filters['client_name']}%")

            if 'file_name' in filters and filters['file_name']:
                conditions.append("cf.file_name LIKE ?")
                params.append(f"%{filters['file_name']}%")

            if 'title_number' in filters and filters['title_number']:
                conditions.append("sj.title_number LIKE ?")
                params.append(f"%{filters['title_number']}%")
            
            if 'from_date' in filters and filters['to_date']:
                conditions.append("sp.payment_date BETWEEN ? AND ?")
                params.append(filters['from_date'])
                params.append(filters['to_date'])
                
            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            
            # First, get the total count for pagination
            count_query = f"SELECT COUNT(*) {base_query}{where_clause}"
            cursor = conn.cursor()
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()[0]

            # Then, get the paginated data
            data_query = f"""
                SELECT
                    sp.payment_id,
                    sc.name AS client_name,
                    cf.file_name,
                    sj.job_description,
                    sj.title_number,
                    sp.amount,
                    sp.status,
                    sp.payment_type,
                    sp.payment_date
                {base_query}{where_clause}
                ORDER BY sp.payment_date DESC
                LIMIT ? OFFSET ?;
            """
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
            cursor.execute(data_query, params)
            payments = cursor.fetchall()

            return payments, total_count
        except sqlite3.Error as e:
            print(f"Error fetching filtered payments: {e}")
            return [], 0
        finally:
            conn.close()

    def update_payment_record(self, payment_id, new_status, payment_type):
        """
        Updates the status and payment type of a specific payment.

        Args:
            payment_id (int): The ID of the payment to update.
            new_status (str): The new status ('paid' or 'unpaid').
            payment_type (str): The method of payment ('cash', 'mpesa', 'bank').
        
        Returns:
            bool: True on success, False on failure.
        """
        conn = self._get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE service_payments SET status = ?, payment_type = ? WHERE payment_id = ?",
                (new_status, payment_type, payment_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating payment record: {e}")
            return False
        finally:
            conn.close()






    def get_total_survey_jobs(self):
        """
        Returns the total count of survey jobs.
        Returns: Total number of survey jobs.
        """
        query = "SELECT COUNT(*) FROM service_jobs"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0

    
    

    def get_survey_job_status_counts(self):
        """
        Returns a dictionary of survey job status counts.
        e.g., {'Pending': 5, 'Ongoing': 2, 'Completed': 8, 'Cancelled': 1}
        """
        query = "SELECT status, COUNT(*) FROM service_jobs GROUP BY status"
        results_rows = self._execute_query(query, fetch_all=True)
        return {row[0]: row[1] for row in results_rows} if results_rows else {}

    ## NEW REPORTING METHODS (FOR SalesReportsForm)
    def get_total_sales_for_date_range(self, start_date, end_date):
        """
        Retrieves total revenue and total properties sold within a specified date range.
        Assumes 'transaction_date' in 'transactions' table is stored as Букмекерлар-MM-DD HH:MM:SS.
        """
        try:
            query = """
                SELECT 
                    SUM(t.total_amount_paid + t.balance) AS total_revenue, -- Total sales value (paid + balance)
                    COUNT(DISTINCT t.property_id) AS total_properties_sold
                FROM 
                    transactions t
                WHERE 
                    t.transaction_date BETWEEN ? AND ? || ' 23:59:59'
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
                    t.transaction_date BETWEEN ? AND ? || ' 23:59:59'
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [dict(row) | {'property_type': 'Land'} for row in results_rows] if results_rows else []
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
                    p.status = 'Sold' AND t.transaction_date BETWEEN ? AND ? || ' 23:59:59'
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [dict(row) for row in results_rows] if results_rows else []
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
                    t.balance > 0 AND t.transaction_date BETWEEN ? AND ? || ' 23:59:59'
                ORDER BY t.transaction_date ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [dict(row) for row in results_rows] if results_rows else []
        except Exception as e:
            print(f"Error in get_pending_instalments_for_date_range: {e}")
            return []

    
    def get_all_agents(self):
        """Fetches all agent records from the 'agents' table as a list of dictionaries."""
        try:
            # We'll assume a method like _execute_query exists within the class
            # to handle the connection and cursor, as per your example.
            rows = self._execute_query(
                "SELECT agent_id, name, status, added_by, timestamp FROM agents",
                fetch_all=True
            )
            if rows:
                return [{
                    "agent_id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "added_by": row[3],
                    "timestamp": row[4]
                } for row in rows]
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
        try:
            # Check if an agent with the same name already exists
            existing_agent = self._execute_query(
                "SELECT agent_id FROM agents WHERE name = ?",
                (name,)
            )
            if existing_agent:
                print("Agent with this name already exists.")
                return False

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return self._execute_query(
                "INSERT INTO agents (name, status, added_by, timestamp) VALUES (?, ?, ?, ?)",
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
            tuple: A tuple containing the agent's data if found, otherwise None.
        """
        try:
            # We'll assume a method like _execute_query exists within the class
            # to handle the connection and cursor, as per your example.
            # This query is designed to fetch only a single record.
            row = self._execute_query(
                "SELECT agent_id, name, status, added_by, timestamp FROM agents WHERE name = ?",
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
            updates.append("name = ?")
            params.append(new_name)
        if new_status:
            updates.append("status = ?")
            params.append(new_status)

        if not updates:
            print("No updates provided.")
            return False

        query = f"UPDATE agents SET {', '.join(updates)} WHERE agent_id = ?"
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
                "DELETE FROM agents WHERE agent_id = ?",
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
            bool: True if the user is an agent (is_agent = 1), False otherwise.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT is_agent FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                return True
            return False
            
        except sqlite3.Error as e:
            print(f"Database error checking if user is an agent: {e}")
            return False
        
    def get_agent_by_user_id(self, user_id):
        """
        Retrieves an agent's data from the users table by their user ID.
        
        Args:
            user_id (int): The ID of the user to retrieve.
            
        Returns:
            tuple or None: A tuple containing the user's data if they are an agent, 
                           otherwise None.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ? AND is_agent = 1", (user_id,))
            return cursor.fetchone()
            
        except sqlite3.Error as e:
            print(f"Database error fetching agent data: {e}")
            return None

        
    ############# NEW METHODS FOR PROPOSED LOTS UI ################
        
    def propose_new_lot(self, proposed_lot_data):
        """
        Inserts a new proposed lot record into the proposed_lots table.
        
        Args:
            proposed_lot_data (dict): A dictionary containing the details of the new lot.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Insert the data into the proposed_lots table.
        # Note: The 'created_at' column is handled automatically by the DEFAULT CURRENT_TIMESTAMP.
        cursor.execute('''
            INSERT INTO proposed_lots (parent_block_id, size, location, surveyor_name, created_by, title_deed_number, price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proposed_lot_data['parent_block_id'],
            proposed_lot_data['size'],
            proposed_lot_data['location'],
            proposed_lot_data['surveyor_name'],
            proposed_lot_data['created_by'],
            proposed_lot_data.get('title_deed_number', 'N/A'),
            str(proposed_lot_data.get('price', 0)),
            proposed_lot_data.get('status', 'Proposed')
        ))
        
        conn.commit()
        conn.close()

    def create_payment_plan(self, plan_data):
        """
        Inserts a new payment plan record into the payment_plans table.
        
        Args:
            plan_data (dict): A dictionary containing the details of the new plan,
                              including 'name', 'duration_months', 'interest_rate',
                              and 'created_by'.
        """
        sql = """
        INSERT INTO payment_plans (name, deposit_percentage,duration_months, interest_rate, created_by)
        VALUES (?,?,?, ?, ?);
        """
        conn = self._get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                plan_data['name'],
                plan_data['deposit_percentage'],
                plan_data['duration_months'],
                plan_data['interest_rate'],
                plan_data['created_by']
            ))
            conn.commit()
            conn.close()
            return cursor.lastrowid

    def get_payment_plans(self):
        """
        Retrieves all payment plans from the database.
        
        Returns:
            list: A list of dictionaries, where each dictionary represents a plan.
        """
        sql = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans;"
        conn = self._get_connection()
        plans = []
        if conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Convert list of tuples to list of dictionaries for easier use
            columns = [desc[0] for desc in cursor.description]
            for row in rows:
                plans.append(dict(zip(columns, row)))
            conn.close()
        return plans
    
    def get_plan_by_id(self, plan_id):
        """
        Fetches a single payment plan from the database using its plan_id.
        
        Returns:
            dict: A dictionary of the plan details, or None if not found.
        """
        sql = "SELECT plan_id, name, deposit_percentage, duration_months, interest_rate, created_by FROM payment_plans WHERE plan_id = ?;"
        conn = self._get_connection()
        plan_data = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(sql, (plan_id,))
                row = cursor.fetchone()
                
                if row:
                    # Convert the single tuple row to a dictionary
                    columns = [desc[0] for desc in cursor.description]
                    plan_data = dict(zip(columns, row))
            except sqlite3.Error as e:
                print(f"Database error while fetching plan: {e}")
            finally:
                conn.close()
        return plan_data

    def update_payment_plan(self, plan_id, plan_data):
        """
        Updates an existing payment plan using the provided format.
        
        Args:
            plan_id (int): The ID of the plan to update.
            plan_data (dict): A dictionary with the new plan details.
                              Can contain 'name', 'duration_months', or 'interest_rate'.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE payment_plans
            SET name = ?, deposit_percentage =?,duration_months = ?, interest_rate = ?
            WHERE plan_id = ?
        ''', (
            plan_data.get('name'),
            plan_data.get('deposit_percentage'),
            plan_data.get('duration_months'),
            plan_data.get('interest_rate'),
            plan_id
        ))
        conn.commit()
        conn.close()

    def delete_payment_plan(self, plan_id):
        """
        Deletes a payment plan based on its ID using the new, simple format.
        
        Args:
            plan_id (int): The ID of the plan to delete.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM payment_plans WHERE plan_id = ?
        ''', (plan_id,))
        conn.commit()
        conn.close()


    def update_block_size(self, block_id, new_size):
        """
        Updates the size of a parent block in the properties table.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE properties
            SET size = ?
            WHERE property_id = ?
        ''', (new_size, block_id))
        conn.commit()
        conn.close()

    def get_proposed_lots_with_details(self):
        """
        Retrieves all proposed lots with details from both tables.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
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
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'lot_id': row[1],
                'title_deed_number': row[0],
                'size': row[2],
                'location': row[3],
                'surveyor_name': row[4],
                'created_by': row[5],
                'status': row[6]
            }
            for row in rows
        ]
    
    

    
    def get_lots_for_update(self):
        """
        Retrieves proposed or confirmed lots for potential updates.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT lot_id, title_deed_number, size, status, location
            FROM proposed_lots
            WHERE status IN ('Proposed')
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                'lot_id': row[0],
                'title_deed': row[1],
                'size': row[2],
                'status': row[3],
                'location': row[4]
            }
            for row in rows
        ]

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
        """
        Updates the status of a proposed lot to 'Confirmed'.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE proposed_lots
            SET status = 'Confirmed'
            WHERE lot_id = ?
        ''', (lot_id,))
        conn.commit()
        conn.close()

    def reject_lot(self, lot_id):
        """
        Updates the status of a proposed lot to 'Rejected'.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE proposed_lots
            SET status = 'Rejected'
            WHERE lot_id = ?
        ''', (lot_id,))
        conn.commit()
        conn.close()

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
            cursor = conn.cursor()
            
            # 1. Get current block size and status
            cursor.execute("SELECT size, status FROM properties WHERE property_id = ?", (block_id,))
            result = cursor.fetchone()
            
            if result:
                current_size, current_status = result
                new_size = current_size + size_to_add
                # If the status was unavailable, change it back to available
                new_status = 'Available' if current_status == 'Unavailable' else current_status
                
                # 2. Update the block with the new size and status
                cursor.execute("UPDATE properties SET size = ?, status = ? WHERE property_id = ?", (new_size, new_status, block_id))
                conn.commit()
                print(f"Size {size_to_add} successfully returned to block {block_id}. New size: {new_size}. New status: {new_status}.")
            else:
                print(f"Block with ID {block_id} not found.")

        except sqlite3.Error as e:
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
        conn = None  # Initialize conn to None for proper cleanup
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = "UPDATE properties SET status = ? WHERE property_id = ?"
            cursor.execute(sql, (status, block_id))
            conn.commit()
            print(f"Status for block {block_id} successfully updated to '{status}'.")
        except sqlite3.Error as e:
            print(f"Database error occurred: {e}")
            if conn:
                conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            if conn:
                conn.close()

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
            WHERE t.client_id = ?
            ORDER BY t.transaction_date DESC
        """
        rows = self._execute_query(query, (client_id,), fetch_all=True)
        return [dict(row) for row in rows] if rows else []
    

    def get_client_survey_jobs(self, client_id):
        """
        Retrieves all survey jobs for a specific client.
        """
        query = """
            SELECT job_id, property_location, job_description, fee, amount_paid, balance,
                   deadline, status, created_at
            FROM survey_jobs
            WHERE client_id = ?
            ORDER BY created_at DESC
        """
        rows = self._execute_query(query, (client_id,), fetch_all=True)
        return [dict(row) for row in rows] if rows else []
    
    def get_all_propertiesForTransfer_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        """
        Fetches properties from 'properties' and 'propertiesForTransfer' with optional search,
        size filters, status, and pagination, including the username of the user who added them.
        Returns properties ordered by property_id DESC (newest first).
        Returns: A list of dictionaries, each representing a property.
        """
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
            pt.telephone_number,
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
        if search_query:
            full_query += " AND (title_deed_number LIKE ? OR location LIKE ? OR description LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

        if min_size is not None:
            full_query += " AND size >= ?"
            params.append(min_size)

        if max_size is not None:
            full_query += " AND size <= ?"
            params.append(max_size)
        
        if status:
            # Note: Status filter only applies to properties with a status column
            full_query += " AND status = ?"
            params.append(status)

        full_query += " ORDER BY property_id DESC"
        if limit is not None:
            full_query += " LIMIT ?"
            params.append(limit)
        if offset is not None:
            full_query += " OFFSET ?"
            params.append(offset)
        results_rows = self._execute_query(full_query, tuple(params), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []
    def get_property_by_source(self, property_id, source_table):
        """
        Fetches a single property from either the 'properties' or 'propertiesForTransfer' table
        based on its property ID and source table.
        """
        if source_table == 'Main':
           query = """
           SELECT
               p.property_id, p.title_deed_number, p.location, p.size, p.description,
               p.price, p.telephone_number, p.image_paths, p.title_image_paths, p.status,
               p.added_by_user_id, p.owner, u.username AS added_by_username
           FROM properties p
           LEFT JOIN users u ON p.added_by_user_id = u.user_id
           WHERE p.property_id = ?
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
           WHERE pt.property_id = ?
           """
           results_row = self._execute_query(query, (property_id,), fetch_one=True)
        else:
            results_row = None
    
        return dict(results_row) if results_row else None

    def execute_property_transfer(self, property_id, from_client_id, to_client_id, transfer_price, transfer_date, executed_by_user_id, supervising_agent_id, document_path, source_table):
        """
        Executes a property transfer transaction:
        1. Updates the owner in the correct table (properties or propertiesForTransfer).
        2. Records the transfer details in the property_transfers table.
        
        Returns: True on success, False on failure.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Start a transaction
                cursor.execute("BEGIN TRANSACTION")

                # 1. Fetch the name of the new owner from the clients table
                cursor.execute("SELECT name FROM clients WHERE client_id = ?", (to_client_id,))
                new_owner_name = cursor.fetchone()
                
                if new_owner_name:
                    new_owner_name = new_owner_name[0]
                else:
                    raise ValueError(f"Client with ID {to_client_id} not found.")

                # 2. Update the property owner in the correct source table
                if source_table == 'Main':
                    cursor.execute("UPDATE properties SET owner = ? WHERE property_id = ?", (new_owner_name, property_id))
                elif source_table == 'Transfer':
                    cursor.execute("UPDATE propertiesForTransfer SET owner = ? WHERE property_id = ?", (new_owner_name, property_id))
                else:
                    raise ValueError(f"Invalid source table: {source_table}")

                # 3. Insert a record into the 'property_transfers' table
                transfer_record_query = """
                INSERT INTO property_transfers (
                    property_id, from_client_id, to_client_id, transfer_price,
                    transfer_date, executed_by_user_id, supervising_agent_id,
                    transfer_document_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(transfer_record_query, (
                    property_id, from_client_id, to_client_id, transfer_price,
                    transfer_date, executed_by_user_id, supervising_agent_id,
                    document_path
                ))

                # Commit the transaction
                conn.commit()
                return True

        except Exception as e:
            if 'conn' in locals() and conn:
                conn.rollback()
            print(f"Database error during property transfer: {e}")
            return False

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
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT * FROM service_jobs
                    WHERE completion_date BETWEEN ? AND ?
                """
                params = [start_date, end_date]

                if status:
                    query += " AND status = ?"
                    params.append(status)

                query += " ORDER BY completion_date"

                cursor.execute(query, tuple(params))
                return cursor.fetchall()
        except Exception as e:
            print(f"Database error retrieving service jobs for report: {e}")
            return []

        ## --- NEW METHODS FOR ACTIVITY LOGS ---
    def add_activity_log(self, user_id, action_type, details):
            """
            Logs a user action in the activity_logs table.
            Args:
                user_id (int): The ID of the user performing the action.
                action_type (str): A brief, descriptive type of action (e.g., 'Login', 'Property Added').
                details (str): A more detailed description of the action.
            """
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = "INSERT INTO activity_logs (timestamp, user_id, action_type, details) VALUES (?, ?, ?, ?)"
            self._execute_query(query, (timestamp, user_id, action_type, details))

    def get_activity_logs(self, user_id=None, action_type=None, start_date=None, end_date=None, limit=None,
                          offset=None):
        """
        Retrieves activity logs with optional filters,
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
            query += " AND l.user_id = ?"
            params.append(user_id)
        if action_type:
            query += " AND l.action_type = ?"
            params.append(action_type)
        if start_date:
            query += " AND l.timestamp >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND l.timestamp <= ?"
            params.append(f"{end_date} 23:59:59")

        query += " ORDER BY l.timestamp DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)

        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else []

    def get_all_users_for_log_viewer(self):
            """
            Retrieves a list of usernames to populate the user filter.
            Returns: A list of usernames.
            """
            try:
                rows = self._execute_query("SELECT username FROM users ORDER BY username ASC", fetch_all=True)
                return [row['username'] for row in rows] if rows else []
            except Exception as e:
                print(f"Error fetching users for log viewer: {e}")
                return []

    def get_all_action_types(self):
            """
            Retrieves a list of unique action types from the activity logs to populate the filter.
            Returns: A list of unique action type strings.
            """
            try:
                rows = self._execute_query("SELECT DISTINCT action_type FROM activity_logs ORDER BY action_type ASC",
                                           fetch_all=True)
                return [row['action_type'] for row in rows] if rows else []
            except Exception as e:
                print(f"Error fetching action types: {e}")
                return []

    def get_total_activity_logs_count(self, user_id=None, action_type=None, start_date=None, end_date=None):
            """
            Returns the total count of activity logs, with optional filters.
            """
            query = "SELECT COUNT(*) FROM activity_logs WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if action_type:
                query += " AND action_type = ?"
                params.append(action_type)
            if start_date:
                query += " AND timestamp >= ?"
                params.append(f"{start_date} 00:00:00")
            if end_date:
                query += " AND timestamp <= ?"
                params.append(f"{end_date} 23:59:59")

            result_row = self._execute_query(query, params, fetch_one=True)
            return result_row[0] if result_row else 0

    def get_activity_logs_paginated(self, user_id=None, action_type=None, start_date=None, end_date=None,
                                        limit=None, offset=None):
            """
            Fetches a paginated list of activity logs with optional filters,
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
                query += " AND l.user_id = ?"
                params.append(user_id)
            if action_type:
                query += " AND l.action_type = ?"
                params.append(action_type)
            if start_date:
                query += " AND l.timestamp >= ?"
                params.append(f"{start_date} 00:00:00")
            if end_date:
                query += " AND l.timestamp <= ?"
                params.append(f"{end_date} 23:59:59")

            query += " ORDER BY l.timestamp DESC"

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

            results_rows = self._execute_query(query, params, fetch_all=True)
            return [dict(row) for row in results_rows] if results_rows else []
