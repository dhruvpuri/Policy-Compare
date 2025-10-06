# 🏦 Ai Bank Policy Comparator

**Discover. Compare. Secure. Your Perfect Home Loan**

Born from my parents' struggle with home loan documents - an AI-powered platform built with React, TypeScript, and Python that uses NLP and document parsing to simplify complex policy comparisons for everyday people.

## 🎯 Overview

The AI Bank Policy Comparator empowers customers and analysts to:

- **📤 Upload Documents**: Ingest 2-4 bank home loan MITC documents (PDF/TXT/DOCX)
- **🤖 AI Analysis**: Extract key terms using Google Gemini LLM with confidence scoring
- **⚖️ Smart Comparison**: Side-by-side analysis with human-readable explanations
- **🔍 Evidence Tracing**: Click any cell to see normalized value, explanation, and source evidence
- **📊 Export Results**: Generate CSV/JSON reports for decision making
- **🎨 Butter Money Branding**: Beautiful blue gradient theme matching Butter Money's website

## 🎯 User Workflow

### For Customers:
1. **Upload** 2-4 home loan MITC documents from different banks
2. **Wait** for AI processing (30-60 seconds per document)
3. **Compare** policies side-by-side with clear explanations
4. **Click** any cell to understand differences and see evidence
5. **Export** comparison report for decision making

### For Analysts:
1. **Batch process** multiple customer document sets
2. **Review** confidence scores and flag low-confidence extractions
3. **Validate** AI extractions against source documents
4. **Generate** reports for customer consultations

## 📁 Project Structure

```
bank-comparator/
├── app/
│   ├── models/              # Pydantic data models
│   ├── services/            # Business logic
│   │   ├── document_service.py    # Document processing
│   │   ├── extraction_service.py  # AI fact extraction
│   │   ├── comparison_service.py  # Policy comparison
│   │   └── export_service.py      # Report generation
│   ├── api/                 # FastAPI endpoints
│   │   ├── documents.py           # Document upload/management
│   │   ├── comparison.py          # Comparison endpoints
│   │   └── main.py               # API application
│   └── ui/                  # Streamlit interface
│       ├── main.py               # Main UI application
│       ├── beautiful_comparison.py # Comparison display
│       └── components.py         # Reusable UI components
├── tests/                   # Test suite
├── data/                    # Sample documents and uploads
├── logs/                    # Application logs
├── requirements.txt         # Python dependencies
├── run_api.py              # API server launcher
├── run_ui.py               # UI server launcher
└── README.md               # This documentation
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Set up environment variables
cp .env.example .env
# Add your Google Gemini API key to .env
```

### 3. Run the Application
```bash
# Terminal 1: Start FastAPI backend
python run_api.py
# Or: uvicorn app.api.main:app --reload --port 8000

# Terminal 2: Start Streamlit UI  
python run_ui.py
# Or: streamlit run app/ui/main.py
```

### 4. Access the App
- **Streamlit UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## ✅ Current Status

### ✅ **Completed Features**
- [x] **Document Processing**: PDF/TXT/DOCX upload and text extraction
- [x] **AI Integration**: Google Gemini LLM for fact extraction with confidence scoring
- [x] **Smart Extraction**: Rule-based + LLM hybrid approach for accuracy
- [x] **Comparison Engine**: Side-by-side analysis with status indicators
- [x] **Beautiful UI**: Butter Money branded interface with blue gradient theme
- [x] **Evidence Tracing**: Click cells to see normalized values and source evidence
- [x] **Export Functionality**: CSV/JSON report generation
- [x] **API Architecture**: FastAPI backend with comprehensive endpoints

### 🔄 **In Progress**
- [ ] Performance optimization for large documents
- [ ] Enhanced error handling and validation
- [ ] Comprehensive test coverage
- [ ] Docker containerization

