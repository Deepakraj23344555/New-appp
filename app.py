import streamlit as st
import pandas as pd
import sqlite3
import datetime
from fpdf import FPDF
import plotly.graph_objects as go

# ==========================================
# 1. DATABASE MANAGEMENT
# ==========================================
class DatabaseManager:
    def __init__(self, db_name="msme_health.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            bankability_score REAL,
            risk_classification TEXT,
            scan_date TIMESTAMP
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def save_scan(self, company_name, score, risk):
        query = "INSERT INTO scans (company_name, bankability_score, risk_classification, scan_date) VALUES (?, ?, ?, ?)"
        self.conn.execute(query, (company_name, score, risk, datetime.datetime.now()))
        self.conn.commit()

    def get_history(self):
        return pd.read_sql_query("SELECT * FROM scans ORDER BY scan_date DESC", self.conn)

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
# 4. PERFORMANCE OPTIMIZATION (CACHING)
# ==========================================
@st.cache_data(show_spinner="Parsing Financials...")
def load_excel_data(file):
    """Caches the heavy Excel reading process."""
    return pd.read_excel(file)

@st.cache_resource
def get_db_connection():
    """Ensures only one database connection is spun up per session."""
    return DatabaseManager()

# ==========================================
# 5. STREAMLIT UI & STATE MANAGEMENT
# ==========================================
st.set_page_config(page_title="MSME Scanner", layout="wide")
db = get_db_connection()

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Scanner Dashboard", "Scan History"])

if page == "Scanner Dashboard":
    st.title("MSME Financial Health & Loan Readiness Scanner")
    st.markdown("Upload your structured Excel file to analyze balance sheets and P&L statements.")
    
    company_name = st.text_input("Company Name")
    uploaded_file = st.file_uploader("Upload Financial Data (Excel)", type=["xlsx", "xls"])
    
    if uploaded_file and company_name:
        try:
            # 1. Load Data (Instant if cached)
            df = load_excel_data(uploaded_file)
            
            # 2. State Management: Only calculate if it's a new file
            if 'current_file' not in st.session_state or st.session_state.current_file != uploaded_file.name:
                engine = FinancialEngine(df)
                st.session_state.base_ratios = engine.calculate_ratios()
                st.session_state.base_score = engine.calculate_bankability(st.session_state.base_ratios)
                st.session_state.risk_level, st.session_state.rec = engine.get_risk_classification(st.session_state.base_score)
                
                # Pre-calculate stress test
                st.session_state.stress_ratios = engine.calculate_ratios(apply_stress=True, revenue_drop=0.10, rate_hike=0.02)
                st.session_state.stress_score = engine.calculate_bankability(st.session_state.stress_ratios)
                st.session_state.current_file = uploaded_file.name
            
            # 3. Render UI from Session State (Extremely fast)
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
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Save Results to Database"):
                    db.save_scan(company_name, st.session_state.base_score, st.session_state.risk_level)
                    st.success("Scan saved successfully!")
            with col_b:
                pdf_bytes = ReportGenerator.generate_pdf(company_name, st.session_state.base_score, st.session_state.risk_level, st.session_state.rec, st.session_state.base_ratios)
                st.download_button(label="Download PDF Report", data=pdf_bytes, file_name=f"{company_name}_report.pdf", mime="application/pdf")
                
        except Exception as e:
            st.error(f"Error processing file. Please ensure it matches the required format. Details: {e}")

elif page == "Scan History":
    st.title("Scan History")
    history_df = db.get_history()
    if not history_df.empty:
        st.dataframe(history_df, hide_index=True, use_container_width=True)
    else:
        st.write("No scan history found.")
