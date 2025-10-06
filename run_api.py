"""
🏦 Bank Policy Comparator - API Server
Discover. Compare. Secure. Your Perfect Home Loan
"""

import uvicorn
from dotenv import load_dotenv
import os

def main():
    # Load environment variables
    load_dotenv()
    
    print("🏦 Bank Policy Comparator")
    print("=" * 50)
    print("🔧 Loading environment variables...")
    
    # Check for required API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
        print("   Please add your Google Gemini API key to .env")
        return
    
    print("✅ Environment configured successfully")
    print("🚀 Starting FastAPI server...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 API docs available at: http://localhost:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