### 🎯 **Planned Enhancements**
- [ ] Batch processing for multiple document sets
- [ ] Advanced analytics and insights
- [ ] Integration with Butter Money's existing systems
- [ ] Mobile-responsive design improvements

## 🌟 Key Features

### � **Bank-Specific Intelligence**
- **Auto-detects** major Indian banks (HDFC, ICICI, SBI, Axis, Kotak)
- **Clean bank names** in comparison headers (no more confusing filenames)
- **Contextual explanations** for each policy term
- **Indian financial notation** support (₹, Rs, Lakhs, Crores)

### 🤖 **Advanced AI Processing**
- **Hybrid extraction**: Rule-based + Google Gemini LLM
- **Confidence scoring** with color-coded indicators
- **Smart gap filling** for missing information
- **Conflict detection** for contradictory data

### 📊 **Beautiful Comparison Interface**
- **Expandable cells** showing full values (no truncation)
- **Human-readable explanations** for each difference
- **Evidence tracing** with clean source text display
- **Status indicators**: Same/Different/Missing with clear badges

### 🔍 **Evidence & Transparency**
When you click any cell, see:
1. **Normalized value** with clear formatting
2. **Brief explanation** in plain English
3. **Confidence score** with reliability indicator
4. **Exact evidence** from source document
5. **Document reference** for verification

### 🎨 **User Experience**
- **No truncated text** - see complete information
- **Clear bank identification** - HDFC Bank vs ICICI Bank
- **Intuitive navigation** - click to explore
- **Responsive layout** for different screen sizes

### 📈 **Export & Analysis**
- **CSV reports** for spreadsheet analysis
- **JSON exports** for system integration
- **Comparison summaries** with key metrics
- **Evidence documentation** for audit trails

## 🛠 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Google Gemini** - LLM for document analysis
- **PyMuPDF & PDFPlumber** - PDF text extraction
- **Pandas** - Data processing and analysis
- **Pydantic** - Data validation and serialization

### Frontend
- **Streamlit** - Interactive web interface
- **Plotly** - Data visualization
- **Custom CSS** - Butter Money branding

### Development
- **pytest** - Testing framework
- **uvicorn** - ASGI server
- **python-dotenv** - Environment management

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=./data/uploads
```

### API Configuration
- **Port**: 8000 (configurable)
- **Max file size**: 10MB per document
- **Supported formats**: PDF, TXT, DOCX
- **Concurrent uploads**: Up to 4 documents

## 🐛 Troubleshooting

### Common Issues

**1. "No module named 'app'" Error**
```bash
# Make sure you're in the bank-comparator directory
cd bank-comparator
python run_api.py
```

**2. "Google API Key not found" Error**
```bash
# Check your .env file has the correct API key
echo $GOOGLE_API_KEY  # Should show your key
```

**3. "Port already in use" Error**
```bash
# Kill existing processes
pkill -f "uvicorn"
pkill -f "streamlit"
# Or use different ports
uvicorn app.api.main:app --port 8001
streamlit run app/ui/main.py --server.port 8502
```

**4. PDF Processing Issues**
- Ensure PDFs are text-based (not scanned images)
- Check file size is under 10MB
- Try converting to TXT if extraction fails

**5. Slow Processing**
- Large documents take longer to process
- Check internet connection for Gemini API calls
- Monitor logs for processing status

### Performance Tips
- **Smaller files** process faster
- **Text files** are processed quicker than PDFs
- **Clear document structure** improves extraction accuracy
- **Good internet connection** reduces API latency

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API logs in `logs/` directory
3. Test with sample documents in `data/` folder
4. Verify all dependencies are installed correctly

## 🚀 Deployment

### Local Development
```bash
# Development mode with auto-reload
python run_api.py --reload
python run_ui.py --debug
```

### Production Deployment
```bash
# Production mode
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
streamlit run app/ui/main.py --server.port 8501 --server.address 0.0.0.0
```

---


*Helping customers discover, compare, and secure their perfect home loan*