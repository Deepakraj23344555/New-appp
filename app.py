import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import razorpay
from fpdf import FPDF
import plotly.graph_objects as go

# ==========================================
# 1. DATABASE & AUTH MANAGEMENT
# ==========================================
class DatabaseManager:
    def __init__(self, db_name="msme_health.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        # Scan History Table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            company_name TEXT,
            bankability_score REAL,
            risk_classification TEXT,
            scan_date TIMESTAMP
        )
        """)
        # Users Table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            is_paid INTEGER DEFAULT 0
        )
        """)
        self.conn.commit()

    def save_scan(self, username, company_name, score, risk):
        query = "INSERT INTO scans (username, company_name, bankability_score, risk_classification, scan_date) VALUES (?, ?, ?, ?, ?)"
        self.conn.execute(query, (username, company_name, score, risk, datetime.datetime.now()))
        self.conn.commit()

    def get_history(self, username):
        return pd.read_sql_query("SELECT company_name, bankability_score, risk_classification, scan_date FROM scans WHERE username=? ORDER BY scan_date DESC", self.conn, params=(username,))

    # User Auth Methods
    def create_user(self, username, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_pw))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # Username exists

    def verify_user(self, username, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cursor = self.conn.execute("SELECT is_paid FROM users WHERE username=? AND password_hash=?", (username, hashed_pw))
        result = cursor.fetchone()
        if result:
            return {"authenticated": True, "is_paid": bool(result[0])}
        return {"authenticated": False, "is_paid": False}

    def upgrade_user(self, username):
        self.conn.execute("UPDATE users SET is_paid=1 WHERE username=?", (username,))
        self.conn.commit()

# ==========================================
# 2. FINANCIAL & REPORT ENGINE (Abstracted for brevity)
# ==========================================
# [Keep your existing FinancialEngine and ReportGenerator classes here exactly as they were in V2]
class FinancialEngine:
    # ... (Insert V2 logic here) ...
    pass

class ReportGenerator:
    # ... (Insert V2 logic here) ...
    pass

# ==========================================
# 3. PERFORMANCE & STATE OPTIMIZATION
# ==========================================
@st.cache_data(show_spinner="Parsing Financials...")
def load_excel_data(file):
    return pd.read_excel(file)

@st.cache_resource
def get_db_connection():
    return DatabaseManager()

def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.is_paid = False

# ==========================================
# 4. STREAMLIT UI & NAVIGATION
# ==========================================
st.set_page_config(page_title="MSME Scanner PRO", layout="wide")
db = get_db_connection()
init_session()

# --- AUTHENTICATION UI ---
if not st.session_state.logged_in:
    st.title("MSME Financial Health Scanner")
    st.markdown("Please log in or sign up to access the application.")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        l_user = st.text_input("Username", key="l_user")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            auth_data = db.verify_user(l_user, l_pass)
            if auth_data["authenticated"]:
                st.session_state.logged_in = True
                st.session_state.username = l_user
                st.session_state.is_paid = auth_data["is_paid"]
                st.rerun()
            else:
                st.error("Invalid credentials.")
                
    with tab2:
        s_user = st.text_input("Choose Username", key="s_user")
        s_pass = st.text_input("Choose Password", type="password", key="s_pass")
        if st.button("Create Account"):
            if db.create_user(s_user, s_pass):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists.")
    st.stop() # Halt execution here if not logged in

# --- MAIN APPLICATION UI ---
st.sidebar.title(f"Welcome, {st.session_state.username}")
if st.session_state.is_paid:
    st.sidebar.success("PRO Member")
else:
    st.sidebar.warning("Free Member")

page = st.sidebar.radio("Navigation", ["Scanner Dashboard", "Scan History", "Upgrade to PRO"])

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.is_paid = False
    st.rerun()

# --- PAGE: SCANNER DASHBOARD ---
if page == "Scanner Dashboard":
    st.title("MSME Financial Health Scanner")
    # ... [Insert your existing file upload and gauge chart UI here] ...
    
    # Example Paywall implementation inside your results block:
    # After generating base_score, risk_level, rec, base_ratios:
    
    st.markdown("---")
    st.subheader("Actions")
    
    # Anyone can save
    # if st.button("Save Results to Database"):
    #    db.save_scan(st.session_state.username, company_name, base_score, risk_level)
    
    # Paywall for PDF
    if st.session_state.is_paid:
        # pdf_bytes = ReportGenerator.generate_pdf(...)
        # st.download_button(label="Download PDF Report", data=pdf_bytes, file_name=f"report.pdf", mime="application/pdf")
        st.success("Download unlocked.")
    else:
        st.info("🔒 Premium Feature. Please upgrade to download full PDF reports.")

# --- PAGE: SCAN HISTORY ---
elif page == "Scan History":
    st.title("Your Scan History")
    history_df = db.get_history(st.session_state.username)
    if not history_df.empty:
        st.dataframe(history_df, hide_index=True, use_container_width=True)
    else:
        st.write("No scan history found.")

# --- PAGE: UPGRADE TO PRO (RAZORPAY) ---
elif page == "Upgrade to PRO":
    st.title("Upgrade to PRO")
    
    if st.session_state.is_paid:
        st.success("You are already a PRO member. Enjoy unlimited PDF downloads!")
    else:
        st.markdown("""
        ### Unlock Full Reporting
        1. **Pay ₹999** via our secure Razorpay link.
        2. Copy your **Payment ID** (starts with `pay_...`) from the receipt.
        3. Paste it below to instantly unlock your account.
        """)
        
        # Replace with your actual Razorpay Payment Link
        st.markdown("[👉 **Click Here to Pay via Razorpay**](https://rzp.io/l/your_payment_link_here)")
        
        st.markdown("---")
        payment_id = st.text_input("Enter your Razorpay Payment ID:")
        
        if st.button("Verify & Upgrade"):
            if not payment_id.startswith("pay_"):
                st.error("Invalid Payment ID format.")
            else:
                try:
                    # Initialize Razorpay Client (Use Streamlit Secrets in production)
                    # client = razorpay.Client(auth=(st.secrets["rzp_key_id"], st.secrets["rzp_key_secret"]))
                    
                    # Simulated Verification for prototype
                    # payment = client.payment.fetch(payment_id)
                    # if payment['status'] == 'captured':
                    
                    # For now, we will assume validation passed if it starts with 'pay_'
                    db.upgrade_user(st.session_state.username)
                    st.session_state.is_paid = True
                    st.success("Payment Verified! You are now a PRO member.")
                    st.rerun()
                        
                except Exception as e:
                    st.error(f"Payment verification failed: {e}")
