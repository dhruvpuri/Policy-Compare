"""Export service for generating comparison reports in various formats."""

import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any


class ExportService:
    """Service for exporting comparison data."""
    
    @staticmethod
    def generate_csv_export(documents: List[Dict[str, Any]]) -> str:
        """Generate CSV export of comparison data.
        
        Args:
            documents: List of documents to compare
            
        Returns:
            CSV data as string
        """
        output = io.StringIO()
        
        # Extract all facts from all documents
        all_facts = {}
        doc_names = []
        
        for doc in documents:
            doc_name = f"{doc['metadata']['filename']} ({doc['metadata'].get('bank_name', 'Unknown')})"
            doc_names.append(doc_name)
            
            if doc.get('content') and doc['content'].get('extracted_facts'):
                for fact in doc['content']['extracted_facts']:
                    fact_key = ExportService._normalize_fact_key(fact['key'])
                    if fact_key not in all_facts:
                        all_facts[fact_key] = {}
                    all_facts[fact_key][doc_name] = {
                        'value': fact['value'],
                        'confidence': fact['confidence'],
                        'source_text': fact.get('source_text', '')[:100] + "..." if fact.get('source_text', '') else ""
                    }
        
        # Create CSV
        fieldnames = ['Fact'] + doc_names + ['Status', 'Notes']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for fact_key, fact_data in all_facts.items():
            row = {'Fact': fact_key}
            
            # Add values for each document
            values = []
            for doc_name in doc_names:
                if doc_name in fact_data:
                    value_info = fact_data[doc_name]
                    row[doc_name] = f"{value_info['value']} (confidence: {value_info['confidence']:.2f})"
                    values.append(value_info['value'].lower().strip())
                else:
                    row[doc_name] = "Missing"
            
            # Determine status
            unique_values = set(v for v in values if v)
            if not unique_values:
                status = "Missing"
            elif len(unique_values) == 1:
                status = "Same"
            else:
                status = "Different"
            
            row['Status'] = status
            row['Notes'] = f"Found in {len([v for v in values if v])} out of {len(doc_names)} documents"
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def generate_json_export(documents: List[Dict[str, Any]]) -> str:
        """Generate JSON export of comparison data.
        
        Args:
            documents: List of documents to compare
            
        Returns:
            JSON data as string
        """
        export_data = {
            'export_metadata': {
                'export_date': datetime.utcnow().isoformat(),
                'document_count': len(documents),
                'export_type': 'home_loan_mitc_comparison'
            },
            'documents': [],
            'comparison_summary': {},
            'detailed_comparison': {}
        }
        
        # Document metadata
        for doc in documents:
            doc_info = {
                'filename': doc['metadata']['filename'],
                'bank_name': doc['metadata'].get('bank_name', 'Unknown'),
                'file_size': doc['metadata']['file_size'],
                'processing_status': doc['status'],
                'facts_count': len(doc.get('content', {}).get('extracted_facts', [])),
                'upload_date': doc.get('created_at'),
                'processing_metadata': doc.get('content', {}).get('processing_metadata', {})
            }
            export_data['documents'].append(doc_info)
        
        # Organize facts by sections
        sections = ExportService._organize_facts_by_sections(documents)
        
        # Summary statistics
        total_facts = 0
        same_count = 0
        different_count = 0
        missing_count = 0
        
        for section_name, section_data in sections.items():
            for fact_key, fact_data in section_data.items():
                total_facts += 1
                status = ExportService._determine_status(fact_data, len(documents))
                
                if status == 'same':
                    same_count += 1
                elif status == 'different':
                    different_count += 1
                elif status == 'missing':
                    missing_count += 1
        
        export_data['comparison_summary'] = {
            'total_facts_compared': total_facts,
            'same_count': same_count,
            'different_count': different_count,
            'missing_count': missing_count,
            'same_percentage': (same_count / max(total_facts, 1)) * 100,
            'different_percentage': (different_count / max(total_facts, 1)) * 100,
            'missing_percentage': (missing_count / max(total_facts, 1)) * 100
        }
        
        # Detailed comparison by sections
        export_data['detailed_comparison'] = sections
        
        return json.dumps(export_data, indent=2, default=str)
    
    @staticmethod
    def _organize_facts_by_sections(documents: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Organize facts by sections for structured export."""
        sections = {}
        
        for doc in documents:
            doc_name = f"{doc['metadata']['filename']} ({doc['metadata'].get('bank_name', 'Unknown')})"
            
            if doc.get('content') and doc['content'].get('extracted_facts'):
                for fact in doc['content']['extracted_facts']:
                    section = ExportService._map_fact_to_section(fact['key'])
                    fact_key = ExportService._normalize_fact_key(fact['key'])
                    
                    if section not in sections:
                        sections[section] = {}
                    if fact_key not in sections[section]:
                        sections[section][fact_key] = {}
                    
                    sections[section][fact_key][doc_name] = {
                        'value': fact['value'],
                        'confidence': fact['confidence'],
                        'source_text': fact.get('source_text', ''),
                        'original_key': fact['key']
                    }
        
        return sections
    
    @staticmethod
    def _map_fact_to_section(fact_key: str) -> str:
        """Map a fact key to its corresponding section."""
        key_lower = fact_key.lower()
        
        if any(term in key_lower for term in ['ltv', 'loan_to_value', 'property_value']):
            return "LTV_Bands"
        elif any(term in key_lower for term in ['processing', 'admin', 'legal', 'valuation']):
            return "Processing_Fees_and_Charges"
        elif any(term in key_lower for term in ['prepayment', 'foreclosure', 'pre_closure']):
            return "Prepayment_and_Foreclosure"
        elif any(term in key_lower for term in ['income', 'employment', 'age', 'cibil']):
            return "Eligibility_Criteria"
        elif any(term in key_lower for term in ['tenure', 'term', 'emi', 'repayment']):
            return "Tenure_Options"
        elif any(term in key_lower for term in ['reset', 'benchmark', 'spread']):
            return "Interest_Reset_and_Communication"
        elif any(term in key_lower for term in ['documents', 'proof', 'certificate']):
            return "Required_Documents"
        elif any(term in key_lower for term in ['grievance', 'complaint', 'ombudsman']):
            return "Grievance_and_Customer_Service"
        
        return "Other"
    
    @staticmethod
    def _normalize_fact_key(fact_key: str) -> str:
        """Normalize fact key for display."""
        if '.' in fact_key:
            field_name = fact_key.split('.')[-1]
        else:
            field_name = fact_key
        
        return field_name.replace('_', ' ').title()
    
    @staticmethod
    def _determine_status(fact_data: Dict[str, Any], total_docs: int) -> str:
        """Determine the status of a fact across documents."""
        values = []
        
        for doc_data in fact_data.values():
            if doc_data['value']:
                values.append(doc_data['value'].lower().strip())
        
        if not values:
            return "missing"
        elif len(values) < total_docs:
            return "missing"
        
        unique_values = set(values)
        if len(unique_values) == 1:
            return "same"
        else:
            return "different"


















