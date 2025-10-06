"""Main Streamlit application for the Multi-Bank Policy Comparator."""

import streamlit as st
import requests
import pandas as pd
from typing import List
import io
import time
import random
import os

from app.ui.components import show_document_details, show_processing_stats, show_fact_comparison_table
from app.ui.comparison_components import CompactComparisonTable
from app.ui.home_loan_components import show_home_loan_facts_summary, show_processing_progress, show_bank_selector, show_export_options
from app.ui.beautiful_comparison import show_beautiful_side_by_side_comparison
from app.services.export_service import ExportService

# Configure page
st.set_page_config(
    page_title="Bank Policy Comparator",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom header function
def show_custom_header():
    """Show a custom header to replace Streamlit's default header."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #2C5282 0%, #1A365D 100%);
            color: white;
            padding: 1rem;
            margin: -1rem -1rem 2rem -1rem;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
        ">
            <div style="
                display: flex; 
                align-items: center; 
                gap: 1rem; 
                flex: 1; 
                min-width: 280px;
            ">
                <div style="
                    background: #F6D55C;
                    color: #1A365D;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    font-weight: bold;
                    flex-shrink: 0;
                ">🏦</div>
                <div style="flex: 1; min-width: 0;">
                    <h1 style="
                        margin: 0; 
                        font-size: 1.4rem; 
                        font-weight: 700; 
                        color: #FFFFFF !important; 
                        line-height: 1.2;
                        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    ">Bank Policy Comparator</h1>
                    <div style="
                        margin: 0; 
                        font-size: 0.85rem; 
                        color: #FFFFFF !important; 
                        line-height: 1.2;
                        background: rgba(255, 255, 255, 0.1);
                        padding: 0.3rem 0.6rem;
                        border-radius: 12px;
                        font-weight: 500;
                        display: inline-block;
                    ">AI-Powered Document Analysis</div>
                </div>
            </div>
            <div style="
                background: rgba(255, 255, 255, 0.2);
                padding: 0.5rem 1rem;
                border-radius: 20px;
                font-size: 0.8rem;
                color: #FFFFFF !important;
                font-weight: 500;
                flex-shrink: 0;
                white-space: nowrap;
                border: 1px solid rgba(255, 255, 255, 0.1);
            ">
                ✨ Smart Comparison
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Modern theming
def apply_modern_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        /* Hide Streamlit's default header and toolbar - Streamlit compliant */
        header[data-testid="stHeader"] {
          display: none !important;
        }
        
        .stDeployButton {
          display: none !important;
        }
        
        div[data-testid="stDecoration"] {
          display: none !important;
        }
        
        div[data-testid="stToolbar"] {
          display: none !important;
        }
        
        .stMainBlockContainer {
          padding-top: 0 !important;
        }
        
        /* Remove top padding from the app */
        .stApp {
          margin-top: 0 !important;
          padding-top: 0 !important;
        }
        
        :root {
          /* Modern Brand Colors - Updated with Blue Theme */
          --primary: #F6D55C;        /* Signature golden yellow */
          --primary-dark: #ED8936;   /* Darker gold for hover */
          --secondary: #1A365D;      /* Deep blue for text */
          --dark: #2C5282;           /* Blue accent */
          --bg: #2C5282;             /* Blue gradient background */
          --card: #FFFFFF;           /* Pure white cards */
          --border: #E5E7EB;         /* Light border */
          --muted: #4A5568;          /* Muted text */
          --success: #10B981;        /* Success green */
          --error: #EF4444;          /* Error red */
          --warning: #F59E0B;        /* Warning orange */
          
          /* Status colors for comparison */
          --same-bg: #E6F3FF;               /* Light blue */
          --same-border: #2C5282;
          --diff-bg: #FEF2F2;              /* Light red */
          --diff-border: #EF4444;
          --miss-bg: #F9FAFB;              /* Light gray */
          --miss-border: #D1D5DB;
          --sus-bg: #FFFBEB;               /* Light yellow */
          --sus-border: #F59E0B;
        }
        
        /* Global Styling - Modern Blue Theme */
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
        .stApp { 
          background: linear-gradient(135deg, #2C5282 0%, #2A4A6B 50%, #1A365D 100%) !important;
          color: var(--secondary);
          min-height: 100vh !important;
        }
        
        /* Layout & Spacing - White card on blue background */
        .block-container { 
          background: rgba(255, 255, 255, 0.95) !important;
          border-radius: 20px !important;
          padding: 2rem !important;
          margin: 1rem !important;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1) !important;
          backdrop-filter: blur(10px) !important;
          max-width: 1200px !important;
        }
        
        /* Typography Hierarchy */
        h1 { 
          font-family: 'Inter', sans-serif !important;
          font-weight: 800 !important; 
          color: var(--dark) !important;
          font-size: 2.5rem !important;
          line-height: 1.2 !important;
          margin-bottom: 1rem !important;
        }
        h2 { 
          font-family: 'Inter', sans-serif !important;
          font-weight: 700 !important; 
          color: var(--dark) !important;
          font-size: 2rem !important;
          margin-bottom: 0.8rem !important;
        }
        h3 { 
          font-family: 'Inter', sans-serif !important;
          font-weight: 600 !important; 
          color: var(--dark) !important;
          font-size: 1.5rem !important;
        }
        h4, h5, h6 {
          font-family: 'Inter', sans-serif !important;
          font-weight: 600 !important;
          color: var(--dark) !important;
        }
        p, span, label, div { 
          font-family: 'Inter', sans-serif !important;
          color: var(--secondary) !important;
          line-height: 1.6 !important;
        }
        
        /* Modern Button Styling */
        .stButton > button {
          background: var(--primary) !important;
          color: var(--dark) !important;
          border: none !important;
          border-radius: 12px !important;
          font-weight: 600 !important;
          font-family: 'Inter', sans-serif !important;
          padding: 0.75rem 1.5rem !important;
          font-size: 0.95rem !important;
          transition: all 0.2s ease !important;
          box-shadow: 0 2px 4px rgba(255, 215, 0, 0.2) !important;
          min-height: 44px !important;
        }
        .stButton > button:hover {
          background: var(--primary-dark) !important;
          transform: translateY(-1px) !important;
          box-shadow: 0 4px 8px rgba(255, 215, 0, 0.3) !important;
        }
        .stButton > button:focus {
          outline: 2px solid var(--primary) !important;
          outline-offset: 2px !important;
        }
        
        /* Hero Section */
        .hero {
          background: linear-gradient(135deg, var(--primary) 0%, #F4C430 100%) !important;
          color: var(--dark) !important;
          border-radius: 20px !important;
          padding: 3rem 2rem !important;
          margin-bottom: 3rem !important;
          text-align: center !important;
          box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3) !important;
        }
        .hero h2 {
          color: var(--dark) !important;
          margin-bottom: 1rem !important;
          font-size: 2.5rem !important;
          font-weight: 800 !important;
        }
        .hero small {
          color: var(--secondary) !important;
          font-size: 1.1rem !important;
          opacity: 0.8 !important;
        }
        .accent-pill {
          background: var(--card) !important;
          color: var(--primary) !important;
          padding: 0.5rem 1rem !important;
          border-radius: 25px !important;
          font-weight: 700 !important;
          font-size: 0.9rem !important;
          display: inline-block !important;
          margin-bottom: 1rem !important;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* File Upload Styling */
        .stFileUploader > div {
          background: var(--card) !important;
          border: 2px dashed var(--border) !important;
          border-radius: 16px !important;
          padding: 2rem !important;
          transition: all 0.2s ease !important;
        }
        .stFileUploader > div:hover {
          border-color: var(--primary) !important;
          background: var(--bg) !important;
        }
        
        /* Data Frame Styling */
        .stDataFrame {
          border: 1px solid var(--border) !important;
          border-radius: 12px !important;
          overflow: hidden !important;
        }
        .stDataFrame thead tr th {
          background: var(--primary) !important;
          color: var(--dark) !important;
          font-weight: 600 !important;
          font-family: 'Inter', sans-serif !important;
          padding: 1rem !important;
        }
        .stDataFrame tbody tr td {
          padding: 0.8rem !important;
          border-bottom: 1px solid var(--border) !important;
        }
        .stDataFrame tbody tr:hover {
          background: var(--bg) !important;
        }
        
        /* Status Colors */
        .status-same { 
          background: var(--same-bg) !important; 
          border-left: 4px solid var(--same-border) !important; 
          color: var(--dark) !important;
        }
        .status-different { 
          background: var(--diff-bg) !important; 
          border-left: 4px solid var(--diff-border) !important; 
          color: var(--dark) !important;
        }
        .status-missing { 
          background: var(--miss-bg) !important; 
          border-left: 4px solid var(--miss-border) !important; 
          color: var(--muted) !important;
        }
        .status-suspect { 
          background: var(--sus-bg) !important; 
          border-left: 4px solid var(--sus-border) !important; 
          color: var(--dark) !important;
        }
        
        /* Sidebar Styling */
        .css-1d391kg { background: var(--card) !important; }
        
        /* Progress Bar */
        .stProgress > div > div > div {
          background: var(--primary) !important;
        }
        
        /* Select Box */
        .stSelectbox > div > div {
          border-radius: 8px !important;
          border: 1px solid var(--border) !important;
        }
        
        /* Text Input */
        .stTextInput > div > div > input {
          border-radius: 8px !important;
          border: 1px solid var(--border) !important;
          font-family: 'Inter', sans-serif !important;
        }
        .stTextInput > div > div > input:focus {
          border-color: var(--primary) !important;
          box-shadow: 0 0 0 1px var(--primary) !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
          background: var(--card) !important;
          border: 1px solid var(--border) !important;
          border-radius: 8px !important;
        }
        
        /* Custom spacing utilities */
        .mt-4 { margin-top: 2rem !important; }
        .mb-4 { margin-bottom: 2rem !important; }
        .p-4 { padding: 2rem !important; }
        
        /* Global text visibility fix - ensure white text on dark backgrounds */
        .stButton > button {
          color: #FFFFFF !important;
        }
        .stButton > button[kind="primary"] {
          color: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# Apply theme
apply_modern_theme()

# Show custom header
show_custom_header()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

def _show_hero():
    st.markdown(
        """
        <div class="hero">
          <div class="accent-pill">✨ AI-Powered Bank Comparison Tool</div>
          <h1 style="margin:0; color: var(--dark) !important;">Discover. Compare. Secure.</h1>
          <h2 style="margin:0.5rem 0 1.5rem 0; color: var(--dark) !important;">Your Perfect Home Loan</h2>
          <p style="font-size: 1.2rem; margin-bottom: 2rem; color: var(--secondary) !important;">
            Upload loan documents from different banks and let our AI analyze them side-by-side. 
            Make smarter decisions with transparent comparisons.
          </p>
          <div style="background: rgba(255, 255, 255, 0.2); border-radius: 15px; padding: 1.5rem; margin-top: 1.5rem;">
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 1rem;">
              <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📤</div>
                <strong>Upload Documents</strong>
                <div style="font-size: 0.9rem; opacity: 0.8;">2-4 bank loan PDFs</div>
              </div>
              <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🤖</div>
                <strong>AI Analysis</strong>
                <div style="font-size: 0.9rem; opacity: 0.8;">Extract key terms & rates</div>
              </div>
              <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚖️</div>
                <strong>Smart Comparison</strong>
                <div style="font-size: 0.9rem; opacity: 0.8;">Side-by-side analysis</div>
              </div>
              <div style="text-align: center; flex: 1; min-width: 200px;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                <strong>Export Results</strong>
                <div style="font-size: 0.9rem; opacity: 0.8;">CSV/JSON reports</div>
              </div>
            </div>
          </div>
          <p style="margin-top: 1.5rem; font-size: 0.95rem; opacity: 0.7;">
            🔒 Secure processing • 📍 Evidence-backed results • ⚡ Lightning fast
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def show_processing_indicator(operation_type="processing", file_name=None, total_files=1):
    """Show a simple processing indicator without blocking animations."""
    
    # Fun facts and tips to show during processing
    fun_facts = [
        "💡 Did you know? Home loan interest rates can vary by up to 2% between different banks!",
        "🏠 Tip: Processing fees can range from 0.5% to 3% of your loan amount",
        "⚡ Fun fact: Our AI can extract 50+ key terms from a loan document in seconds",
        "📊 Smart tip: LTV ratios above 80% usually require additional insurance",
        "🎯 Did you know? Prepayment penalties can save or cost you thousands",
        "🤖 AI insight: We analyze clause patterns to detect hidden charges",
        "💰 Pro tip: Compare both fixed and floating rate options",
        "📈 Fact: Interest rate changes are usually communicated 30 days in advance",
        "🔍 Smart analysis: We cross-reference terms across multiple document sections",
        "⏰ Time saver: Manual comparison of 4 banks would take 2+ hours",
        "🏦 Did you know? Banks update their loan policies quarterly on average",
        "📋 Tip: Always check for hidden charges in the fine print",
        "🎯 Smart fact: Our AI reads documents 100x faster than humans",
        "💼 Pro tip: Compare total cost of ownership, not just interest rates",
        "🔒 Security: Your documents are processed locally and never stored",
        "📊 Insight: We analyze over 50 different loan parameters automatically",
        "⚡ Speed tip: Batch processing multiple documents saves significant time",
        "🏠 Fact: Home loan terms can vary significantly even within the same bank",
        "🤖 AI magic: We detect inconsistencies humans often miss",
        "💡 Smart comparison: We normalize different bank terminologies for you"
    ]
    
    if operation_type == "document":
        title = f"AI is Processing {file_name or 'document'}..."
        current_step = "🤖 AI analyzing loan terms..."
    else:  # comparison
        title = f"AI is Comparing {total_files} documents..."
        current_step = "⚖️ Generating intelligent comparison..."
    
    # Show processing header
    st.markdown(
        f"""
        <div style="text-align: center; background: linear-gradient(135deg, var(--primary) 0%, #F4C430 100%); 
                   border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem; 
                   box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);">
            <h3 style="margin: 0 0 0.5rem 0; color: var(--dark); font-weight: 700;">
                {title}
            </h3>
            <p style="margin: 0; color: var(--secondary); opacity: 0.8;">
                Sit back and relax while our AI works its magic ✨
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Show current processing step
    st.markdown(
        f"""
        <div style="background: var(--card); border-radius: 16px; padding: 1.5rem; 
                   border: 1px solid var(--border); margin-bottom: 1rem; text-align: center;">
            <div style="display: flex; align-items: center; justify-content: center; gap: 1rem;">
                <div style="width: 12px; height: 12px; background: var(--success); 
                           border-radius: 50%; animation: pulse 1.5s infinite;"></div>
                <h4 style="margin: 0; color: var(--dark);">{current_step}</h4>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Show a random tip
    current_tip = random.choice(fun_facts)
    st.markdown(
        f"""
        <div style="background: var(--same-bg); border-left: 4px solid var(--same-border); 
                   border-radius: 0 12px 12px 0; padding: 1rem; margin: 1rem 0;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.2rem;">💭</span>
                <span style="color: var(--dark); font-weight: 500;">
                    {current_tip}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Add CSS animation for pulse effect
    st.markdown(
        """
        <style>
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
            100% { opacity: 1; transform: scale(1); }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def show_rotating_facts_indicator(operation_type="processing", file_name=None, total_files=1, container=None):
    """Show a processing indicator with rotating facts for longer operations."""
    
    # Extended fun facts and tips
    fun_facts = [
        "💡 Did you know? Home loan interest rates can vary by up to 2% between different banks!",
        "🏠 Tip: Processing fees can range from 0.5% to 3% of your loan amount",
        "⚡ Fun fact: Our AI can extract 50+ key terms from a loan document in seconds",
        "📊 Smart tip: LTV ratios above 80% usually require additional insurance",
        "🎯 Did you know? Prepayment penalties can save or cost you thousands",
        "🤖 AI insight: We analyze clause patterns to detect hidden charges",
        "💰 Pro tip: Compare both fixed and floating rate options",
        "📈 Fact: Interest rate changes are usually communicated 30 days in advance",
        "🔍 Smart analysis: We cross-reference terms across multiple document sections",
        "⏰ Time saver: Manual comparison of 4 banks would take 2+ hours",
        "🏦 Did you know? Banks update their loan policies quarterly on average",
        "📋 Tip: Always check for hidden charges in the fine print",
        "🎯 Smart fact: Our AI reads documents 100x faster than humans",
        "💼 Pro tip: Compare total cost of ownership, not just interest rates",
        "🔒 Security: Your documents are processed locally and never stored",
        "📊 Insight: We analyze over 50 different loan parameters automatically",
        "⚡ Speed tip: Batch processing multiple documents saves significant time",
        "🏠 Fact: Home loan terms can vary significantly even within the same bank",
        "🤖 AI magic: We detect inconsistencies humans often miss",
        "💡 Smart comparison: We normalize different bank terminologies for you",
        "🎯 Pro insight: Fixed vs floating rates each have different risk profiles",
        "📈 Market tip: Interest rates are influenced by RBI policy changes",
        "🏦 Banking fact: Each bank has different risk assessment criteria",
        "💰 Money tip: Small rate differences compound to large amounts over time",
        "🔍 Analysis: We check for contradictions within the same document"
    ]
    
    if operation_type == "document":
        title = f"AI is Processing {file_name or 'document'}..."
        current_step = "🤖 AI analyzing loan terms..."
    else:  # comparison
        title = f"AI is Comparing {total_files} documents..."
        current_step = "⚖️ Generating intelligent comparison..."
    
    # Use provided container or create new one
    if container is None:
        container = st.empty()
    
    # Initialize fact rotation
    if 'current_fact_index' not in st.session_state:
        st.session_state.current_fact_index = 0
    
    # Rotate to next fact
    current_fact = fun_facts[st.session_state.current_fact_index % len(fun_facts)]
    st.session_state.current_fact_index += 1
    
    with container.container():
        # Show processing header
        st.markdown(
            f"""
            <div style="text-align: center; background: linear-gradient(135deg, var(--primary) 0%, #F4C430 100%); 
                       border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem; 
                       box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);">
                <h3 style="margin: 0 0 0.5rem 0; color: var(--dark); font-weight: 700;">
                    {title}
                </h3>
                <p style="margin: 0; color: var(--secondary); opacity: 0.8;">
                    Sit back and relax while our AI works its magic ✨
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Show current processing step
        st.markdown(
            f"""
            <div style="background: var(--card); border-radius: 16px; padding: 1.5rem; 
                       border: 1px solid var(--border); margin-bottom: 1rem; text-align: center;">
                <div style="display: flex; align-items: center; justify-content: center; gap: 1rem;">
                    <div style="width: 12px; height: 12px; background: var(--success); 
                               border-radius: 50%; animation: pulse 1.5s infinite;"></div>
                    <h4 style="margin: 0; color: var(--dark);">{current_step}</h4>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Show rotating fact with smooth transition
        st.markdown(
            f"""
            <div style="background: var(--same-bg); border-left: 4px solid var(--same-border); 
                       border-radius: 0 12px 12px 0; padding: 1rem; margin: 1rem 0;
                       animation: fadeIn 0.5s ease-in;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">💭</span>
                    <span style="color: var(--dark); font-weight: 500;">
                        {current_fact}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Add CSS animations
        st.markdown(
            """
            <style>
            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.7; transform: scale(1.1); }
                100% { opacity: 1; transform: scale(1); }
            }
            @keyframes fadeIn {
                0% { opacity: 0; transform: translateY(10px); }
                100% { opacity: 1; transform: translateY(0); }
            }
            </style>
            """,
            unsafe_allow_html=True
        )


def show_comparison_with_rotating_facts(loading_container, document_ids, total_files):
    """Show comparison processing with a visually distinct loading experience."""
    
    # Fun facts to show during processing
    fun_facts = [
        "Home loan interest rates can vary by up to 2% between different banks!",
        "Processing fees can range from 0.5% to 3% of your loan amount",
        "Our AI can extract 50+ key terms from a loan document in seconds",
        "LTV ratios above 80% usually require additional insurance",
        "Prepayment penalties can save or cost you thousands",
        "We analyze clause patterns to detect hidden charges",
        "Compare both fixed and floating rate options for best results",
        "Interest rate changes are usually communicated 30 days in advance",
        "We cross-reference terms across multiple document sections",
        "Manual comparison of 4 banks would take 2+ hours",
        "Each bank has different risk assessment criteria",
        "Small rate differences compound to large amounts over time"
    ]
    
    # Clear the loading container first
    loading_container.empty()
    
    # Select random facts for this session
    selected_facts = random.sample(fun_facts, min(4, len(fun_facts)))
    
    try:
        comparison_request = {
            "document_ids": document_ids
        }
        
        # Create a visually distinct loading experience
        st.markdown("### 🚀 AI is Processing Your Documents")
        
        # Show selected facts in an attractive format
        st.markdown("**💡 While you wait, here are some insights:**")
        
        for i, fact in enumerate(selected_facts, 1):
            if i == 1:
                st.success(f"**Tip {i}:** {fact}")
            elif i == 2:
                st.info(f"**Tip {i}:** {fact}")
            elif i == 3:
                st.warning(f"**Tip {i}:** {fact}")
            else:
                st.error(f"**Tip {i}:** {fact}")
        
        # Big visual separator
        st.markdown("---")
        
        # Use a different loading approach - progress bar with spinner
        progress_bar = st.progress(0, text="🔄 Initializing AI comparison engine...")
        
        # Update progress bar
        progress_bar.progress(25, text="📊 Extracting loan terms and conditions...")
        progress_bar.progress(50, text="🤖 Analyzing document patterns...")
        progress_bar.progress(75, text="⚖️ Cross-referencing and comparing...")
        
        # Final spinner for the actual API call
        with st.spinner("🧠 Generating intelligent comparison matrix..."):
            # Make the actual API call
            response = requests.post(
                f"{API_BASE_URL}/comparison/compare",
                json=comparison_request
            )
        
        # Clear progress bar
        progress_bar.empty()
        
        if response.status_code == 200:
            comparison_data = response.json()
            
            # Success message
            st.success("🎉 **Comparison Generated Successfully!**")
            
            # Show comparison
            show_beautiful_side_by_side_comparison(comparison_data)
        else:
            st.error(f"❌ **Comparison Failed:** Status code {response.status_code}")
            
    except Exception as e:
        st.error(f"❌ **Error generating comparison:** {str(e)}")


def show_mega_loading_experience(loading_container, document_ids, total_files):
    """Show an over-the-top loading experience with multiple Streamlit widgets."""
    
    loading_container.empty()
    
    # Big header
    st.markdown("# 🤖 AI Processing Center")
    st.markdown("### Your documents are being analyzed by our advanced AI system")
    
    # Create columns for a dashboard-like experience
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Documents", total_files, "Processing")
        st.progress(100, text="✅ Upload Complete")
    
    with col2:
        st.metric("AI Models", "3", "Active")
        st.progress(75, text="🤖 Analysis Running")
    
    with col3:
        st.metric("Comparison", "0%", "Starting")
        st.progress(0, text="⏳ Queued")
    
    # Fun facts in different formats
    st.markdown("## 💡 Did You Know?")
    
    tab1, tab2, tab3 = st.tabs(["💰 Rates", "📊 Fees", "🎯 Tips"])
    
    with tab1:
        st.info("Home loan interest rates can vary by up to 2% between different banks!")
    
    with tab2:
        st.warning("Processing fees can range from 0.5% to 3% of your loan amount")
    
    with tab3:
        st.success("Our AI can extract 50+ key terms from a loan document in seconds")
    
    # The actual processing with a big spinner
    with st.spinner("🔄 **PROCESSING IN PROGRESS** - Please wait while our AI works..."):
        try:
            comparison_request = {"document_ids": document_ids}
            response = requests.post(f"{API_BASE_URL}/comparison/compare", json=comparison_request)
            
            if response.status_code == 200:
                st.success("# 🎉 SUCCESS!")
                comparison_data = response.json()
                show_beautiful_side_by_side_comparison(comparison_data)
            else:
                st.error(f"❌ Comparison failed: {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")



def show_demo_loading_with_delay():
    """Show the loading experience with a realistic delay for demo purposes."""
    
    # Fun facts to show during processing
    fun_facts = [
        "Home loan interest rates can vary by up to 2% between different banks!",
        "Processing fees can range from 0.5% to 3% of your loan amount",
        "Our AI can extract 50+ key terms from a loan document in seconds",
        "LTV ratios above 80% usually require additional insurance",
        "Prepayment penalties can save or cost you thousands",
        "We analyze clause patterns to detect hidden charges",
        "Compare both fixed and floating rate options for best results",
        "Interest rate changes are usually communicated 30 days in advance",
        "We cross-reference terms across multiple document sections",
        "Manual comparison of 4 banks would take 2+ hours"
    ]
    
    # Select random facts for this demo
    selected_facts = random.sample(fun_facts, min(4, len(fun_facts)))
    
    # Show the loading UI with the same styling as the real version
    st.markdown("### 🚀AI is Processing Demo Documents")
    
    # Show selected facts in an attractive format
    st.markdown("**💡 While you wait, here are some insights:**")
    
    for i, fact in enumerate(selected_facts, 1):
        if i == 1:
            st.success(f"**Tip {i}:** {fact}")
        elif i == 2:
            st.info(f"**Tip {i}:** {fact}")
        elif i == 3:
            st.warning(f"**Tip {i}:** {fact}")
        else:
            st.error(f"**Tip {i}:** {fact}")
    
    # Big visual separator
    st.markdown("---")
    
    # Show progress bar with realistic timing
    progress_bar = st.progress(0, text="🔄 Initializing AI comparison engine...")
    
    # Simulate realistic processing with delays
    time.sleep(1)
    progress_bar.progress(25, text="📊 Extracting loan terms and conditions...")
    
    time.sleep(1)
    progress_bar.progress(50, text="🤖 Analyzing document patterns...")
    
    time.sleep(1.5)
    progress_bar.progress(75, text="⚖️ Cross-referencing and comparing...")
    
    # Final spinner for the last bit
    with st.spinner("🧠 Generating intelligent comparison matrix..."):
        time.sleep(1.5)  # Final delay
    
    # Clear progress bar
    progress_bar.empty()
    
    # Success message
    st.success("🎉 **Demo Comparison Generated Successfully!**")


def show_enhanced_document_processing(loading_container, file_name, current_file, total_files):
    """Show enhanced loading experience for document processing with multiple tips."""
    
    # Fun facts to show during processing
    fun_facts = [
        "Home loan interest rates can vary by up to 2% between different banks!",
        "Processing fees can range from 0.5% to 3% of your loan amount",
        "Our AI can extract 50+ key terms from a loan document in seconds",
        "LTV ratios above 80% usually require additional insurance",
        "Prepayment penalties can save or cost you thousands",
        "We analyze clause patterns to detect hidden charges",
        "Compare both fixed and floating rate options for best results",
        "Interest rate changes are usually communicated 30 days in advance",
        "We cross-reference terms across multiple document sections",
        "Manual comparison of 4 banks would take 2+ hours",
        "Each bank has different risk assessment criteria",
        "Small rate differences compound to large amounts over time"
    ]
    
    # Clear the loading container first
    loading_container.empty()
    
    # Select random facts for this session
    selected_facts = random.sample(fun_facts, min(4, len(fun_facts)))
    
    with loading_container.container():
        # Create enhanced loading experience
        st.markdown(f"### 🤖AI is Processing {file_name}... ({current_file}/{total_files})")
        
        # Show selected facts in an attractive format
        st.markdown("**💡 While you wait, here are some insights:**")
        
        for i, fact in enumerate(selected_facts, 1):
            if i == 1:
                st.success(f"**Tip {i}:** {fact}")
            elif i == 2:
                st.info(f"**Tip {i}:** {fact}")
            elif i == 3:
                st.warning(f"**Tip {i}:** {fact}")
            else:
                st.error(f"**Tip {i}:** {fact}")
        
        # Big visual separator
        st.markdown("---")
        
        # Progress bar for current file
        progress = current_file / total_files
        st.progress(progress, text=f"🔄AI is Processing document {current_file} of {total_files}...")


def main():
    """Main application function - Simplified Upload & Compare."""
    _show_hero()
    
    # Single upload and compare flow
    show_simple_upload_and_compare()


def show_upload_page():
    """Show document upload interface."""
    st.header("📁 Document Upload")
    st.markdown("Upload your bank MITC documents for AI processing and comparison.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose MITC documents",
        type=['pdf', 'txt', 'docx'],
        accept_multiple_files=True,
        help="Supported formats: PDF, TXT, DOCX (max 10MB each)"
    )
    
    if uploaded_files:
        st.subheader("📄 Uploaded Files")
        
        # Display file information
        for file in uploaded_files:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{file.name}**")
            with col2:
                st.write(f"{file.size / 1024:.1f} KB")
            with col3:
                if st.button(f"Process", key=f"process_{file.name}"):
                    process_document(file)
    
    # Upload status area
    if 'upload_status' in st.session_state:
        st.subheader("📊 Processing Status")
        for status in st.session_state.upload_status:
            status_color = "green" if status['status'] == 'success' else "red"
            st.markdown(f":{status_color}[{status['filename']}: {status['message']}]")


def process_document(file):
    """Process an uploaded document with processing indicator."""
    # Create a container for the processing indicator
    loading_container = st.empty()
    
    try:
        # Show enhanced processing experience
        show_enhanced_document_processing(loading_container, file.name, 1, 1) # Assuming only one file for now
        
        # Prepare file for API request
        files = {"file": (file.name, file.getvalue(), file.type)}
        
        # Make API request (this is where the real processing happens)
        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
        
        # Clear loading widget after API call completes
        loading_container.empty()
        
        if response.status_code == 200:
            result = response.json()
            status = {
                'filename': file.name,
                'status': result['status'],
                'message': result['message'],
                'document_id': result.get('document_id')
            }
            st.success(f"✅ {file.name} processed successfully!")
        else:
            status = {
                'filename': file.name,
                'status': 'error',
                'message': f"Upload failed: {response.status_code}",
                'document_id': None
            }
            st.error(f"❌ Failed to process {file.name}")
        
        # Store status in session
        if 'upload_status' not in st.session_state:
            st.session_state.upload_status = []
        st.session_state.upload_status.append(status)
        
    except Exception as e:
        # Clear loading widget on error too
        loading_container.empty()
        st.error(f"❌ Error processing {file.name}: {str(e)}")


def show_document_management():
    """Show document management interface."""
    st.header("📚 Document Management")
    st.markdown("View and manage your uploaded documents.")
    
    # Placeholder for document list
    st.info("🔄 Document management features will be available once document storage is implemented.")
    
    # Mock document list for UI demonstration
    if st.checkbox("Show demo data"):
            demo_data = {
            'Document ID': ['doc-001', 'doc-002', 'doc-003'],
            'Filename': ['bank_a_mitc.pdf', 'bank_b_policy.txt', 'bank_c_terms.pdf'],
                'Bank': ['Bank A', 'Bank B', 'Bank C'],
                'Status': ['✅ Processed', '✅ Processed', '⏳ Processing'],
            'Upload Date': ['2024-01-15', '2024-01-16', '2024-01-17']
            }
            
            df = pd.DataFrame(demo_data)
            st.dataframe(df, use_container_width=True)


def show_comparison_page():
    """Show document comparison interface."""
    st.header("⚖️ Document Comparison")
    st.markdown("Compare multiple MITC documents side-by-side.")
    
    st.info("🔄 Document comparison features will be available in the next development phase.")
    
    # Mock comparison interface
    if st.checkbox("Show comparison mockup"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Select Documents")
            st.multiselect(
                "Choose documents to compare:",
                options=["Bank A MITC", "Bank B Policy", "Bank C Terms"],
                default=["Bank A MITC", "Bank B Policy"]
            )
        
        with col2:
            st.subheader("Comparison Fields")
            st.multiselect(
                "Select fields to compare:",
                options=["Interest Rates", "Fees", "Terms", "Penalties", "Benefits"],
                default=["Interest Rates", "Fees"]
            )
        
        if st.button("🔍 Start Comparison"):
            st.success("Comparison initiated! Results will appear in the Results page.")


def show_results_page():
    """Show comparison results."""
    st.header("📈 Comparison Results")
    st.markdown("View detailed comparison results and analysis.")
    
    st.info("🔄 Results will be displayed here once comparison functionality is implemented.")
    
    # Mock results for UI demonstration
    if st.checkbox("Show demo results"):
        st.subheader("📊 Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Same", "12", "+2")
        with col2:
            st.metric("Different", "8", "-1")
        with col3:
            st.metric("Missing", "3", "0")
        with col4:
            st.metric("Suspect", "2", "+1")
        
        st.subheader("🔍 Detailed Comparison")
        
        # Mock comparison results
        results_data = {
            'Field': ['Interest Rate', 'Annual Fee', 'Penalty Rate', 'Grace Period'],
            'Bank A': ['3.5%', '$95', '25%', '21 days'],
            'Bank B': ['3.2%', '$85', '25%', '25 days'],
            'Bank C': ['3.8%', 'No fee', '29%', '21 days'],
            'Status': ['🔴 Different', '🔴 Different', '🟡 Suspect', '🔴 Different']
        }
        
        df = pd.DataFrame(results_data)
        st.dataframe(df, use_container_width=True)
        
        # Evidence drill-down example
        st.subheader("🔍 Source Evidence")
        if st.button("Show evidence for Interest Rate"):
            st.text_area(
                "Bank A Source Text:",
                "The annual percentage rate (APR) for purchases is 3.5% based on your creditworthiness...",
                height=100
            )


def show_simple_upload_and_compare():
    """Simple upload and compare flow."""
    
    st.markdown("## 📤 Upload Home Loan Documents")
    st.markdown("Upload 2-4 home loan MITC documents from different banks for AI-powered comparison.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "📄 Select Home Loan MITC Documents",
        type=['pdf', 'txt', 'docx'],
        accept_multiple_files=True,
        help="Upload 2-4 home loan policy documents (PDF/TXT/DOCX, max 10MB each)"
    )
    
    if uploaded_files and len(uploaded_files) >= 2:
        st.success(f"✅ {len(uploaded_files)} documents uploaded successfully!")
        
        # Process documents
        if st.button("🚀 Process & Compare Documents", type="primary"):
            # Create container for processing indicator
            loading_container = st.empty()
            
            try:
                # Show enhanced processing experience
                show_enhanced_document_processing(loading_container, uploaded_files[0].name, 1, len(uploaded_files)) # Assuming only one file for now
                
                document_ids = []
                
                # Upload each document (real API calls)
                for i, file in enumerate(uploaded_files, 1):
                    try:
                        # Show enhanced processing experience
                        show_enhanced_document_processing(loading_container, file.name, i, len(uploaded_files))
                        
                        files = {"file": (file.name, file.getvalue(), file.type)}
                        response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('document_id'):
                                document_ids.append(result['document_id'])
                                st.success(f"✅ Processed: {file.name}")
                        else:
                            st.error(f"❌ Failed to process: {file.name}")
                    except Exception as e:
                        st.error(f"❌ Error processing {file.name}: {str(e)}")
                
                # Generate comparison if we have documents (another real API call)
                if len(document_ids) >= 2:
                    # Show comparison processing with multiple facts
                    show_comparison_with_rotating_facts(loading_container, document_ids, len(uploaded_files))
                else:
                    loading_container.empty()
                    st.error("❌ Need at least 2 successfully processed documents for comparison")
                    
            except Exception as e:
                loading_container.empty()
                st.error(f"❌ Unexpected error: {str(e)}")
    
    elif uploaded_files and len(uploaded_files) == 1:
        st.warning("⚠️ Please upload at least 2 documents for comparison")
    
    # Demo section
    st.markdown("---")
    st.markdown("## 🧪 Try Demo Comparison")
    st.markdown("See how the comparison works with sample data (no API calls)")
    
    if st.button("🎯 Show Demo Comparison", type="primary"):
        # Show the loading experience first
        show_demo_loading_with_delay()
        
        # Then show the comparison
        dummy_data = _get_dummy_comparison_data()
        show_beautiful_side_by_side_comparison(dummy_data)


def _get_dummy_comparison_data():
    """Get dummy comparison data for demo - expanded to show more realistic results."""
    return {
        "document_count": 3,
        "total_facts": 8,
        "same_facts": 3,
        "different_facts": 4,
        "missing_facts": 1,
        "suspect_facts": 0,
        "document_names": ["HDFC.pdf", "ICICI.pdf", "SBI.pdf"],
        "comparison_table": [
            {"section": "Processing Fees and Charges", "field": "Processing Fee", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "1.50% or ₹4,500 (whichever is minimum)", "confidence": 0.92, "source_text": "Processing fee shall be upto 1.50% of the loan amount or Rs. 4500 whichever is minimum. This fee is non-refundable and payable at the time of loan application.", "source_reference": "HDFC MITC Page 2, Section 3.1"},
              "ICICI.pdf": {"value": "0.50% to 3.00% of loan amount", "confidence": 0.87, "source_text": "Processing charges range from 0.50% to 3.00% of the loan amount as applicable based on the loan scheme and customer profile.", "source_reference": "ICICI Home Loan Terms Page 3, Clause 4.2"},
              "SBI.pdf": {"value": "1.00% + GST (Min ₹2,000, Max ₹10,000)", "confidence": 0.85, "source_text": "Processing fee: 1% of loan amount plus applicable GST. Minimum Rs. 2000 and maximum Rs. 10000.", "source_reference": "SBI Terms Page 1, Article 2.3"}
             }
            },
            {"section": "Interest Rates", "field": "Benchmark Rate", "comparison_status": "same",
             "documents": {
              "HDFC.pdf": {"value": "RPLR (Retail Prime Lending Rate)", "confidence": 0.95, "source_text": "Interest rate will be linked to Retail Prime Lending Rate (RPLR) as declared by the bank from time to time.", "source_reference": "HDFC MITC Page 1, Section 2.1"},
              "ICICI.pdf": {"value": "RPLR (Retail Prime Lending Rate)", "confidence": 0.93, "source_text": "The applicable interest rate shall be based on RPLR (Retail Prime Lending Rate) of ICICI Bank.", "source_reference": "ICICI Home Loan Terms Page 2, Clause 3.1"},
              "SBI.pdf": {"value": "RPLR (Retail Prime Lending Rate)", "confidence": 0.91, "source_text": "Interest rates are linked to SBI's Retail Prime Lending Rate (RPLR) and subject to periodic review.", "source_reference": "SBI Terms Page 2, Article 3.2"}
             }
            },
            {"section": "Interest Rates", "field": "Notification Method", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "www.hdfc.com and branch notice boards", "confidence": 0.88, "source_text": "Any changes in interest rates will be communicated through the bank's official website www.hdfc.com and displayed at branch notice boards.", "source_reference": "HDFC MITC Page 3, Section 4.2"},
              "ICICI.pdf": {"value": "Branch notification as per borrower address", "confidence": 0.82, "source_text": "Rate changes will be notified at the nearest loan servicing branch of ICICI Bank Limited/ICICI HFC as per the borrower's communication address.", "source_reference": "ICICI Home Loan Terms Page 4, Clause 5.3"},
              "SBI.pdf": {"value": "Newspaper publication or bank website", "confidence": 0.79, "source_text": "Changes in REPO rate are notified and published in a newspaper or in the website of the Bank/RBI.", "source_reference": "SBI Terms Page 3, Article 4.1"}
             }
            },
            {"section": "Prepayment and Foreclosure", "field": "Lock In Period", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "6 months (non-individuals)", "confidence": 0.90, "source_text": "Lock-in period: 6 months for non-individual borrowers. No prepayment charges for individual borrowers.", "source_reference": "HDFC MITC Page 4, Section 5.1"},
              "ICICI.pdf": {"value": "First 12 EMI period", "confidence": 0.86, "source_text": "Prepayment is not allowed during the first 12 EMI period. After this period, prepayment is allowed with applicable charges.", "source_reference": "ICICI Home Loan Terms Page 5, Clause 6.1"},
              "SBI.pdf": {"value": "Not found", "confidence": 0.0, "source_text": "", "source_reference": ""}
             }
            },
            {"section": "Prepayment and Foreclosure", "field": "Foreclosure Penalty", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "NIL for individuals, 2% for non-individuals", "confidence": 0.87, "source_text": "Foreclosure charges: NIL for individual borrowers. For non-individual borrowers: 2% of outstanding principal amount.", "source_reference": "HDFC MITC Page 4, Section 5.2"},
              "ICICI.pdf": {"value": "1% of outstanding principal (after lock-in)", "confidence": 0.84, "source_text": "Foreclosure charges: 1% of outstanding principal amount applicable after completion of lock-in period.", "source_reference": "ICICI Home Loan Terms Page 5, Clause 6.2"},
              "SBI.pdf": {"value": "NIL for floating rate loans", "confidence": 0.83, "source_text": "No foreclosure charges for floating rate home loans. Fixed rate loans may attract penalty as per terms.", "source_reference": "SBI Terms Page 4, Article 5.3"}
             }
            },
            {"section": "Eligibility Criteria", "field": "Minimum Income", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "₹25,000 per month (salaried), ₹2,00,000 per annum (self-employed)", "confidence": 0.89, "source_text": "Minimum income eligibility: Salaried - Rs. 25,000 per month, Self-employed - Rs. 2,00,000 per annum.", "source_reference": "HDFC MITC Page 5, Section 6.1"},
              "ICICI.pdf": {"value": "₹20,000 per month (salaried), ₹1,50,000 per annum (self-employed)", "confidence": 0.91, "source_text": "Income criteria: Minimum Rs. 20,000 per month for salaried individuals, Rs. 1,50,000 per annum for self-employed.", "source_reference": "ICICI Home Loan Terms Page 6, Clause 7.1"},
              "SBI.pdf": {"value": "₹15,000 per month (salaried), ₹1,00,000 per annum (self-employed)", "confidence": 0.86, "source_text": "Minimum income: Rs. 15,000 per month for salaried, Rs. 1,00,000 per annum for self-employed professionals.", "source_reference": "SBI Terms Page 5, Article 6.2"}
             }
            },
            {"section": "LTV Bands", "field": "Maximum LTV", "comparison_status": "different",
             "documents": {
              "HDFC.pdf": {"value": "90% (up to ₹30 lakhs), 80% (above ₹30 lakhs)", "confidence": 0.93, "source_text": "LTV ratio: Up to 90% for loan amounts up to Rs. 30 lakhs, 80% for amounts above Rs. 30 lakhs.", "source_reference": "HDFC MITC Page 1, Section 1.3"},
              "ICICI.pdf": {"value": "85% (standard), 90% (for women borrowers)", "confidence": 0.88, "source_text": "Loan to Value ratio: Up to 85% of property value, 90% for women borrowers under special schemes.", "source_reference": "ICICI Home Loan Terms Page 1, Clause 2.2"},
              "SBI.pdf": {"value": "80% (standard), 85% (for women/senior citizens)", "confidence": 0.89, "source_text": "Maximum LTV: 80% of property value, enhanced to 85% for women borrowers and senior citizens.", "source_reference": "SBI Terms Page 1, Article 1.4"}
             }
            },
            {"section": "Required Documents", "field": "Income Proof", "comparison_status": "same",
             "documents": {
              "HDFC.pdf": {"value": "Salary slips, Form 16, ITR for last 2 years", "confidence": 0.94, "source_text": "Income documents: Latest 3 months salary slips, Form 16, Income Tax Returns for last 2 years.", "source_reference": "HDFC MITC Page 6, Section 7.1"},
              "ICICI.pdf": {"value": "Salary slips, Form 16, ITR for last 2 years", "confidence": 0.92, "source_text": "Required income proof: 3 months salary slips, Form 16, ITR for previous 2 financial years.", "source_reference": "ICICI Home Loan Terms Page 7, Clause 8.1"},
              "SBI.pdf": {"value": "Salary slips, Form 16, ITR for last 2 years", "confidence": 0.90, "source_text": "Income documents: Latest 3 months salary slips, Form 16, Income Tax Returns for last 2 years.", "source_reference": "SBI Terms Page 6, Article 7.1"}
             }
            }
        ]
    }


if __name__ == "__main__":
    main()