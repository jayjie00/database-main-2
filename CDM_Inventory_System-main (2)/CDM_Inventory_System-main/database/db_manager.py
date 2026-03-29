import json
import os
import random
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from env_loader import load_env_file

load_env_file(__file__)

try:
    import mysql.connector as mysql_driver
    from mysql.connector import Error as MySQLError
except ImportError:
    mysql_driver = None
    MySQLError = Exception

DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "cdm_inventory_system")
RESET_CODE_EXPIRY_MINUTES = int(os.getenv("RESET_CODE_EXPIRY_MINUTES", "10"))


def _ensure_driver():
    if mysql_driver is None:
        raise RuntimeError(
            "MySQL driver not installed. Install it with: pip install mysql-connector-python"
        )


def _connect(include_database=True):
    _ensure_driver()
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "use_pure": True,
    }
    if include_database:
        config["database"] = DB_NAME
    return mysql_driver.connect(**config)


def get_connection():
    return _connect(include_database=True)


def _column_exists(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (DB_NAME, table_name, column_name),
    )
    result = cursor.fetchone()
    return bool(result and result[0])


def _ensure_column(cursor, table_name, column_name, definition):
    if not _column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {definition}")


def initialize_db():
    _ensure_driver()

    bootstrap_conn = _connect(include_database=False)
    try:
        cursor = bootstrap_conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        bootstrap_conn.commit()
    finally:
        bootstrap_conn.close()

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255) NOT NULL UNIQUE,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'Staff'
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                brand VARCHAR(255),
                qty INT NOT NULL DEFAULT 0,
                status VARCHAR(50) NOT NULL DEFAULT 'Available',
                category VARCHAR(100) NOT NULL,
                image_path TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INT PRIMARY KEY AUTO_INCREMENT,
                student_name VARCHAR(255) NOT NULL,
                items_json LONGTEXT NOT NULL,
                purpose TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                created_at DATETIME NOT NULL,
                approved_by VARCHAR(255) NULL,
                returned_by VARCHAR(255) NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id INT PRIMARY KEY AUTO_INCREMENT,
                email VARCHAR(255) NOT NULL,
                code VARCHAR(6) NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        _ensure_column(cursor, "users", "username", "VARCHAR(255) NULL")
        _ensure_column(cursor, "users", "email", "VARCHAR(255) NULL")
        _ensure_column(cursor, "users", "password", "VARCHAR(255) NULL")
        _ensure_column(cursor, "users", "role", "VARCHAR(50) NOT NULL DEFAULT 'Staff'")

        _ensure_column(cursor, "inventory", "name", "VARCHAR(255) NULL")
        _ensure_column(cursor, "inventory", "brand", "VARCHAR(255) NULL")
        _ensure_column(cursor, "inventory", "qty", "INT NOT NULL DEFAULT 0")
        _ensure_column(cursor, "inventory", "status", "VARCHAR(50) NOT NULL DEFAULT 'Available'")
        _ensure_column(cursor, "inventory", "category", "VARCHAR(100) NULL")
        _ensure_column(cursor, "inventory", "image_path", "TEXT NULL")

        _ensure_column(cursor, "requests", "student_name", "VARCHAR(255) NULL")
        _ensure_column(cursor, "requests", "items_json", "LONGTEXT NULL")
        _ensure_column(cursor, "requests", "purpose", "TEXT NULL")
        _ensure_column(cursor, "requests", "status", "VARCHAR(50) NOT NULL DEFAULT 'PENDING'")
        _ensure_column(cursor, "requests", "created_at", "DATETIME NULL")
        _ensure_column(cursor, "requests", "approved_by", "VARCHAR(255) NULL")
        _ensure_column(cursor, "requests", "returned_by", "VARCHAR(255) NULL")

        _ensure_column(cursor, "password_reset_codes", "email", "VARCHAR(255) NULL")
        _ensure_column(cursor, "password_reset_codes", "code", "VARCHAR(6) NULL")
        _ensure_column(cursor, "password_reset_codes", "created_at", "DATETIME NULL")

        if _column_exists(cursor, "inventory", "item_name"):
            cursor.execute(
                """
                UPDATE inventory
                SET name = item_name
                WHERE (name IS NULL OR name = '') AND item_name IS NOT NULL
                """
            )
        if _column_exists(cursor, "inventory", "quantity"):
            cursor.execute(
                """
                UPDATE inventory
                SET qty = quantity
                WHERE (qty IS NULL OR qty = 0) AND quantity IS NOT NULL
                """
            )

        cursor.execute(
            """
            UPDATE requests
            SET created_at = NOW()
            WHERE created_at IS NULL
            """
        )
        cursor.execute(
            """
            UPDATE password_reset_codes
            SET created_at = NOW()
            WHERE created_at IS NULL
            """
        )

        cursor.execute("SELECT id FROM users WHERE id = 1")
        if cursor.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO users (username, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                ("admin", "admin@cdm.local", "admin123", "Admin"),
            )

        conn.commit()
    finally:
        conn.close()


def _fetchone_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


def _fetchall_tuples(cursor):
    return [tuple(row) for row in cursor.fetchall()]


def _status_from_qty(qty):
    return "Available" if int(qty) > 0 else "Out of Stock"


def verify_admin(login_value, password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT role, username
            FROM users
            WHERE LOWER(COALESCE(email, '')) = LOWER(%s)
              AND password = %s
            LIMIT 1
            """,
            (login_value, password),
        )
        row = _fetchone_dict(cursor)
        if row:
            return True, row["role"], row["username"]
        return False, None, None
    finally:
        conn.close()


def create_user_account(username, email, password, role="Admin"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, email, password, role)
            VALUES (%s, %s, %s, %s)
            """,
            (username, email, password, role),
        )
        conn.commit()
        return True, "Account created successfully."
    except MySQLError:
        return False, "Username or email already exists."
    finally:
        conn.close()


