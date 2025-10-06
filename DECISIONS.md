# Technical Decisions and Architecture Documentation

## Project Overview
The Bank Policy Comparator is an AI-powered tool designed to extract, normalize, and compare key facts from home loan MITC (Most Important Terms and Conditions) documents across multiple banks. This document outlines the key technical decisions, architecture choices, and trade-offs made during development.

## Section Selection Rationale

### 1. Document Processing Pipeline
**Decision**: Implemented a multi-stage pipeline with upload → processing → fact extraction → comparison
**Rationale**: 
- Separates concerns for better maintainability
- Allows for asynchronous processing of large documents
- Enables status tracking and error handling at each stage
- Supports batch processing of multiple documents

**Trade-offs**:
- ✅ Better error isolation and recovery
- ✅ Scalable architecture
- ❌ More complex state management
- ❌ Increased latency for simple operations

### 2. Fact Extraction Categories
**Decision**: Organized facts into 8 main categories:
1. **Fees and Charges** - Processing fees, admin charges, legal fees
2. **Interest Rates** - Benchmark rates, spreads, reset frequency
3. **LTV Bands** - Loan-to-value ratios, property value limits
4. **Prepayment and Foreclosure** - Penalties, lock-in periods
5. **Eligibility Criteria** - Income requirements, age limits, CIBIL scores
6. **Tenure Options** - Loan terms, EMI structures
7. **Required Documents** - Income proofs, identity documents
8. **Grievance and Customer Service** - Complaint mechanisms, contact details

**Rationale**:
- Based on RBI guidelines for home loan disclosures
- Covers most critical decision factors for borrowers
- Aligns with industry standard MITC document structures
- Enables meaningful side-by-side comparisons

**Trade-offs**:
- ✅ Comprehensive coverage of important terms
- ✅ Standardized comparison framework
- ❌ May miss bank-specific unique features
- ❌ Requires ongoing maintenance as regulations change

### 3. Comparison Status Classification
**Decision**: Four-tier status system:
- **Same**: Identical values across all documents
- **Different**: Varying values across documents
- **Missing**: Present in some documents but not others
- **Suspect**: Low confidence or contradictory information

**Rationale**:
- Provides clear visual indicators for users
- Helps prioritize which terms need closer review
- Supports confidence-based quality assessment
- Enables automated flagging of potential issues

**Trade-offs**:
- ✅ Clear user guidance on comparison results
- ✅ Quality control through confidence scoring
- ❌ May oversimplify complex variations
- ❌ Requires careful threshold tuning

## Technical Architecture Choices

### 1. Backend Architecture
**Decision**: FastAPI + Pydantic + In-Memory Storage
**Rationale**:
- FastAPI provides excellent API documentation and validation
- Pydantic ensures type safety and data validation
- In-memory storage sufficient for MVP and demo purposes
- Async support for better performance

**Trade-offs**:
- ✅ Rapid development and prototyping
- ✅ Strong type safety and validation
- ✅ Excellent developer experience
- ❌ Data lost on restart (in-memory storage)
- ❌ Limited scalability without persistent storage
- ❌ No concurrent user support

**Future Considerations**:
- Migrate to PostgreSQL or MongoDB for persistence
- Add Redis for caching and session management
- Implement proper user authentication and authorization

### 2. Frontend Architecture
**Decision**: Streamlit for UI
**Rationale**:
- Rapid prototyping and development
- Built-in components for file upload and data display
- Easy integration with Python backend
- Good for data-heavy applications

**Trade-offs**:
- ✅ Very fast development cycle
- ✅ Built-in data visualization components
- ✅ No separate frontend build process
- ❌ Limited customization options
- ❌ Not suitable for production web applications
- ❌ Single-user sessions only

**Future Considerations**:
- Migrate to React/Vue.js for production
- Implement proper responsive design
- Add real-time collaboration features

### 3. Document Processing Strategy
**Decision**: Pattern-based extraction without LLM integration
**Rationale**:
- Deterministic and predictable results
- No external API dependencies or costs
- Faster processing for structured documents
- Better privacy and data security

**Trade-offs**:
- ✅ Consistent and reliable extraction
- ✅ No external dependencies
- ✅ Cost-effective solution
- ❌ Limited adaptability to new document formats
- ❌ Requires manual pattern maintenance
- ❌ May miss context-dependent information

**Future Considerations**:
- Hybrid approach: patterns for structured data, LLM for complex cases
- Fine-tuned models for banking document understanding
- OCR integration for scanned documents

### 4. Export Functionality
**Decision**: CSV and JSON export formats
**Rationale**:
- CSV for spreadsheet analysis and business users
- JSON for programmatic access and API integration
- Both formats widely supported and understood
- Enables offline analysis and reporting

