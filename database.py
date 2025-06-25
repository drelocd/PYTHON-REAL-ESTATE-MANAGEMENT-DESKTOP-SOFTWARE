import sqlite3
import os
from datetime import datetime, timedelta
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
                    transaction_date TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS
                    receipt_path TEXT,
                    added_by_user_id INTEGER, -- New column
                    FOREIGN KEY (property_id) REFERENCES properties(property_id),
                    FOREIGN KEY (client_id) REFERENCES clients(client_id),
                    FOREIGN KEY (added_by_user_id) REFERENCES users(user_id)
                )
            ''')

            # 4. SurveyJobs Table - ADDED 'added_by_user_id'
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS survey_jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL, -- Link to clients table
                    property_location TEXT NOT NULL, -- Location where survey is done
                    job_description TEXT,
                    fee REAL NOT NULL,
                    amount_paid REAL DEFAULT 0.0,
                    balance REAL DEFAULT 0.0,
                    deadline TEXT NOT NULL, -- YYYY-MM-DD
                    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Ongoing', 'Completed', 'Cancelled')),
                    attachments_path TEXT,
                    added_by_user_id INTEGER, -- New column
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

    def _get_connection(self):
        """Returns a connection object to the database."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

## User Management Methods (New)
    def add_user(self, username, password, role='user'):
        """
        Adds a new user to the database with a hashed password.
        Args:
            username (str): The unique username.
            password (str): The plain text password.
            role (str, optional): The user's role ('user' or 'admin'). Defaults to 'user'.
        Returns:
            int: The ID of the newly added user, or None on error (e.g., duplicate username).
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
        Args:
            username (str): The username provided by the user.
            password (str): The plain text password provided by the user.
        Returns:
            dict: The user's data (user_id, username, role) if credentials are valid, None otherwise.
        """
        query = "SELECT user_id, username, password_hash, role FROM users WHERE username = ?"
        user_data = self._execute_query(query, (username,), fetch_one=True)

        if user_data:
            stored_password_hash = user_data['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash):
                # Credentials are valid, return user data without the hash
                user_dict = dict(user_data)
                del user_dict['password_hash'] # Do not return the hash
                return user_dict
        return None

    def get_user_by_id(self, user_id):
        """
        Retrieves a user by their ID.
        Args:
            user_id (int): The ID of the user to retrieve.
        Returns:
            sqlite3.Row: The user's data (excluding password_hash), or None if not found.
        """
        query = "SELECT user_id, username, role FROM users WHERE user_id = ?"
        return self._execute_query(query, (user_id,), fetch_one=True)

    def update_user_password(self, user_id, new_password):
        """
        Updates a user's password.
        Args:
            user_id (int): The ID of the user to update.
            new_password (str): The new plain text password.
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "UPDATE users SET password_hash = ? WHERE user_id = ?"
        return self._execute_query(query, (hashed_password, user_id))

    def update_user_role(self, user_id, new_role):
        """
        Updates a user's role.
        Args:
            user_id (int): The ID of the user to update.
            new_role (str): The new role ('user' or 'admin').
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        if new_role not in ['user', 'admin']:
            print("Invalid role specified. Role must be 'user' or 'admin'.")
            return False
        query = "UPDATE users SET role = ? WHERE user_id = ?"
        return self._execute_query(query, (new_role, user_id))

    def delete_user(self, user_id):
        """
        Deletes a user from the database.
        Args:
            user_id (int): The ID of the user to delete.
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        query = "DELETE FROM users WHERE user_id = ?"
        return self._execute_query(query, (user_id,))
    
    def _execute_query(self, query, params=(), fetch_one=False, fetch_all=False):
        """
        A helper method to execute SQL queries.
        Can fetch one, fetch all, or just execute (for INSERT, UPDATE, DELETE).
        Handles common SQLite errors.
        Returns:
            - For SELECT queries: a single row (sqlite3.Row) or a list of rows, or None if no results.
            - For INSERT queries: the last inserted row ID, or None on error.
            - For UPDATE/DELETE queries: True if at least one row was affected, False otherwise, or None on error.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()

                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                
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
            print(f"An unexpected error occurred: {e}")
            return None

    def get_properties_by_title_deed(self, title_deed_number):
        """
        Retrieves ALL properties matching a given title deed number.
        This is useful now that title_deed_number is no longer unique per record.
        Args:
            title_deed_number (str): The title deed number of the property.
        Returns:
            list: A list of sqlite3.Row objects representing matching properties.
        """
        query = "SELECT * FROM properties WHERE title_deed_number = ?;"
        return self._execute_query(query, (title_deed_number,), fetch_all=True)
    ## CRUD Operations for Properties

    def add_property(self, title_deed_number, location, size, description, price, image_paths=None, title_image_paths=None, status='Available', added_by_user_id=None):
        """
        Adds a new property to the database, tracking the user who added it.
        ... (docstring remains mostly the same, add user_id)
        """
        existing_properties = self.get_properties_by_title_deed(title_deed_number)

        for prop in existing_properties:
            if prop['status'].lower() == 'available':
                print(f"Property with title deed '{title_deed_number}' already exists and is 'Available'. Cannot add duplicate.")
                return None

        # UPDATED: Added 'added_by_user_id' to query and parameters
        query = '''INSERT INTO properties (title_deed_number, location, size, description, price, image_paths, title_image_paths, status, added_by_user_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (title_deed_number, location, size, description, price, image_paths, title_image_paths, status, added_by_user_id))

    def get_property(self, property_id):
        """
        Retrieves a property by its ID.
        Args:
            property_id (int): The ID of the property to retrieve.
        Returns:
            sqlite3.Row: The property details, or None if not found.
        """
        query = "SELECT * FROM properties WHERE property_id = ?"
        return self._execute_query(query, (property_id,), fetch_one=True)

    def get_all_properties(self, status=None):
        """
        Retrieves all properties, optionally filtered by status.
        Args:
            status (str, optional): Filter by property status ('Available', 'Sold'). Defaults to None (all properties).
        Returns:
            list: A list of sqlite3.Row objects representing properties.
        """
        query = "SELECT * FROM properties"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        return self._execute_query(query, params, fetch_all=True)

    def update_property(self, property_id, **kwargs):
        """
        Updates details of an existing property.
        Args:
            property_id (int): The ID of the property to update.
            **kwargs: Keyword arguments for columns to update (e.g., location='New Location').
                      Valid keys: 'title_deed_number', 'location', 'size', 'description',
                      'price', 'image_paths', 'title_image_paths', 'status'.
        Returns:
            bool: True if the update was successful and affected at least one row, False otherwise.
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
        Args:
            property_id (int): The ID of the property to delete.
        Returns:
            bool: True if deletion was successful and affected at least one row, False otherwise.
        """
        query = "DELETE FROM properties WHERE property_id = ?"
        return self._execute_query(query, (property_id,))
    
    def get_total_properties(self):
        """
        Returns the total count of properties.
        Returns:
            int: Total number of properties.
        """
        query = "SELECT COUNT(*) FROM properties"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result else 0

    def get_properties_by_title_deed(self, title_deed_number): # <-- RENAMED METHOD
        """
        Retrieves ALL properties associated with a given title deed number.
        This is crucial for checking if ANY of them are 'Available'.
        Args:
            title_deed_number (str): The title deed number to search for.
        Returns:
            list: A list of sqlite3.Row objects representing all matching properties.
        """
        query = "SELECT * FROM properties WHERE title_deed_number = ?;"
        return self._execute_query(query, (title_deed_number,), fetch_all=True) # <-- ENSURED fetch_all=True


    def get_all_properties_paginated(self, limit=None, offset=None, search_query=None, min_size=None, max_size=None, status=None):
        """
        Fetches properties with optional search, size filters, status, and pagination,
        including the username of the user who added the property.
        Returns properties ordered by property_id DESC (newest first).
        
        Args:
            limit (int, optional): The maximum number of records to return. If None, no limit.
            offset (int, optional): The number of records to skip. If None, no offset.
            search_query (str, optional): Search string for title_deed_number, location, or description.
            min_size (float, optional): Minimum size of the property.
            max_size (float, optional): Maximum size of the property.
            status (str, optional): 'Available', 'Sold', or None for all.
        Returns:
            list: A list of dictionaries, each representing a property, including 'added_by_username'.
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
            p.added_by_user_id, -- Explicitly select the user ID
            u.username AS added_by_username -- Get the username from the users table
        FROM
            properties p
        LEFT JOIN
            users u ON p.added_by_user_id = u.user_id -- Join with the users table
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

        if status: # "Available" or "Sold"
            query += " AND p.status = ?"
            params.append(status)

        query += " ORDER BY p.property_id DESC" # Order by newest first (higher ID)

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)

        results = self._execute_query(query, tuple(params), fetch_all=True)
        return [dict(row) for row in results] if results else []

    ## CRUD Operations for Clients

    def add_client(self, name, contact_info, added_by_user_id=None): # ADDED added_by_user_id
        """
        Adds a new client to the database, tracking the user who added them.
        Returns: The ID of the new client, or None on error/duplicate contact_info.
        """
        query = "INSERT INTO clients (name, contact_info, added_by_user_id) VALUES (?, ?, ?)" # UPDATED query
        return self._execute_query(query, (name, contact_info, added_by_user_id)) # UPDATED params

    def get_client(self, client_id):
        """
        Retrieves a client by their ID.
        Args:
            client_id (int): The ID of the client to retrieve.
        Returns:
            sqlite3.Row: The client details, or None if not found.
        """
        query = "SELECT * FROM clients WHERE client_id = ?"
        return self._execute_query(query, (client_id,), fetch_one=True)

    def get_client_by_contact_info(self, contact_info):
        """
        Retrieves a client by their contact information.
        Args:
            contact_info (str): The unique contact information of the client.
        Returns:
            sqlite3.Row: The client details, or None if not found.
        """
        query = "SELECT * FROM clients WHERE contact_info = ?"
        return self._execute_query(query, (contact_info,), fetch_one=True)

    def get_all_clients(self):
        """
        Retrieves all clients from the database.
        Returns:
            list: A list of sqlite3.Row objects representing clients.
        """
        query = "SELECT * FROM clients"
        return self._execute_query(query, fetch_all=True)

    def update_client(self, client_id, **kwargs):
        """
        Updates details of an existing client.
        Args:
            client_id (int): The ID of the client to update.
            **kwargs: Keyword arguments for columns to update (e.g., name='New Name').
                      Valid keys: 'name', 'contact_info'.
        Returns:
            bool: True if the update was successful and affected at least one row, False otherwise.
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
        Args:
            client_id (int): The ID of the client to delete.
        Returns:
            bool: True if deletion was successful and affected at least one row, False otherwise.
        """
        query = "DELETE FROM clients WHERE client_id = ?"
        return self._execute_query(query, (client_id,))

    def get_total_clients(self):
        """
        Returns the total count of clients.
        Returns:
            int: Total number of clients.
        """
        query = "SELECT COUNT(*) FROM clients"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result else 0

    def get_client_by_id(self, client_id):
        """
        Retrieves client details by ID, formatted as a dictionary.
        """
        try:
            # Use the existing _execute_query method which uses _get_connection
            query = "SELECT * FROM clients WHERE client_id = ?"
            client_data = self._execute_query(query, (client_id,), fetch_one=True)
            
            if client_data:
                return dict(client_data) # Convert the sqlite3.Row to a dictionary
            return None
        except Exception as e: # Catch any potential errors from _execute_query
            print(f"Error getting client by ID: {e}")
            return None

    ## CRUD Operations for Transactions

    def add_transaction(self, property_id, client_id, payment_mode, total_amount_paid, discount=0.0, balance=0.0, receipt_path=None, added_by_user_id=None): # ADDED added_by_user_id
        """
        Adds a new sales transaction, automatically setting the transaction date/time,
        and tracking the user who recorded it.
        Args:
            property_id (int): ID of the property involved.
            client_id (int): ID of the client involved.
            payment_mode (str): How the payment was made ('Cash', 'Installments').
            total_amount_paid (float): The total amount paid in this transaction.
            discount (float, optional): Any discount applied. Defaults to 0.0.
            balance (float, optional): Remaining balance if in installments. Defaults to 0.0.
            receipt_path (str, optional): Path to the transaction receipt. Defaults to None.
            added_by_user_id (int, optional): The user_id of the employee who recorded this transaction. Defaults to None. # NEW ARG
        Returns:
            int: The ID of the newly added transaction, or None on error.
        """
        # Always use the current date and time from the system for system integrity
        transaction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # UPDATED: Added 'added_by_user_id' to query and parameters
        query = '''INSERT INTO transactions (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        return self._execute_query(query, (property_id, client_id, payment_mode, total_amount_paid, discount, balance, transaction_date, receipt_path, added_by_user_id))

    def get_transaction(self, transaction_id):
        """
        Retrieves a transaction by its ID.
        Args:
            transaction_id (int): The ID of the transaction to retrieve.
        Returns:
            sqlite3.Row: The transaction details, or None if not found.
        """
        query = "SELECT * FROM transactions WHERE transaction_id = ?"
        return self._execute_query(query, (transaction_id,), fetch_one=True)

    def get_transactions_by_property(self, property_id):
        """
        Retrieves all transactions related to a specific property.
        Args:
            property_id (int): The ID of the property.
        Returns:
            list: A list of sqlite3.Row objects representing transactions.
        """
        query = "SELECT * FROM transactions WHERE property_id = ?"
        return self._execute_query(query, (property_id,), fetch_all=True)
    
    def get_transactions_by_client(self, client_id):
        """
        Retrieves all transactions related to a specific client.
        Args:
            client_id (int): The ID of the client.
        Returns:
            list: A list of sqlite3.Row objects representing transactions.
        """
        query = "SELECT * FROM transactions WHERE client_id = ?"
        return self._execute_query(query, (client_id,), fetch_all=True)

    def get_all_transactions(self):
        """
        Retrieves all transactions from the database.
        Returns:
            list: A list of sqlite3.Row objects representing transactions.
        """
        query = "SELECT * FROM transactions"
        return self._execute_query(query, fetch_all=True)

    def get_total_pending_sales_payments(self):
        """
        Calculates the sum of outstanding balances from property transactions.
        Returns:
            float: Total pending amount from sales, or 0.0 if none.
        """
        query = "SELECT SUM(balance) FROM transactions WHERE balance > 0"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result and result[0] is not None else 0.0

    def update_transaction(self, transaction_id, **kwargs):
        """
        Updates details of an existing transaction.
        Args:
            transaction_id (int): The ID of the transaction to update.
            **kwargs: Keyword arguments for columns to update.
                      Valid keys: 'property_id', 'client_id', 'payment_mode',
                      'total_amount_paid', 'discount', 'balance', 'transaction_date',
                      'receipt_path'.
        Returns:
            bool: True if the update was successful and affected at least one row, False otherwise.
        """
        set_clauses = []
        params = []
        
        # Define allowed columns to prevent SQL injection or updating non-existent columns
        allowed_columns = [
            'property_id', 'client_id', 'payment_mode', 'total_amount_paid',
            'discount', 'balance', 'transaction_date', 'receipt_path'
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

    # --- NEW METHOD FOR TrackPaymentsForm ---
    def get_transactions_with_details(self, status=None, start_date=None, end_date=None, payment_mode=None, client_name_search=None, property_search=None, client_contact_search=None):
        """
        Retrieves transactions with details from linked properties and clients,
        allowing for various filtering options, including client contact info.
        
        Args:
            status (str, optional): 'complete', 'pending', or None for all.
                                    This relates to the 'balance' being 0 or > 0.
            start_date (str, optional): YYYY-MM-DD. Start date for transaction_date.
            end_date (str, optional): YYYY-MM-DD. End date for transaction_date.
            payment_mode (str, optional): 'Cash', 'Installments', or None for all.
            client_name_search (str, optional): Partial client name search.
            property_search (str, optional): Partial property title_deed_number or location search.
            client_contact_search (str, optional): Partial client contact_info search. # NEW PARAMETER

        Returns:
            list: A list of dictionaries, where each dictionary contains combined
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
            c.contact_info AS client_contact_info, -- Changed alias for clarity and consistency
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
            params.append(f"{start_date} 00:00:00") # Include start of day
        
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59") # Include end of day
            
        if payment_mode:
            query += " AND t.payment_mode = ?"
            params.append(payment_mode)
            
        if client_name_search:
            query += " AND c.name LIKE ?"
            params.append(f"%{client_name_search}%")
            
        if property_search:
            # Search in both title_deed_number and location
            query += " AND (p.title_deed_number LIKE ? OR p.location LIKE ?)"
            params.append(f"%{property_search}%")
            params.append(f"%{property_search}%")

        if client_contact_search: # NEW FILTER CONDITION
            query += " AND c.contact_info LIKE ?"
            params.append(f"%{client_contact_search}%")
            
        query += " ORDER BY t.transaction_date DESC" # Order by date, newest first

        results = self._execute_query(query, params, fetch_all=True)
        # Convert sqlite3.Row objects to dictionaries for easier access
        return [dict(row) for row in results] if results else []

    ## --- NEW METHODS FOR SOLD PROPERTIES UI ---

    def get_total_sold_properties_count(self, start_date=None, end_date=None):
        """
        Returns the total count of properties with 'Sold' status, optionally filtered by transaction date.
        Args:
            start_date (str, optional): YYYY-MM-DD. Start date for transaction_date.
            end_date (str, optional): YYYY-MM-DD. End date for transaction_date.
        Returns:
            int: Total number of sold properties matching criteria.
        """
        query = "SELECT COUNT(*) FROM properties p JOIN transactions t ON p.property_id = t.property_id WHERE p.status = 'Sold'"
        params = []

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")
        
        result = self._execute_query(query, params, fetch_one=True)
        return result[0] if result else 0

    def get_sold_properties_paginated(self, limit, offset, start_date=None, end_date=None):
        """
        Retrieves sold properties along with their transaction and client details,
        supporting pagination and date filtering.
        
        Args:
            limit (int): The maximum number of records to return.
            offset (int): The number of records to skip from the beginning.
            start_date (str, optional): YYYY-MM-DD. Start date for transaction_date.
            end_date (str, optional): YYYY-MM-DD. End date for transaction_date.

        Returns:
            list: A list of dictionaries, each containing details for a sold property.
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
            c.name AS client_name,
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
        params.extend([limit, offset]) # Add limit and offset to params at the end

        results = self._execute_query(query, params, fetch_all=True)
        return [dict(row) for row in results] if results else []


    # UPDATED add_survey_job to reflect schema changes and default attachments_path to None
    def add_survey_job(self, client_id, property_location, job_description, fee, deadline,
                       amount_paid=0.0, balance=0.0, status='Pending',
                       attachments_path=None, added_by_user_id=None, created_at=None): # <-- Added created_at parameter
        """
        Adds a new survey job, tracking the user who created it and the creation timestamp.
        Args:
            client_id (int): ID of the client requesting the survey.
            property_location (str): Location where the survey is to be conducted.
            job_description (str): Description of the survey job.
            fee (float): Total fee for the survey job.
            deadline (str): Deadline for the survey in 'YYYY-MM-DD' format.
            amount_paid (float, optional): Initial amount paid for the survey. Defaults to 0.0.
            balance (float, optional): Remaining balance for the survey. Defaults to 0.0.
            status (str, optional): Current status ('Pending', 'Ongoing', 'Completed', 'Cancelled'). Defaults to 'Pending'.
            attachments_path (str, optional): Comma-separated paths to job attachments. Defaults to None.
            added_by_user_id (int, optional): The user_id of the employee who added this survey job. Defaults to None.
            created_at (str, optional): Timestamp when the job was created (YYYY-MM-DD HH:MM:SS). Defaults to None.
                                        If None, and DB column has DEFAULT CURRENT_TIMESTAMP, DB will set it.
        Returns:
            int: The ID of the newly added survey job, or None on error.
        """
        query = '''INSERT INTO survey_jobs (client_id, property_location, job_description, fee,
                                     amount_paid, balance, deadline, status, attachments_path, added_by_user_id, created_at)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''' # <-- Added created_at column and its placeholder '?'
        return self._execute_query(query, (client_id, property_location, job_description, fee,
                                            amount_paid, balance, deadline, status, attachments_path, added_by_user_id, created_at)) # <-- Added created_at value
    def get_survey_job(self, job_id):
        """
        Retrieves a survey job by its ID.
        Args:
            job_id (int): The ID of the survey job to retrieve.
        Returns:
            sqlite3.Row: The survey job details, or None if not found.
        """
        query = "SELECT * FROM survey_jobs WHERE job_id = ?"
        return self._execute_query(query, (job_id,), fetch_one=True)


    def update_survey_job_receipt_path(self, job_id, receipt_path):
        """
        Updates the 'receipt_path' field for a given survey job.
        Args:
            job_id (int): The ID of the survey job to update.
            receipt_path (str): The path to the generated receipt PDF.
        Returns:
            bool: True if the update was successful, False otherwise.
        """
        query = """
            UPDATE survey_jobs
            SET receipt_path = ?
            WHERE job_id = ?
        """
        # _execute_query returns True on success for updates, False on failure.
        return self._execute_query(query, (receipt_path, job_id), fetch_one=False)
    

    def get_all_survey_jobs(self, status=None):
        """
        Retrieves all survey jobs, optionally filtered by status.
        Args:
            status (str, optional): Filter by job status ('Pending', 'Ongoing', 'Completed', 'Cancelled'). Defaults to None (all jobs).
        Returns:
            list: A list of sqlite3.Row objects representing survey jobs.
        """
        query = "SELECT * FROM survey_jobs"
        params = ()
        if status:
            query += " WHERE status = ?"
            params = (status,)
        return self._execute_query(query, params, fetch_all=True)
    
    # --- ADD THIS NEW METHOD ---
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
        return self._execute_query(query, (attachments_paths_str, job_id), fetch_one=False) # No fetch needed for UPDATE

    def update_survey_job(self, job_id, **kwargs):
        """
        Updates details of an existing survey job.
        Args:
            job_id (int): The ID of the survey job to update.
            **kwargs: Keyword arguments for columns to update.
                      Valid keys: 'client_id', 'property_location', 'job_description',
                      'fee', 'amount_paid', 'balance', 'deadline', 'status', 'attachments_path', 'added_by_user_id'.
        Returns:
            bool: True if the update was successful and affected at least one row, False otherwise.
        """
        set_clauses = []
        params = []
        # Updated allowed keys to match your schema and added 'added_by_user_id'
        allowed_keys = ['client_id', 'property_location', 'job_description', 
                        'fee', 'amount_paid', 'balance', 'deadline', 
                        'status', 'attachments_path', 'added_by_user_id'] 

        for key, value in kwargs.items():
            if key in allowed_keys:
                set_clauses.append(f"{key} = ?")
                params.append(value)
            
        if not set_clauses:
            print("No valid columns provided for survey job update.")
            return False

        params.append(job_id)
        query = f"UPDATE survey_jobs SET {', '.join(set_clauses)} WHERE job_id = ?"
        # Use _execute_query, it will return True/False based on affected rows
        return self._execute_query(query, params, fetch_one=False)

    def delete_survey_job(self, job_id):
        """
        Deletes a survey job from the database.
        Args:
            job_id (int): The ID of the survey job to delete.
        Returns:
            bool: True if deletion was successful and affected at least one row, False otherwise.
        """
        query = "DELETE FROM survey_jobs WHERE job_id = ?"
        return self._execute_query(query, (job_id,))

    def get_total_pending_survey_payments(self):
        """
        Calculates the sum of outstanding balances from survey jobs.
        Returns:
            float: Total pending amount from survey jobs, or 0.0 if none.
        """
        query = "SELECT SUM(balance) FROM survey_jobs WHERE balance > 0"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result and result[0] is not None else 0.0

    def get_total_survey_jobs(self):
        """
        Returns the total count of survey jobs.
        Returns:
            int: Total number of survey jobs.
        """
        query = "SELECT COUNT(*) FROM survey_jobs"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result else 0

    def get_completed_survey_jobs_count(self):
        """
        Returns the count of completed survey jobs.
        Returns:
            int: Number of completed survey jobs.
        """
        query = "SELECT COUNT(*) FROM survey_jobs WHERE status = 'Completed'"
        result = self._execute_query(query, fetch_one=True)
        return result[0] if result else 0

    def get_upcoming_survey_deadlines_count(self, days_threshold=30):
        """
        Returns the count of pending/ongoing survey jobs with deadlines within the next `days_threshold` days.
        Args:
            days_threshold (int): Number of days from today to consider for upcoming deadlines.
        Returns:
            int: Number of upcoming survey deadlines.
        """
        current_date = datetime.now().strftime("%Y-%m-%d")
        future_date = (datetime.now() + timedelta(days=days_threshold)).strftime("%Y-%m-%d")
        
        query = "SELECT COUNT(*) FROM survey_jobs WHERE status IN ('Pending', 'Ongoing') AND deadline BETWEEN ? AND ?"
        params = (current_date, future_date)
        result = self._execute_query(query, params, fetch_one=True)
        return result[0] if result else 0

    # --- NEW REPORTING METHODS (FOR SalesReportsForm) ---
    # These methods assume 'transactions' and 'properties' tables exist.
    # Ensure those tables are also created in _create_tables() if not already.

    def get_total_sales_for_date_range(self, start_date, end_date):
        """
        Retrieves total revenue and total properties sold within a specified date range.
        Assumes 'transaction_date' in 'transactions' table is stored as YYYY-MM-DD HH:MM:SS.
        """
        try:
            # Using self._execute_query for consistency
            query = """
                SELECT 
                    SUM(t.total_amount_paid + t.balance) AS total_revenue, -- Total sales value (paid + balance)
                    COUNT(DISTINCT t.property_id) AS total_properties_sold
                FROM 
                    transactions t
                WHERE 
                    t.transaction_date BETWEEN ? AND ? || ' 23:59:59'
            """
            result = self._execute_query(query, (start_date, end_date), fetch_one=True)
            
            return {
                'total_revenue': result['total_revenue'] if result and result['total_revenue'] else 0.0,
                'total_properties_sold': result['total_properties_sold'] if result and result['total_properties_sold'] else 0
            }
        except Exception as e: # Catch generic Exception to log issues with this specific query
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
            results = self._execute_query(query, (start_date, end_date), fetch_all=True)
            # Manually add 'property_type' as 'Land' since it's not a DB column
            return [dict(row) | {'property_type': 'Land'} for row in results] if results else []
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
            return self._execute_query(query, (start_date, end_date), fetch_all=True)
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
            return self._execute_query(query, (start_date, end_date), fetch_all=True)
        except Exception as e:
            print(f"Error in get_pending_instalments_for_date_range: {e}")
            return []