def generate_reset_code(email):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE LOWER(email) = LOWER(%s) LIMIT 1", (email,)
        )
        user = cursor.fetchone()
        if user is None:
            return False, "Email address was not found.", None

        code = f"{random.randint(0, 999999):06d}"
        cursor.execute("DELETE FROM password_reset_codes WHERE LOWER(email) = LOWER(%s)", (email,))
        cursor.execute(
            """
            INSERT INTO password_reset_codes (email, code, created_at)
            VALUES (%s, %s, %s)
            """,
            (email, code, datetime.now()),
        )
        conn.commit()
        return True, "Reset code generated.", code
    finally:
        conn.close()


def reset_password_with_code(email, code, new_password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at
            FROM password_reset_codes
            WHERE LOWER(email) = LOWER(%s) AND code = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (email, code),
        )
        reset_row = cursor.fetchone()
        if reset_row is None:
            return False, "Invalid reset code."

        created_at = reset_row[1]
        if created_at is None:
            return False, "Reset code is invalid. Please request a new one."

        age_seconds = (datetime.now() - created_at).total_seconds()
        if age_seconds > RESET_CODE_EXPIRY_MINUTES * 60:
            cursor.execute("DELETE FROM password_reset_codes WHERE LOWER(email) = LOWER(%s)", (email,))
            conn.commit()
            return False, "Reset code expired. Please request a new one."

        cursor.execute(
            "UPDATE users SET password = %s WHERE LOWER(email) = LOWER(%s)",
            (new_password, email),
        )
        cursor.execute("DELETE FROM password_reset_codes WHERE LOWER(email) = LOWER(%s)", (email,))
        conn.commit()
        return True, "Password updated successfully."
    finally:
        conn.close()


def get_all_items():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, brand, qty, status, category, image_path FROM inventory ORDER BY id"
        )
        return _fetchall_tuples(cursor)
    finally:
        conn.close()


def add_inventory_item(name, brand, qty, category, image_path=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO inventory (name, brand, qty, status, category, image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (name, brand, qty, _status_from_qty(qty), category, image_path),
        )
        item_id = cursor.lastrowid
        if _column_exists(cursor, "inventory", "item_name"):
            cursor.execute("UPDATE inventory SET item_name = %s WHERE id = %s", (name, item_id))
        if _column_exists(cursor, "inventory", "quantity"):
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (qty, item_id))
        conn.commit()
    finally:
        conn.close()


def update_inventory_item(item_id, name, brand, qty, category, image_path=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE inventory
            SET name = %s, brand = %s, qty = %s, status = %s, category = %s, image_path = %s
            WHERE id = %s
            """,
            (name, brand, qty, _status_from_qty(qty), category, image_path, item_id),
        )
        if _column_exists(cursor, "inventory", "item_name"):
            cursor.execute("UPDATE inventory SET item_name = %s WHERE id = %s", (name, item_id))
        if _column_exists(cursor, "inventory", "quantity"):
            cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (qty, item_id))
        conn.commit()
    finally:
        conn.close()


def delete_inventory_item(item_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id = %s", (item_id,))
        conn.commit()
    finally:
        conn.close()


def add_request(student_name, items, purpose):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO requests (student_name, items_json, purpose, status, created_at)
            VALUES (%s, %s, %s, 'PENDING', %s)
            """,
            (student_name, json.dumps(items), purpose, datetime.now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_requests():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, student_name, items_json, purpose, status, created_at, approved_by, returned_by
            FROM requests
            ORDER BY id DESC
            """
        )
        return _fetchall_tuples(cursor)
    finally:
        conn.close()


def update_request_status(request_id, status, acted_by=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if status == "RETURNED":
            cursor.execute(
                "UPDATE requests SET status = %s, returned_by = %s WHERE id = %s",
                (status, acted_by, request_id),
            )
        elif status in ["APPROVED", "REJECTED"]:
            cursor.execute(
                "UPDATE requests SET status = %s, approved_by = %s WHERE id = %s",
                (status, acted_by, request_id),
            )
        else:
            cursor.execute("UPDATE requests SET status = %s WHERE id = %s", (status, request_id))
        conn.commit()
    finally:
        conn.close()


def deduct_stock(item_name, qty):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT qty FROM inventory WHERE name = %s LIMIT 1", (item_name,))
        row = _fetchone_dict(cursor)
        if row is None:
            return

        new_qty = max(0, int(row["qty"]) - int(qty))
        cursor.execute(
            "UPDATE inventory SET qty = %s, status = %s WHERE name = %s",
            (new_qty, _status_from_qty(new_qty), item_name),
        )
        conn.commit()
    finally:
        conn.close()


def return_item(item_name, qty):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT qty FROM inventory WHERE name = %s LIMIT 1", (item_name,))
        row = _fetchone_dict(cursor)
        current_qty = int(row["qty"]) if row else 0
        new_qty = current_qty + int(qty)
        cursor.execute(
            "UPDATE inventory SET qty = %s, status = %s WHERE name = %s",
            (new_qty, _status_from_qty(new_qty), item_name),
        )
        conn.commit()
    finally:
        conn.close()


def add_user(username, email, password, role="Staff"):
    success, _ = create_user_account(username, email, password, role=role)
    return success


def update_admin_credentials(username, email, password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET username = %s, email = %s, password = %s, role = 'Admin'
            WHERE id = 1
            """,
            (username, email, password),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_all_users():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users ORDER BY id")
        return _fetchall_tuples(cursor)
    finally:
        conn.close()


def delete_user(user_id):
    if int(user_id) == 1:
        return False

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()








