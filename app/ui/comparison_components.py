"""Specialized comparison components for home loan MITC documents."""

import streamlit as st
import pandas as pd
import requests
from typing import Dict, Any, List, Optional, Tuple


class CompactComparisonTable:
    """Compact comparison table with clickable cells for evidence drill-down."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        self.api_base_url = api_base_url
    
    def show_comparison(self, comparison_data: Dict[str, Any]) -> None:
        """Show compact comparison table with Same/Different/Missing/Suspect status."""
        
        if not comparison_data.get('comparison_table'):
            st.warning("No comparison data available")
            return
        
        # Show summary metrics
        self._show_api_summary_metrics(comparison_data)
        
        # Organize facts by sections
        sections = self._organize_api_facts_by_section(comparison_data['comparison_table'])
        
        # Show comparison table by sections
        for section_name, facts in sections.items():
            if facts:
                self._show_api_section_table(section_name, facts, comparison_data)
    
    def _organize_facts_by_section(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Organize facts by sections across documents."""
        sections = {
            "LTV Bands": {"facts": {}, "priority": 1},
            "Processing Fees and Charges": {"facts": {}, "priority": 2},
            "Prepayment and Foreclosure": {"facts": {}, "priority": 3},
            "Eligibility Criteria": {"facts": {}, "priority": 4},
            "Tenure Options": {"facts": {}, "priority": 5},
            "Interest Reset and Communication": {"facts": {}, "priority": 6},
            "Required Documents": {"facts": {}, "priority": 7},
            "Grievance and Customer Service": {"facts": {}, "priority": 8}
        }
        
        # Collect all facts from all documents
        for doc in documents:
            doc_name = f"{doc['metadata']['filename']} ({doc['metadata'].get('bank_name', 'Unknown')})"
            
            if doc.get('content') and doc['content'].get('extracted_facts'):
                for fact in doc['content']['extracted_facts']:
                    # Map fact to section
                    section = self._map_fact_to_section(fact['key'])
                    if section and section in sections:
                        fact_key = self._normalize_fact_key(fact['key'])
                        
                        if fact_key not in sections[section]['facts']:
                            sections[section]['facts'][fact_key] = {}
                        
                        sections[section]['facts'][fact_key][doc_name] = {
                            'value': fact['value'],
                            'confidence': fact['confidence'],
                            'source_text': fact.get('source_text', ''),
                            'original_key': fact['key']
                        }
        
        # Remove empty sections and sort by priority
        return {k: v for k, v in sorted(sections.items(), key=lambda x: x[1]['priority']) 
                if v['facts']}
    
    def _map_fact_to_section(self, fact_key: str) -> Optional[str]:
        """Map a fact key to its corresponding section."""
        key_lower = fact_key.lower()
        
        if any(term in key_lower for term in ['ltv', 'loan_to_value', 'property_value', 'financing']):
            return "LTV Bands"
        elif any(term in key_lower for term in ['processing', 'admin', 'legal', 'valuation', 'insurance']):
            return "Processing Fees and Charges"
        elif any(term in key_lower for term in ['prepayment', 'foreclosure', 'pre_closure', 'lock_in']):
            return "Prepayment and Foreclosure"
        elif any(term in key_lower for term in ['income', 'employment', 'age', 'cibil', 'eligibility']):
            return "Eligibility Criteria"
        elif any(term in key_lower for term in ['tenure', 'term', 'emi', 'repayment']):
            return "Tenure Options"
        elif any(term in key_lower for term in ['reset', 'benchmark', 'spread', 'communication']):
            return "Interest Reset and Communication"
        elif any(term in key_lower for term in ['documents', 'proof', 'certificate']):
            return "Required Documents"
        elif any(term in key_lower for term in ['grievance', 'complaint', 'escalation', 'ombudsman']):
            return "Grievance and Customer Service"
        
        return None
    
    def _normalize_fact_key(self, fact_key: str) -> str:
        """Normalize fact key for display."""
        # Extract the field name after the section prefix
        if '.' in fact_key:
            field_name = fact_key.split('.')[-1]
        else:
            field_name = fact_key
        
        # Convert to readable format
        return field_name.replace('_', ' ').title()
    
    def _show_summary_metrics(self, comparison_data: Dict[str, Any]) -> None:
        """Show summary metrics across all sections."""
        total_facts = 0
        same_count = 0
        different_count = 0
        missing_count = 0
        suspect_count = 0
        
        for section_data in comparison_data.values():
            for fact_data in section_data['facts'].values():
                total_facts += 1
                status = self._determine_fact_status(fact_data)
                
                if status == "Same":
                    same_count += 1
                elif status == "Different":
                    different_count += 1
                elif status == "Missing":
                    missing_count += 1
                elif status == "Suspect":
                    suspect_count += 1
        
        st.subheader("📊 Comparison Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("✅ Same", same_count, delta=f"{same_count/max(total_facts,1)*100:.0f}%")
        with col2:
            st.metric("🔴 Different", different_count, delta=f"{different_count/max(total_facts,1)*100:.0f}%")
        with col3:
            st.metric("⚪ Missing", missing_count, delta=f"{missing_count/max(total_facts,1)*100:.0f}%")
        with col4:
            st.metric("🟡 Suspect", suspect_count, delta=f"{suspect_count/max(total_facts,1)*100:.0f}%")
    
    def _show_section_table(self, section_name: str, section_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> None:
        """Show comparison table for a specific section."""
        st.subheader(f"🔍 {section_name}")
        
        # Prepare table data
        table_data = []
        doc_names = [f"{doc['metadata']['filename']}" for doc in documents]
        
        for fact_key, fact_data in section_data['facts'].items():
            row = {"Field": fact_key}
            
            # Add columns for each document
            for doc_name in doc_names:
                full_doc_name = f"{doc_name} ({[doc for doc in documents if doc['metadata']['filename'] == doc_name][0]['metadata'].get('bank_name', 'Unknown')})"
                
                if full_doc_name in fact_data:
                    value_info = fact_data[full_doc_name]
                    confidence = value_info['confidence']
                    confidence_icon = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                    row[doc_name] = f"{value_info['value']} {confidence_icon}"
                else:
                    row[doc_name] = "❌ Missing"
            
            # Determine status
            status = self._determine_fact_status(fact_data)
            status_icons = {
                "Same": "✅",
                "Different": "🔴", 
                "Missing": "⚪",
                "Suspect": "🟡"
            }
            row["Status"] = f"{status_icons.get(status, '❓')} {status}"
            
            # Add clickable evidence
            row["Evidence"] = "🔍 Click for details"
            table_data.append(row)
        
        # Show table
        if table_data:
            df = pd.DataFrame(table_data)
            
            # Display with custom styling
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Evidence drill-down functionality
            selected_field = st.selectbox(
                f"Select field to view evidence ({section_name}):",
                options=[row["Field"] for row in table_data],
                key=f"evidence_{section_name}"
            )
            
            if selected_field:
                self._show_evidence_drill_down(selected_field, section_data['facts'][selected_field], documents)
    
    def _determine_fact_status(self, fact_data: Dict[str, Any]) -> str:
        """Determine the status of a fact across documents."""
        values = []
        confidences = []
        
        for doc_data in fact_data.values():
            if doc_data['value']:
                values.append(doc_data['value'].lower().strip())
                confidences.append(doc_data['confidence'])
        
        if not values:
            return "Missing"
        
        # Check for suspect (low confidence)
        if any(conf < 0.6 for conf in confidences):
            return "Suspect"
        
        # Check for same/different
        unique_values = set(values)
        if len(unique_values) == 1:
            return "Same"
        elif len(unique_values) > 1:
            # Check if values are similar (for numerical comparison)
            if self._are_values_similar(values):
                return "Suspect"
            else:
                return "Different"
        
        return "Missing"
    
    def _are_values_similar(self, values: List[str]) -> bool:
        """Check if values are similar enough to be considered suspect rather than different."""
        try:
            # Try to extract numbers and compare
            import re
            numbers = []
            for value in values:
                matches = re.findall(r'[\d.]+', value)
                if matches:
                    numbers.append(float(matches[0]))
            
            if len(numbers) >= 2:
                # If numbers are within 5% of each other, consider suspect
                max_num = max(numbers)
                min_num = min(numbers)
                if max_num > 0 and (max_num - min_num) / max_num < 0.05:
                    return True
        except:
            pass
        
        return False
    
    def _show_evidence_drill_down(self, field_name: str, fact_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> None:
        """Show evidence drill-down for a specific field."""
        st.subheader(f"🔍 Evidence for: {field_name}")
        
        for doc_name, value_info in fact_data.items():
            with st.expander(f"📄 {doc_name}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Extracted Value:** {value_info['value']}")
                    st.write(f"**Source Text:**")
                    st.text_area(
                        "Evidence",
                        value_info.get('source_text', 'No source text available'),
                        height=100,
                        key=f"evidence_{field_name}_{doc_name}"
                    )
                
                with col2:
                    confidence = value_info['confidence']
                    confidence_color = "green" if confidence > 0.8 else "orange" if confidence > 0.5 else "red"
                    st.markdown(f"**Confidence:**")
                    st.markdown(f":{confidence_color}[{confidence:.2f}]")
                    
                    st.markdown(f"**Original Key:**")
                    st.code(value_info.get('original_key', 'N/A'))
    
    def _show_api_summary_metrics(self, comparison_data: Dict[str, Any]) -> None:
        """Show summary metrics from API comparison data."""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Documents", comparison_data.get('document_count', 0))
        with col2:
            st.metric("Total Facts", comparison_data.get('total_facts', 0))
        with col3:
            same_count = comparison_data.get('same_facts', 0)
            st.metric("Same", same_count, delta=None, delta_color="off")
        with col4:
            diff_count = comparison_data.get('different_facts', 0)
            st.metric("Different", diff_count, delta=None, delta_color="off") 
        with col5:
            missing_count = comparison_data.get('missing_facts', 0)
            st.metric("Missing", missing_count, delta=None, delta_color="off")
        
        # Show document names
        st.write("**Documents being compared:**")
        for i, doc_name in enumerate(comparison_data.get('document_names', [])):
            st.write(f"{i+1}. {doc_name}")
    
    def _organize_api_facts_by_section(self, comparison_table: List[Dict[str, Any]]) -> Dict[str, List]:
        """Organize API comparison table by sections."""
        sections = {}
        
        for fact in comparison_table:
            section = fact.get('section', 'Unknown')
            if section not in sections:
                sections[section] = []
            sections[section].append(fact)
        
        return sections
    
    def _show_api_section_table(self, section_name: str, facts: List[Dict], comparison_data: Dict) -> None:
        """Show comparison table for a section using API data."""
        st.subheader(f"📋 {section_name}")
        
        if not facts:
            st.info("No facts found for this section")
            return
        
        # Create columns for table header
        doc_names = comparison_data.get('document_names', [])
        cols = st.columns([2] + [1] * len(doc_names))
        
        # Header row
        cols[0].write("**Field**")
        for i, doc_name in enumerate(doc_names):
            cols[i+1].write(f"**{doc_name[:15]}...**" if len(doc_name) > 15 else f"**{doc_name}**")
        
        st.divider()
        
        # Data rows
        for fact in facts:
            cols = st.columns([2] + [1] * len(doc_names))
            
            # Field name
            field = fact.get('field', 'Unknown')
            status = fact.get('comparison_status', 'unknown')
            status_color = self._get_status_color(status)
            
            cols[0].markdown(f"**{field}** <span style='color: {status_color}'>●</span>", unsafe_allow_html=True)
            
            # Values for each document
            for i, doc_name in enumerate(doc_names):
                doc_data = fact.get('documents', {}).get(doc_name, {})
                value = doc_data.get('value', 'Not found')
                confidence = doc_data.get('confidence', 0)
                
                # Show value with confidence indicator
                if value != "Not found":
                    conf_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                    display_value = f"{value[:20]}..." if len(str(value)) > 20 else str(value)
                    cols[i+1].write(f"{conf_color} {display_value}")
                    
                    # Clickable for source text
                    if st.button(f"Source", key=f"{section_name}_{field}_{doc_name}_{i}", help="Show source text"):
                        source_text = doc_data.get('source_text', 'No source available')
                        st.text_area(f"Source for {field} in {doc_name}", source_text, height=100)
                else:
                    cols[i+1].write("❌ Not found")
        
        st.divider()
    
    def _get_status_color(self, status: str) -> str:
        """Get color code for status badge."""
        colors = {
            'same': '#28a745',      # Green
            'different': '#dc3545',  # Red
            'missing': '#6c757d',    # Gray
            'suspect': '#fd7e14',    # Orange
        }
        return colors.get(status, '#6c757d')
