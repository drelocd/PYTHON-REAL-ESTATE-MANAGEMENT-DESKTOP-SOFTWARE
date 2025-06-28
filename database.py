import sqlite3
import os
from datetime import datetime, timedelta
from tkinter import messagebox

import bcrypt

# Define the path for the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'real_estate.db')


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

    def _create_tables(self):
        """Initializes the database by creating tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Properties Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS properties (
                        property_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title_deed_number TEXT NOT NULL,
                        location TEXT NOT NULL,
                        size REAL NOT NULL,
                        description TEXT,
                        price REAL NOT NULL,
                        image_paths TEXT,      -- Stores comma-separated paths
                        title_image_paths TEXT, -- Stores comma-separated paths
                        status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Sold')),
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 2. Clients Table - ADDED 'added_by_user_id'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        contact_info TEXT UNIQUE NOT NULL, -- Can be phone, email, etc.
                        added_by_user_id INTEGER, -- New column
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 3. Transactions Table - ADDED 'added_by_user_id'
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

                # 4. SurveyJobs Table - ADDED 'added_by_user_id', 'created_at', 'receipt_creation_path'
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS survey_jobs (
                        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER NOT NULL, -- Link to clients table
                        property_location TEXT NOT NULL, -- Location where survey is done
                        job_description TEXT,
                        fee REAL NOT NULL,
                        amount_paid REAL DEFAULT 0.0,
                        balance REAL DEFAULT 0.0,
                        deadline TEXT NOT NULL, --YYYY-MM-DD
                        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Ongoing', 'Completed', 'Cancelled')),
                        attachments_path TEXT,
                        added_by_user_id INTEGER NOT NULL, -- New column
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP, -- New timestamp column
                        receipt_creation_path TEXT,
                        FOREIGN KEY (client_id) REFERENCES clients(client_id),
                        FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                    )
                ''')

                # 5. Users Table (No change needed here for new columns, it's the target)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'user' CHECK(role IN ('user', 'admin'))
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
    def add_user(self, username, password, role='user'):
        """
        Adds a new user to the database with a hashed password.
        Returns: The ID of the newly added user, or None on error (e.g., duplicate username).
        """
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            query = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
            return self._execute_query(query, (username, hashed_password, role))
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

    ## CRUD Operations for Properties

    def get_properties_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        Returns: A list of dictionaries representing matching properties.
        """
        query = "SELECT * FROM properties WHERE title_deed_number = ?;"
        results_rows = self._execute_query(query, (title_deed_number,), fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

    def add_property(self, title_deed_number, location, size, description, price, image_paths=None, title_image_paths=None, status='Available', added_by_user_id=None):
        """
        Adds a new property to the database, tracking the user who added it.
        """
        existing_properties = self.get_properties_by_title_deed(title_deed_number)

        for prop in existing_properties:
            if prop['status'].lower() == 'available': # This 'prop' will already be a dict from get_properties_by_title_deed
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        query = '''INSERT INTO properties (title_deed_number, location, size, description, price, image_paths, title_image_paths, status, added_by_user_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (title_deed_number, location, size, description, price, image_paths, title_image_paths, status, added_by_user_id))

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
            p.title_deed_number,
            p.location,
            p.size,
            p.description,
            p.price,
            p.image_paths,
            p.title_image_paths,
            p.status,
            p.added_by_user_id,
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

    def add_client(self, name, contact_info, added_by_user_id=None):
        """
        Adds a new client to the database, tracking the user who added them.
        Returns: The ID of the new client, or None on error/duplicate contact_info.
        """
        query = "INSERT INTO clients (name, contact_info, added_by_user_id) VALUES (?, ?, ?)"
        return self._execute_query(query, (name, contact_info, added_by_user_id))

    def get_client(self, client_id):
        """
        Retrieves a client by their ID.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE client_id = ?"
        client_data_row = self._execute_query(query, (client_id,), fetch_one=True)
        return dict(client_data_row) if client_data_row else None # Explicitly convert

    def get_client_by_contact_info(self, contact_info):
        """
        Retrieves a client by their contact information.
        Returns: The client details as a dict, or None if not found.
        """
        query = "SELECT * FROM clients WHERE contact_info = ?"
        client_data_row = self._execute_query(query, (contact_info,), fetch_one=True)
        return dict(client_data_row) if client_data_row else None # Explicitly convert

    def get_all_clients(self, ):
        """
        Retrieves all clients from the database.
        Returns: A list of dictionaries representing clients.
        """
        query = "SELECT * FROM clients"
        results_rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert

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
        """
        Deletes a client from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "DELETE FROM clients WHERE client_id = ?"
        return self._execute_query(query, (client_id,))

    def get_total_clients(self):
        """
        Returns the total count of clients.
        Returns: Total number of clients.
        """
        query = "SELECT COUNT(*) FROM clients"
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


    def add_survey_job(self, client_id, property_location, job_description, fee, deadline,
                        amount_paid=0.0, balance=0.0, status='Pending',
                        attachments_path=None, added_by_user_id=None, created_at=None, receipt_creation_path=None):
        """
        Adds a new survey job, tracking the user who created it and the creation timestamp.
        Returns: The ID of the newly added survey job, or None on error.
        """
        query = '''INSERT INTO survey_jobs (client_id, property_location, job_description, fee,
                                     amount_paid, balance, deadline, status, attachments_path, 
                                     added_by_user_id, created_at, receipt_creation_path)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        params = (
             client_id, property_location, job_description, fee,
             amount_paid, balance, deadline, status,
             attachments_path, added_by_user_id, created_at, receipt_creation_path
        )
        return self._execute_query(query, params)

    def get_survey_job_by_id(self, job_id):
        """
        Retrieves a survey job by its ID.
        Returns: The survey job details as a dict, or None if not found.
        """
        query = "SELECT * FROM survey_jobs WHERE job_id = ?"
        job_data_row = self._execute_query(query, (job_id,), fetch_one=True)
        return dict(job_data_row) if job_data_row else None # Explicitly convert


    def update_survey_job_receipt_path(self, job_id, receipt_path):
        """
        Updates the 'receipt_path' field for a given survey job.
        Returns: True if the update was successful, False otherwise.
        """
        query = """
            UPDATE survey_jobs
            SET receipt_creation_path = ?
            WHERE job_id = ?
        """
        return self._execute_query(query, (receipt_path, job_id)) 
    

    def get_all_survey_jobs(self, status=None):
        """
        Retrieves all survey jobs, optionally filtered by status.
        Returns: A list of dictionaries representing survey jobs.
        """
        query = "SELECT * FROM survey_jobs"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        results_rows = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results_rows] if results_rows else [] # Explicitly convert
    
    def update_survey_job_attachments(self, job_id, attachments_paths_str):
        """
        Updates the 'attachments_path' field for a given survey job.
        attachments_paths_str should be a comma-separated string of relative paths.
        """
        query = """
            UPDATE survey_jobs
            SET attachments_path = ?
            WHERE job_id = ?
        """
        return self._execute_query(query, (attachments_paths_str, job_id))

    def update_survey_job(self, job_id, **kwargs):
        """
        Updates details of an existing survey job.
        Returns: True if the update was successful, False otherwise.
        """
        set_clauses = []
        params = []
        allowed_keys = ['client_id', 'property_location', 'job_description', 
                        'fee', 'amount_paid', 'balance', 'deadline', 
                        'status', 'attachments_path', 'added_by_user_id', 'receipt_creation_path'] 

        for key, value in kwargs.items():
            if key in allowed_keys:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for survey job update.")
            return False

        params.append(job_id)
        query = f"UPDATE survey_jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
        return self._execute_query(query, params)

    def delete_survey_job(self, job_id):
        """
        Deletes a survey job from the database.
        Returns: True if deletion was successful, False otherwise.
        """
        query = "DELETE FROM survey_jobs WHERE job_id = ?"
        return self._execute_query(query, (job_id,))

    def get_total_pending_survey_payments(self):
        """
        Calculates the sum of outstanding balances from survey jobs.
        Returns: Total pending amount from survey jobs, or 0.0 if none.
        """
        query = "SELECT SUM(balance) FROM survey_jobs WHERE balance > 0"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row and result_row[0] is not None else 0.0

    def get_total_survey_jobs(self):
        """
        Returns the total count of survey jobs.
        Returns: Total number of survey jobs.
        """
        query = "SELECT COUNT(*) FROM survey_jobs"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0

    def get_completed_survey_jobs_count(self):
        """
        Returns the count of completed survey jobs.
        Returns: Number of completed survey jobs.
        """
        query = "SELECT COUNT(*) FROM survey_jobs WHERE status = 'Completed'"
        result_row = self._execute_query(query, fetch_one=True)
        return result_row[0] if result_row else 0

    def get_upcoming_survey_deadlines_count(self, days_threshold=30):
        """
        Returns the count of pending/ongoing survey jobs with deadlines within the next `days_threshold` days.
        Returns: Number of upcoming survey deadlines.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        future_date = (datetime.now() + timedelta(days=days_threshold)).strftime("%Y-%m-%d")
        
        query = "SELECT COUNT(*) FROM survey_jobs WHERE status IN ('Pending', 'Ongoing') AND deadline BETWEEN ? AND ?"
        params = (current_date, future_date)
        result_row = self._execute_query(query, params, fetch_one=True)
        return result_row[0] if result_row else 0

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

    def get_completed_surveys_for_date_range(self, start_date, end_date):
        """
        Returns completed surveys between the given dates based on 'created_at' and 'status = 'Completed''.
        Uses 'added_by_user_id' for the user who added the job.
        """
        try:
            query = """
            SELECT 
                sj.job_id, 
                sj.property_location, 
                sj.job_description,
                sj.fee,
                sj.status,
                sj.created_at AS completion_date, -- Renamed for report compatibility
                c.name AS client_name,
                u.username AS surveyor_name -- Using added_by_user as surveyor_name for report
            FROM survey_jobs sj
            JOIN clients c ON sj.client_id = c.client_id
            JOIN users u ON sj.added_by_user_id = u.user_id
            WHERE sj.status = 'Completed'
            AND DATE(sj.created_at) BETWEEN ? AND ? 
            ORDER BY sj.created_at DESC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [dict(row) for row in results_rows] if results_rows else []
        except Exception as e:
            print(f"Error fetching completed surveys: {e}")
            return []

    def get_upcoming_survey_deadlines_for_date_range(self, start_date, end_date):
        """
        Returns surveys with deadlines between the given dates, based on 'deadline' and status.
        Uses 'added_by_user_id' for the user who added the job.
        """
        try:
            query = """
            SELECT 
                sj.job_id, 
                c.name AS client_name, 
                sj.property_location,
                sj.deadline AS deadline_date, 
                sj.status, 
                u.username AS assigned_to, -- Using added_by_user as assigned_to for report
                CASE 
                    WHEN DATE(sj.deadline) = DATE('now') THEN 'High'
                    WHEN DATE(sj.deadline) < DATE('now', '+3 days') THEN 'Medium'
                    ELSE 'Low'
                END AS priority
            FROM survey_jobs sj
            JOIN clients c ON sj.client_id = c.client_id
            JOIN users u ON sj.added_by_user_id = u.user_id 
            WHERE sj.status IN ('Pending', 'Ongoing')
            AND DATE(sj.deadline) BETWEEN ? AND ?
            ORDER BY 
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    ELSE 3
                END,
                sj.deadline ASC
            """
            results_rows = self._execute_query(query, (start_date, end_date), fetch_all=True)
            return [dict(row) for row in results_rows] if results_rows else []
        except Exception as e:
            print(f"Error fetching upcoming deadlines: {e}")
            return []


    def get_survey_jobs_paginated(self, page=1, page_size=15, filters=None, sort_by='created_at', sort_order='DESC'):
        """
        Retrieves a paginated list of survey jobs with client and user information,
        applying filters and sorting.
        """
        jobs = []
        total_count = 0
        try:
            where_clauses = []
            params = []

            # Base query including JOINs to client and user tables
            base_query_select = """
                SELECT 
                    sj.job_id, sj.client_id, sj.property_location, sj.job_description,
                    sj.fee, sj.amount_paid, sj.balance, sj.deadline, sj.status,
                    sj.attachments_path, sj.added_by_user_id, sj.created_at, sj.receipt_creation_path,
                    c.name AS client_name, c.contact_info AS client_contact,
                    u.username AS added_by_username
                FROM 
                    survey_jobs sj
                JOIN 
                    clients c ON sj.client_id = c.client_id
                LEFT JOIN 
                    users u ON sj.added_by_user_id = u.user_id
            """
            
            # Filters
            if filters:
                if 'client_name' in filters and filters['client_name']:
                    where_clauses.append("c.name LIKE ?")
                    params.append(f"%{filters['client_name']}%")
                if 'location' in filters and filters['location']:
                    where_clauses.append("sj.property_location LIKE ?")
                    params.append(f"%{filters['location']}%")
                if 'contact_info' in filters and filters['contact_info']:
                    where_clauses.append("c.contact_info LIKE ?")
                    params.append(f"%{filters['contact_info']}%")
                if 'job_description' in filters and filters['job_description']:
                    where_clauses.append("sj.job_description LIKE ?")
                    params.append(f"%{filters['job_description']}%")
                if 'status' in filters and filters['status'] and filters['status'].lower() != 'all':
                    where_clauses.append("sj.status = ?")
                    params.append(filters['status'])
                
                # Date filtering for 'created_at' column
                if 'start_date' in filters and filters['start_date']:
                    try:
                        datetime.strptime(filters['start_date'], '%Y-%m-%d')
                        where_clauses.append("sj.created_at >= ?")
                        params.append(filters['start_date'] + ' 00:00:00')
                    except ValueError:
                        pass # Ignore invalid date format
                if 'end_date' in filters and filters['end_date']:
                    try:
                        datetime.strptime(filters['end_date'], '%Y-%m-%d')
                        where_clauses.append("sj.created_at <= ?")
                        params.append(filters['end_date'] + ' 23:59:59')
                    except ValueError:
                        pass # Ignore invalid date format

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Count total jobs with filters (uses same WHERE clause)
            count_query = f"SELECT COUNT(*) FROM survey_jobs sj JOIN clients c ON sj.client_id = c.client_id {where_sql}"
            total_count_row = self._execute_query(count_query, params, fetch_one=True)
            total_count = total_count_row[0] if total_count_row else 0

            # Fetch paginated jobs
            offset = (page - 1) * page_size
            
            # Validate sort_by column to prevent SQL injection
            allowed_sort_columns_full = ['sj.created_at', 'c.name', 'sj.property_location', 'sj.fee', 'sj.status', 'sj.deadline', 'sj.job_id']
            if sort_by not in [col.replace('sj.', '').replace('c.', '') for col in allowed_sort_columns_full]: 
                sort_by_full = 'sj.created_at' 
            else:
                if sort_by == 'client_name':
                    sort_by_full = 'c.name'
                else: 
                    sort_by_full = f'sj.{sort_by}'
            
            # Validate sort_order
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            order_sql = f"ORDER BY {sort_by_full} {sort_order}"
            limit_sql = f"LIMIT ? OFFSET ?"

            main_query_params = list(params)
            main_query_params.extend([page_size, offset])

            query = f"{base_query_select} {where_sql} {order_sql} {limit_sql}"
            
            rows = self._execute_query(query, main_query_params, fetch_all=True)

            if rows:
                jobs = [dict(row) for row in rows] # Explicitly convert here for this method's consumer

        except Exception as e:
            print(f"Error in get_survey_jobs_paginated: {e}")
            return [], 0 
        return jobs, total_count

