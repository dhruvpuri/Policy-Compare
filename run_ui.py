"""
🏦 Bank Policy Comparator - Streamlit UI
Discover. Compare. Secure. Your Perfect Home Loan
"""

import subprocess
import sys
import os
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    print("🏦 Bank Policy Comparator")
    print("=" * 50)
    print("🎨 Starting Streamlit UI...")
    
    # Check if API is likely running
    print("💡 Make sure the API server is running:")
    print("   python run_api.py")
    print("")
    print("🌐 UI will be available at: http://localhost:8501")
    print("=" * 50)
    
    # Start Streamlit with custom config
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "app/ui/main.py",
        "--server.port=8501",
        "--server.address=localhost",
        "--theme.base=light",
        "--theme.primaryColor=#2C5282",
        "--theme.backgroundColor=#FFFFFF"
    ])

if __name__ == "__main__":
    main()
