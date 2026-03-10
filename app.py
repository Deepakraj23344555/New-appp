import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
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
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
        """)
        self.conn.commit()

    def save_scan(self, username, company_name, score, risk):
        query = "INSERT INTO scans (username, company_name, bankability_score, risk_classification, scan_date) VALUES (?, ?, ?, ?, ?)"
        self.conn.execute(query, (username, company_name, score, risk, datetime.datetime.now()))
        self.conn.commit()

    def get_history(self, username):
        return pd.read_sql_query("SELECT company_name, bankability_score, risk_classification, scan_date FROM scans WHERE username=? ORDER BY scan_date DESC", self.conn, params=(username,))

    def create_user(self, username, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_pw))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False 

    def verify_user(self, username, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        cursor = self.conn.execute("SELECT username FROM users WHERE username=? AND password_hash=?", (username, hashed_pw))
        if cursor.fetchone():
            return True
        return False

# ==========================================
# 2. FINANCIAL ENGINE
# ==========================================
class FinancialEngine:
    def __init__(self, data):
        self.raw_data = dict(zip(data['Metric'], data['Value']))
        self.extract_metrics()

    def extract_metrics(self):
        self.current_assets = self.raw_data.get('Current Assets', 0)
        self.current_liabilities = self.raw_data.get('Current Liabilities', 0)
        self.inventory = self.raw_data.get('Inventory', 0)
        self.total_liabilities = self.raw_data.get('Total Liabilities', 0)
        self.total_equity = self.raw_data.get('Total Equity', 0)
        self.net_income = self.raw_data.get('Net Income', 0)
        self.revenue = self.raw_data.get('Revenue', 0)
        self.total_assets = self.raw_data.get('Total Assets', 0)
        self.ebit = self.raw_data.get('EBIT', 0)
        self.retained_earnings = self.raw_data.get('Retained Earnings', 0)
        self.interest_expense = self.raw_data.get('Interest Expense', 0)
        
        self.working_capital = self.current_assets - self.current_liabilities
        self.total_debt = self.total_liabilities 

    def calculate_ratios(self, apply_stress=False, revenue_drop=0.0, rate_hike=0.0):
        rev = self.revenue * (1 - revenue_drop)
        revenue_loss = self.revenue - rev
        added_interest = self.total_debt * rate_hike
        ni = self.net_income - revenue_loss - added_interest
        
        current_ratio = self.current_assets / self.current_liabilities if self.current_liabilities else 0
        quick_ratio = (self.current_assets - self.inventory) / self.current_liabilities if self.current_liabilities else 0
        debt_to_equity = self.total_liabilities / self.total_equity if self.total_equity else 0
        net_profit_margin = ni / rev if rev else 0
        roa = ni / self.total_assets if self.total_assets else 0

        x1 = self.working_capital / self.total_assets if self.total_assets else 0
        x2 = self.retained_earnings / self.total_assets if self.total_assets else 0
        x3 = self.ebit / self.total_assets if self.total_assets else 0
        x4 = self.total_equity / self.total_liabilities if self.total_liabilities else 0
        x5 = rev / self.total_assets if self.total_assets else 0
        
        z_score = (0.717 * x1) + (0.847 * x2) + (3.107 * x3) + (0.420 * x4) + (0.998 * x5)

        return {
            "Current Ratio": current_ratio,
            "Quick Ratio": quick_ratio,
            "Debt-to-Equity": debt_to_equity,
            "Net Profit Margin": net_profit_margin,
            "ROA": roa,
            "Altman Z-Score": z_score
        }

    def calculate_bankability(self, ratios):
        score = 0
        if ratios["Current Ratio"] >= 1.5: score += 20
        elif ratios["Current Ratio"] >= 1.0: score += 10
        
        if 0 < ratios["Debt-to-Equity"] <= 1.5: score += 20
        elif 1.5 < ratios["Debt-to-Equity"] <= 2.5: score += 10
        
        if ratios["Net Profit Margin"] >= 0.10: score += 20
        elif ratios["Net Profit Margin"] > 0.0: score += 10
        
        if ratios["ROA"] >= 0.05: score += 20
        elif ratios["ROA"] > 0.0: score += 10
        
        if ratios["Altman Z-Score"] > 2.9: score += 20
        elif ratios["Altman Z-Score"] > 1.23: score += 10
        
        return score

    def get_risk_classification(self, score):
        if score >= 80: return "Low Risk", "Highly Ready for Loan processing."
        elif score >= 50: return "Moderate Risk", "Requires collateral or structural review."
        else: return "High Risk", "Not recommended for standard lending at this time."

# ==========================================
# 3. REPORT GENERATOR
# ==========================================
class ReportGenerator:
    @staticmethod
    def generate_pdf(company_name, score, risk, rec, ratios):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=f"MSME Financial Health Report: {company_name}", ln=True, align='C')
        
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Bankability Score: {score}/100", ln=True)
        pdf.cell(200, 10, txt=f"Risk Classification: {risk}", ln=True)
        pdf.cell(200, 10, txt=f"Recommendation: {rec}", ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Key Financial Metrics:", ln=True)
        pdf.set_font("Arial", size=12)
        
        for metric, value in ratios.items():
            pdf.cell(200, 10, txt=f"{metric}: {value:.2f}", ln=True)
            
        return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 4. PERFORMANCE & STATE OPTIMIZATION
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

# ==========================================
# 5. STREAMLIT UI & NAVIGATION
# ==========================================
st.set_page_config(page_title="MSME Scanner", layout="wide")
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
            if db.verify_user(l_user, l_pass):
                st.session_state.logged_in = True
                st.session_state.username = l_user
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
    st.stop() 

# --- MAIN APPLICATION UI ---
st.sidebar.title(f"Welcome, {st.session_state.username}")

page = st.sidebar.radio("Navigation", ["Scanner Dashboard", "Scan History"])

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# --- PAGE: SCANNER DASHBOARD ---
if page == "Scanner Dashboard":
    st.title("MSME Financial Health Scanner")
    st.markdown("Upload your structured Excel file to analyze balance sheets and P&L statements.")
    
    company_name = st.text_input("Company Name")
    uploaded_file = st.file_uploader("Upload Financial Data (Excel)", type=["xlsx", "xls"])
    
    if uploaded_file and company_name:
        try:
            df = load_excel_data(uploaded_file)
            
            if 'current_file' not in st.session_state or st.session_state.current_file != uploaded_file.name:
                engine = FinancialEngine(df)
                st.session_state.base_ratios = engine.calculate_ratios()
                st.session_state.base_score = engine.calculate_bankability(st.session_state.base_ratios)
                st.session_state.risk_level, st.session_state.rec = engine.get_risk_classification(st.session_state.base_score)
                
                st.session_state.stress_ratios = engine.calculate_ratios(apply_stress=True, revenue_drop=0.10, rate_hike=0.02)
                st.session_state.stress_score = engine.calculate_bankability(st.session_state.stress_ratios)
                st.session_state.current_file = uploaded_file.name
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Bankability Score")
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = st.session_state.base_score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': st.session_state.risk_level},
                    gauge = {
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 49], 'color': "red"},
                            {'range': [50, 79], 'color': "yellow"},
                            {'range': [80, 100], 'color': "green"}],
                    }
                ))
                st.plotly_chart(fig, use_container_width=True)
                st.info(f"**Recommendation:** {st.session_state.rec}")
            
            with col2:
                st.subheader("Key Ratios & Metrics")
                metrics_df = pd.DataFrame(list(st.session_state.base_ratios.items()), columns=["Metric", "Value"])
                metrics_df["Value"] = metrics_df["Value"].round(2)
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)
                
            st.markdown("---")
            st.subheader("Stress Test Simulation")
            st.markdown("Simulate a **10% revenue drop** and a **2% interest rate increase**.")
            st.metric("Stress-Tested Score", value=f"{st.session_state.stress_score}/100", 
                      delta=f"{st.session_state.stress_score - st.session_state.base_score} pts", delta_color="normal")
            
            st.markdown("---")
            st.subheader("Actions")
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("Save Results to Database"):
                    db.save_scan(st.session_state.username, company_name, st.session_state.base_score, st.session_state.risk_level)
                    st.success("Scan saved successfully!")
            
            with col_b:
                pdf_bytes = ReportGenerator.generate_pdf(company_name, st.session_state.base_score, st.session_state.risk_level, st.session_state.rec, st.session_state.base_ratios)
                st.download_button(label="Download PDF Report", data=pdf_bytes, file_name=f"{company_name}_report.pdf", mime="application/pdf")
                
        except Exception as e:
            st.error(f"Error processing file. Please ensure it matches the required format. Details: {e}")

# --- PAGE: SCAN HISTORY ---
elif page == "Scan History":
    st.title("Your Scan History")
    history_df = db.get_history(st.session_state.username)
    if not history_df.empty:
        st.dataframe(history_df, hide_index=True, use_container_width=True)
    else:
        st.write("No scan history found.")
