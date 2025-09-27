import streamlit as st
import mysql.connector
import pandas as pd
import hashlib

# ------------------- Database connection -------------------
def create_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='yOUR PASSWORD',
        database='AirportManagement'
    )

# ------------------- Password hashing -------------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# ------------------- Users -------------------
def register_user(username, pwd, role):
    hashed_password = hash_password(pwd)
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, pwd, role) VALUES (%s, %s, %s)",
            (username, hashed_password, role)
        )
        conn.commit()
        conn.close()
        return True
    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return False

def login_user(username, pwd):
    hashed_password = hash_password(pwd)
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role FROM users WHERE username = %s AND pwd = %s",
        (username, hashed_password)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ------------------- CRUD functions -------------------
def record_exists(table, id_column, id_value):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT 1 FROM {table} WHERE {id_column} = %s', (id_value,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def insert_record(table, **kwargs):
    conn = create_connection()
    cursor = conn.cursor()
    columns = ', '.join(kwargs.keys())
    placeholders = ', '.join(['%s'] * len(kwargs))
    cursor.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', tuple(kwargs.values()))
    conn.commit()
    conn.close()

def read_records(table):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {table}')
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return rows, columns

def update_record(table, id_column, id_value, **kwargs):
    if not record_exists(table, id_column, id_value):
        return False
    conn = create_connection()
    cursor = conn.cursor()
    updates = ', '.join([f'{k} = %s' for k in kwargs])
    cursor.execute(f'UPDATE {table} SET {updates} WHERE {id_column} = %s', (*kwargs.values(), id_value))
    conn.commit()
    conn.close()
    return True

def delete_record(table, id_column, id_value):
    if not record_exists(table, id_column, id_value):
        return False
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(f'DELETE FROM {table} WHERE {id_column} = %s', (id_value,))
    conn.commit()
    conn.close()
    return True

# ------------------- Streamlit App -------------------
def main():
    st.set_page_config(page_title="Airport Management", layout="wide")
    st.title("✈️ Airport Ticket Booking Management")

    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None

    # ------------------- Login/Register -------------------
    if not st.session_state["logged_in"]:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                if submit:
                    role = login_user(username, pwd)
                    if role:
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = role
                        st.success(f"Welcome {username}! Role: {role}")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")

        with tab2:
            with st.form("register_form"):
                username = st.text_input("New Username")
                pwd = st.text_input("Password", type="password")
                confirm_pwd = st.text_input("Confirm Password", type="password")
                role_code = st.text_input("Role Code")
                submit_reg = st.form_submit_button("Register")
                if submit_reg:
                    if pwd != confirm_pwd:
                        st.error("Passwords do not match")
                    else:
                        role = {"EMP800": "Employee", "Exec900": "Manager", "BM264": "Board Member"}.get(role_code)
                        if not role:
                            st.error("Invalid role code")
                        elif register_user(username, pwd, role):
                            st.success("Registration successful! Please login now")
                        else:
                            st.error("Username already exists")

    # ------------------- Logged In -------------------
    else:
        st.sidebar.success(f"Logged in as {st.session_state['username']} ({st.session_state['role']})")
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = None
            st.session_state["role"] = None
            st.rerun()

        role = st.session_state["role"]
        if role == "Employee":
            tables = ["PAYMENT", "PASSENGER", "BOOKING", "FLIGHT", "TICKET", "AIRPORT"]
        else:
            tables = ["AIRPORT", "PAYMENT", "PASSENGER", "AIRLINE", "BOOKING", "FLIGHT", "TICKET"]

        st.sidebar.header("Operations")
        operation = st.sidebar.radio("Action", ["Create", "Read", "Update", "Delete"])
        table = st.sidebar.selectbox("Select Table", tables)

        # Fields for each table
        fields = {
            "AIRPORT": ["AID", "AIRPORT_NAME", "CITY", "AREA", "ACOUNTRY", "TIMEZONE", "NO_OF_TERMINALS"],
            "PAYMENT": ["PAYID", "PAYDATE", "PAYABLE_AMOUNT", "PAY_METHOD", "PAYMENT_STATUS"],
            "PASSENGER": ["PID", "NAME", "PHONE", "EMAIL", "DOB", "AGE", "PASSPORTNO", "ADDRESS", "NATIONALITY"],
            "AIRLINE": ["AIRLINEID", "AIRLINENAME", "HELPLINENO", "COUNTRY", "ACODE"],
            "BOOKING": ["BID", "BDATE", "BSTATUS", "AMOUNT", "PAYMENTSTATUS", "PID", "PAYID", "NO_OF_SEATS"],
            "FLIGHT": ["FID", "FNO", "DEPARTURE", "ARRIVAL", "STATUS", "AIRLINEID"],
            "TICKET": ["TICKET_ID", "SEAT_NO", "CLASS", "BID", "FID", "AID", "AIRLINEID", "PID", "DEPARTING_FROM", "ARRIVING_AT"]
        }

        # ------------------- CRUD Operations -------------------
        if operation == "Create":
            st.subheader(f"Add Record to {table}")
            with st.form("create_form"):
                data = {field: st.text_input(f"{field}") for field in fields[table]}
                submit = st.form_submit_button("Add")
                if submit:
                    insert_record(table, **data)
                    st.success("Record added successfully!")

        elif operation == "Read":
            st.subheader(f"Records in {table}")
            records, columns = read_records(table)
            df = pd.DataFrame(records, columns=columns)
            st.dataframe(df, use_container_width=True)

        elif operation == "Update":
            st.subheader(f"Update Record in {table}")
            with st.form("update_form"):
                id_column = st.selectbox("Primary Key", fields[table])
                id_value = st.text_input("Enter ID Value")
                update_data = {field: st.text_input(f"New {field}") for field in fields[table] if field != id_column}
                submit = st.form_submit_button("Update")
                if submit:
                    if update_record(table, id_column, id_value, **update_data):
                        st.success("Record updated safely!")
                    else:
                        st.error("Record not found")

        elif operation == "Delete":
            st.subheader(f"Delete Record from {table}")
            with st.form("delete_form"):
                id_column = st.selectbox("Primary Key", fields[table])
                id_value = st.text_input("Enter ID Value")
                submit = st.form_submit_button("Delete")
                if submit:
                    if delete_record(table, id_column, id_value):
                        st.success("Record deleted successfully!")
                    else:
                        st.error("Record not found")

if __name__ == "__main__":
    main()