**Trade-offs**:
- ✅ Universal compatibility
- ✅ Supports different user workflows
- ✅ Easy to implement and maintain
- ❌ Limited formatting options in CSV
- ❌ No built-in visualization in exports

## Data Models and Storage

### 1. Document Model Structure
**Decision**: Hierarchical model with metadata, content, and facts
```python
Document
├── metadata (filename, bank_name, file_size)
├── content (extracted_facts, processing_metadata)
└── status (uploaded, processing, completed, error)
```

**Rationale**:
- Clear separation of concerns
- Supports incremental processing
- Enables audit trails and debugging
- Flexible for future extensions

### 2. Fact Representation
**Decision**: Structured fact model with confidence scoring
```python
ExtractedFact
├── key (section.field format)
├── value (normalized string)
├── confidence (0.0 to 1.0)
├── source_text (evidence)
└── source_reference (location)
```

**Rationale**:
- Enables quality assessment through confidence
- Provides traceability to source documents
- Supports evidence-based comparisons
- Standardized key format for consistency

## Quality Assurance and Testing

### 1. Test Strategy
**Decision**: Comprehensive test suite covering:
- Document processing pipeline
- Fact extraction accuracy
- Comparison logic
- Normalization functions
- Export functionality

**Rationale**:
- Ensures reliability of financial data processing
- Supports refactoring and feature additions
- Provides regression testing capabilities
- Documents expected behavior

### 2. Confidence Scoring
**Decision**: Pattern-match confidence based on text clarity and structure
**Rationale**:
- Provides quality indicators for extracted facts
- Enables filtering of low-quality extractions
- Supports manual review prioritization
- Improves user trust in results

## Security and Privacy Considerations

### 1. Data Handling
**Decision**: In-memory processing with no persistent storage of document content
**Rationale**:
- Minimizes data retention risks
- Reduces compliance requirements
- Faster processing without I/O overhead
- Simpler deployment and maintenance

**Trade-offs**:
- ✅ Enhanced privacy and security
- ✅ Reduced compliance burden
- ❌ No audit trail for processed documents
- ❌ Cannot resume interrupted processing

### 2. Input Validation
**Decision**: Strict validation using Pydantic models
**Rationale**:
- Prevents injection attacks
- Ensures data integrity
- Provides clear error messages
- Type safety throughout the application

## Performance Considerations

### 1. Processing Optimization
**Decision**: Synchronous processing with status tracking
**Rationale**:
- Simpler implementation for MVP
- Adequate performance for typical document sizes
- Clear error handling and user feedback
- Easier debugging and maintenance

**Future Improvements**:
- Asynchronous processing for large documents
- Parallel processing of multiple documents
- Caching of processed results
- Background job queues

### 2. Memory Management
**Decision**: In-memory storage with document cleanup
**Rationale**:
- Fast access to processed data
- No database setup required
- Automatic cleanup on restart
- Suitable for demo and testing

## Assumptions and Limitations

### 1. Document Format Assumptions
- Documents are primarily PDF format
- Text is extractable (not scanned images)
- Standard MITC document structure
- English language content

### 2. Scale Assumptions
- Single-user application
- Maximum 4 documents per comparison
- Document sizes under 10MB
- Processing time around 30 seconds per document

### 3. Accuracy Assumptions
- Pattern-based extraction achieves 80%+ accuracy
- Manual review required for critical decisions
- Confidence scores correlate with actual accuracy
- Source text provides sufficient evidence

## Future Roadmap

### Short Term (1-3 months)
1. **Persistent Storage**: Migrate to PostgreSQL
2. **Enhanced UI**: Improve Streamlit interface
3. **Better Patterns**: Refine extraction patterns
4. **Error Handling**: Improve error messages and recovery

### Medium Term (3-6 months)
1. **LLM Integration**: Hybrid extraction approach
2. **Multi-user Support**: User authentication and sessions
3. **API Enhancements**: RESTful API with proper versioning
4. **Advanced Export**: PDF reports and visualizations

### Long Term (6+ months)
1. **Production UI**: React/Vue.js frontend
2. **OCR Support**: Scanned document processing
3. **ML Models**: Custom models for banking documents
4. **Enterprise Features**: Audit logs, compliance reporting

## Conclusion

The current architecture provides a solid foundation for the Bank Policy Comparator while maintaining simplicity and rapid development capabilities. The decisions made prioritize reliability, user experience, and maintainability over advanced features and scalability. This approach is appropriate for the current MVP stage while providing clear paths for future enhancements.

The modular design and comprehensive testing ensure that the system can evolve as requirements change and new features are added. The focus on data quality, user experience, and clear documentation supports both current users and future developers working on the system.