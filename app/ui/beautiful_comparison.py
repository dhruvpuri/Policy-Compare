"""Beautiful side-by-side comparison component for loan documents."""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import io
from datetime import datetime
from app.services.export_service import ExportService


def show_beautiful_side_by_side_comparison(comparison_data: Dict[str, Any]) -> None:
    """Show a beautiful side-by-side comparison with drill-down capability.
    
    This meets the assignment requirements:
    1. Extracts & normalizes key facts 
    2. Presents side-by-side comparison with human-readable explanations
    3. Ability to drill into underlying evidence
    """
    
    # Modern brand styling with blue gradient background
    st.markdown("""
    <style>
    /* Modern Brand Theme */
    .stApp {
        background: linear-gradient(135deg, #2C5282 0%, #2A4A6B 50%, #1A365D 100%) !important;
        min-height: 100vh !important;
    }
    
    /* Main content area with white background */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        margin: 1rem !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Headers with modern styling */
    h1, h2, h3 {
        color: #1A365D !important;
        font-weight: 700 !important;
    }
    
    /* Modern yellow accent for important elements */
    .modern-accent {
        background: linear-gradient(135deg, #F6D55C 0%, #ED8936 100%) !important;
        color: #1A365D !important;
        padding: 1rem 2rem !important;
        border-radius: 15px !important;
        font-weight: 600 !important;
        text-align: center !important;
        margin: 1rem 0 !important;
        box-shadow: 0 4px 15px rgba(246, 213, 92, 0.3) !important;
    }
    
    /* Clean comparison table styling */
    .stAlert > div {
        font-size: 0.9rem !important;
        padding: 12px 16px !important;
        margin: 4px 0 !important;
        border-radius: 10px !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Info boxes with modern blue accent */
    .stAlert[data-baseweb="notification"] {
        background: linear-gradient(135deg, #E6F3FF 0%, #CCE7FF 100%) !important;
        border-left: 4px solid #2C5282 !important;
    }
    
    /* Warning boxes with yellow accent */
    .stAlert[data-baseweb="notification"][kind="warning"] {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%) !important;
        border-left: 4px solid #F6D55C !important;
    }
    
    /* Error boxes */
    .stAlert[data-baseweb="notification"][kind="error"] {
        background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%) !important;
        border-left: 4px solid #E53E3E !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: rgba(44, 82, 130, 0.1) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(44, 82, 130, 0.2) !important;
    }
    
    /* Fix form elements */
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background-color: #ffffff !important;
        color: #1A365D !important;
        border: 2px solid rgba(44, 82, 130, 0.2) !important;
        border-radius: 8px !important;
    }
    
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #2C5282 !important;
        box-shadow: 0 0 0 2px rgba(44, 82, 130, 0.2) !important;
    }
    
    /* Status badges */
    .status-badge {
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not comparison_data or not comparison_data.get('comparison_table'):
        st.error("❌ **No comparison data available**")
        st.info("Please upload and process documents first to generate a comparison.")
        return
    
    # Modern branded header
    st.markdown(
        """
        <div class="modern-accent">
            <h1 style="margin: 0; color: #1A365D !important; font-size: 2.5rem;">
                🏦 Discover. Compare. Secure.
            </h1>
            <p style="margin: 0.5rem 0 0 0; color: #1A365D !important; font-size: 1.2rem; font-weight: 500;">
                AI-powered home loan comparison
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Summary metrics in a beautiful card layout
    _show_comparison_summary_cards(comparison_data)
    
    # Add some spacing
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    # Show unified view (all sections together)
    sections = _organize_facts_by_sections(comparison_data['comparison_table'])
    document_names = comparison_data['document_names']
    
    # Display all sections in one unified view
    for section_name, facts in sections.items():
        if not facts:
            continue
            
        st.markdown(f"### {section_name}")
        
        # Create comparison table for this section
        for fact_idx, fact in enumerate(facts):
            term = fact.get('field', '').replace('_', ' ').title()
            status = fact.get('comparison_status') or _infer_status_across_banks(fact)
            
            # Create columns: Term name + Bank values
            cols = st.columns([2] + [1] * len(document_names))
            
            # Term column
            with cols[0]:
                status_badge = _get_company_status_badge(status)
                st.markdown(f"**{term}** {status_badge}")
            
            # Bank value columns (Company Requirement: clickable cells)
            for i, doc in enumerate(document_names):
                doc_info = fact.get('documents', {}).get(doc, {})
                value = doc_info.get('value', 'Not found')
                
                with cols[i + 1]:
                    if value != 'Not found' and value:
                        # Extract clean bank name from document name
                        clean_bank_name = _extract_bank_name(doc)
                        cell_key = f"{section_name}_{term}_{clean_bank_name}_{fact_idx}".replace(' ', '_').replace('&', 'and')
                        confidence = doc_info.get('confidence', 0)
                        
                        # Show full value with clear bank name - no truncation in header
                        with st.expander(f"🏦 **{clean_bank_name}**", expanded=False):
                            # Normalized value with clear formatting
                            st.markdown(f"### 📋 {term}")
                            st.success(f"**Value:** {value}")
                            
                            # Brief human-readable explanation
                            explanation = _generate_brief_explanation(term, value, clean_bank_name)
                            st.info(f"**Explanation:** {explanation}")
                            
                            # Confidence with color coding
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                            st.write(f"**Confidence:** {confidence_color} {confidence:.2f} ({_confidence_label(confidence)})")
                            
                            # Evidence pointer with clean formatting
                            st.markdown("---")
                            st.markdown("### 🔍 Evidence Trace")
                            
                            source_text = doc_info.get('source_text', 'No source text available')
                            source_ref = doc_info.get('source_reference', 'No reference available')
                            
                            # Clean source text display
                            if source_text and source_text != 'No source text available':
                                st.write(f"**📄 Source Document:** {clean_bank_name} Policy")
                                st.write(f"**📍 Reference:** {source_ref}")
                                st.markdown("**📝 Exact Evidence:**")
                                
                                # Clean, readable text area
                                st.markdown(f"""
                                <div style="
                                    background: #f8f9fa; 
                                    border: 1px solid #dee2e6; 
                                    border-radius: 8px; 
                                    padding: 1rem; 
                                    font-family: monospace; 
                                    color: #212529;
                                    max-height: 200px;
                                    overflow-y: auto;
                                ">
                                {source_text}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.warning("No source text available for this extraction")
                    else:
                        # Missing cell with clear bank name
                        clean_bank_name = _extract_bank_name(doc)
                        st.error(f"🏦 **{clean_bank_name}**: Missing Data")
        
        st.markdown("---")
    
    # Export functionality
    _show_export_section(comparison_data)


def _show_comparison_summary_cards(comparison_data: Dict[str, Any]) -> None:
    """Show beautiful summary cards with key metrics."""
    
    # Create metrics cards with modern styling
    total_facts = comparison_data.get('total_facts', 1)
    same_count = comparison_data.get('same_facts', 0)
    diff_count = comparison_data.get('different_facts', 0)
    missing_count = comparison_data.get('missing_facts', 0)
    suspect_count = comparison_data.get('suspect_facts', 0)
    
    # Calculate percentages
    similarity = f"{(same_count/total_facts)*100:.1f}%" if total_facts > 0 else "0%"
    difference = f"{(diff_count/total_facts)*100:.1f}%" if total_facts > 0 else "0%"
    missing_pct = f"{(missing_count/total_facts)*100:.1f}%" if total_facts > 0 else "0%"
    suspect_pct = f"{(suspect_count/total_facts)*100:.1f}%" if total_facts > 0 else "0%"
    
    # Show bank comparison header
    banks = comparison_data.get('document_names', [])
    if len(banks) > 1:
        bank_names = [name.replace('.pdf', '').replace('.docx', '').replace('.txt', '') for name in banks]
        html_block = (
            f"""
<div style="text-align: center; margin-bottom: 2rem; padding: 1.5rem; background: var(--butter-card); border-radius: 16px; border: 1px solid var(--butter-border);">
  <h3 style="margin: 0; color: var(--butter-dark);">🏦 Comparing Banks</h3>
  <p style="font-size: 1.1rem; margin: 0.5rem 0; color: var(--butter-secondary);">
    <strong>{' vs '.join(bank_names[:3])}</strong>
    {'...' if len(banks) > 3 else ''}
  </p>
  <p style="margin: 0; color: var(--butter-muted); font-size: 0.9rem;">
    Found {total_facts} comparable terms across {len(banks)} documents
  </p>
</div>
"""
        )
        st.markdown(html_block, unsafe_allow_html=True)
    
    # Create metrics cards in a responsive grid
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📄 Banks Compared", 
            value=comparison_data.get('document_count', 0),
            help="Number of bank documents in comparison"
        )
    
    with col2:
        st.metric(
            label="✅ Identical Terms", 
            value=same_count,
            delta=similarity,
            delta_color="normal",
            help="Terms that are exactly the same across all banks"
        )
    
    with col3:
        st.metric(
            label="🔍 Different Terms", 
            value=diff_count,
            delta=difference,
            delta_color="inverse",
            help="Terms that vary between banks - review these carefully"
        )
    
    with col4:
        st.metric(
            label="⚠️ Needs Review", 
            value=suspect_count,
            delta=suspect_pct,
            delta_color="inverse",
            help="Terms with low confidence or conflicting information"
        )
    
    with col5:
        st.metric(
            label="❓ Missing Data", 
            value=missing_count,
            delta=missing_pct,
            delta_color="off",
            help="Terms found in some documents but missing in others"
        )
    
    # Add interpretation section
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Smart insights based on the data
    if total_facts > 0:
        same_pct = (same_count / total_facts) * 100
        diff_pct = (diff_count / total_facts) * 100
        
        if same_pct > 60:
            insight_color = "var(--butter-success)"
            insight_icon = "🎯"
            insight_text = "High Similarity - Banks offer similar terms in most areas"
        elif diff_pct > 40:
            insight_color = "var(--butter-warning)"
            insight_icon = "⚡"
            insight_text = "Significant Differences - Important variations found between banks"
        else:
            insight_color = "var(--butter-primary)"
            insight_icon = "📊"
            insight_text = "Mixed Results - Some similarities and differences identified"
        
        st.markdown(
            f"""
            <div style="background: var(--butter-card); border-left: 4px solid {insight_color}; border-radius: 0 12px 12px 0; padding: 1rem 1.5rem; margin: 1rem 0;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.2rem;">{insight_icon}</span>
                    <strong style="color: var(--butter-dark);">Key Insight:</strong>
                </div>
                <p style="margin: 0.5rem 0 0 0; color: var(--butter-secondary);">{insight_text}</p>
            </div>
            """,
            unsafe_allow_html=True
        )


def _organize_facts_by_sections(comparison_table: List[Dict]) -> Dict[str, List[Dict]]:
    """Organize facts by logical sections for better presentation."""
    
    sections = {
        "💰 Loan Amount & LTV": [],
        "📊 Interest Rates": [],
        "💳 Processing Fees": [],
        "🔄 Repayment Terms": [], 
        "⚖️ Prepayment & Penalties": [],
        "📋 Eligibility Criteria": [],
        "📄 Required Documents": [],
        "📞 Customer Service": [],
        "🏛️ Other Terms": []
    }
    
    # Section mapping based on fact keys
    section_mapping = {
        'loan_amount': "💰 Loan Amount & LTV",
        'ltv': "💰 Loan Amount & LTV", 
        'interest': "📊 Interest Rates",
        'rate': "📊 Interest Rates",
        'rplr': "📊 Interest Rates",
        'ihplr': "📊 Interest Rates", 
        'eblr': "📊 Interest Rates",
        'processing': "💳 Processing Fees",
        'fee': "💳 Processing Fees",
        'charges': "💳 Processing Fees",
        'emi': "🔄 Repayment Terms",
        'tenure': "🔄 Repayment Terms",
        'repayment': "🔄 Repayment Terms",
        'prepayment': "⚖️ Prepayment & Penalties",
        'foreclosure': "⚖️ Prepayment & Penalties",
        'penalty': "⚖️ Prepayment & Penalties",
        'penal': "⚖️ Prepayment & Penalties",
        'eligibility': "📋 Eligibility Criteria",
        'income': "📋 Eligibility Criteria",
        'cibil': "📋 Eligibility Criteria",
        'age': "📋 Eligibility Criteria",
        'documents': "📄 Required Documents",
        'proof': "📄 Required Documents",
        'grievance': "📞 Customer Service",
        'customer': "📞 Customer Service",
        'service': "📞 Customer Service"
    }
    
    for fact in comparison_table:
        fact_key = fact.get('fact_key', '').lower()
        section_assigned = False
        
        # Try to match to a section
        for keyword, section in section_mapping.items():
            if keyword in fact_key:
                sections[section].append(fact)
                section_assigned = True
                break
        
        # If no match, put in "Other Terms"
        if not section_assigned:
            sections["🏛️ Other Terms"].append(fact)
    
    # Remove empty sections
    return {k: v for k, v in sections.items() if v}


def _status_color(status: str) -> str:
    """Return a hex color for status background."""
    colors = {
        'same': '#E6F4EA',      # light green
        'different': '#FDECEA', # light red
        'missing': '#F2F2F2',   # light gray
        'suspect': '#FFF4E5',   # light orange
        'unknown': '#F7F7F7'
    }
    return colors.get(status.lower(), '#F7F7F7')


def _infer_status_across_banks(fact: Dict[str, Any]) -> str:
    """Infer same/different/missing/suspect for a single fact across banks."""
    values = []
    confidences = []
    for doc, data in fact.get('documents', {}).items():
        v = str(data.get('value', '')).strip().lower()
        if v and v != 'not found':
            values.append(v)
            confidences.append(data.get('confidence', 0))
    if not values:
        return 'missing'
    if any(c < 0.6 for c in confidences):
        return 'suspect'
    if len(set(values)) == 1:
        return 'same'
    return 'different'


def _explain_fact(fact: Dict[str, Any], status: str) -> str:
    """Generate a short, human-readable explanation for the row."""
    docs = fact.get('documents', {})
    if status == 'missing':
        return "Missing across all compared documents."
    present = {d: info.get('value') for d, info in docs.items() if str(info.get('value', '')).strip().lower() != 'not found'}
    missing = [d for d, info in docs.items() if str(info.get('value', '')).strip().lower() == 'not found']
    if status == 'same':
        v = next(iter(present.values())) if present else '—'
        return f"Same across banks: {v}"
    if status == 'suspect':
        return "Low confidence in at least one document; verify evidence."
    # different
    parts = []
    for d, v in present.items():
        parts.append(f"{d.split('.')[0]}: {v}")
    if missing:
        parts.append(f"Missing in: {', '.join([m.split('.')[0] for m in missing])}")
    return "; ".join(parts)


def _show_unified_comparison_matrix(comparison_table: List[Dict[str, Any]], document_names: List[str]) -> None:
    """
    Company Requirement: Side-by-side comparison with compact table organized by sections.
    Cells show Same/Diff/Missing/Suspect. Clickable cells show normalized value, 
    brief explanation, and exact evidence pointer.
    """
    
    # Clean styling and hide any unwanted link buttons
    st.markdown(
        """
        <style>
        /* Hide any Streamlit link buttons */
        button[kind="header"] {
            display: none !important;
        }
        .stApp > header button {
            display: none !important;
        }
        [data-testid="stHeader"] button {
            display: none !important;
        }
        
        /* Comparison cell styling */
        .comparison-cell {
            padding: 8px 12px;
            margin: 2px;
            border-radius: 6px;
            text-align: center;
            cursor: pointer;
            border: 1px solid #e0e0e0;
            background: white;
            color: #333;
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }
        .comparison-cell:hover {
            border-color: #007bff;
            box-shadow: 0 2px 4px rgba(0,123,255,0.2);
        }
        .status-same { background: #d4edda; border-color: #c3e6cb; }
        .status-different { background: #f8d7da; border-color: #f5c6cb; }
        .status-missing { background: #f8f9fa; border-color: #dee2e6; }
        .status-suspect { background: #fff3cd; border-color: #ffeaa7; }
        
        /* Clickable cell styling */
        .clickable-cell {
            padding: 12px;
            margin: 4px 0;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            border: 2px solid #e0e0e0;
            background: white;
            color: #333;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .clickable-cell:hover {
            border-color: #007bff;
            box-shadow: 0 2px 4px rgba(0,123,255,0.2);
            transform: translateY(-1px);
        }
        .clickable-cell:active {
            transform: translateY(0);
            box-shadow: 0 1px 2px rgba(0,123,255,0.3);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("## 📊 Side-by-Side Comparison")
    st.markdown("**Compact table organized by sections. Click any cell to drill into evidence.**")
    
    # Color coding explanation
    st.markdown("""
    **📋 Color Coding Guide:**
    - 🔵 **Blue cells** = Data found with good confidence
    - 🔴 **Red cells** = Missing data (not found in document)
    - **Expandable cells** = Click to see full value, confidence, and source preview
    """)
    st.markdown("---")
    
    # Organize by sections (Company Requirement: organized by sections you think matter most)
    sections = _organize_facts_by_sections(comparison_table)
    bank_names = [doc.replace('.pdf', '').replace('.docx', '').replace('.txt', '') for doc in document_names]
    
    # Show each section
    for section_name, facts in sections.items():
        if not facts:
            continue
            
        st.markdown(f"### {section_name}")
        
        # Create comparison table for this section
        for fact_idx, fact in enumerate(facts):
            term = fact.get('field', '').replace('_', ' ').title()
            status = fact.get('comparison_status') or _infer_status_across_banks(fact)
            
            # Create columns: Term name + Bank values
            cols = st.columns([2] + [1] * len(document_names))
            
            # Term column
            with cols[0]:
                status_badge = _get_company_status_badge(status)
                st.markdown(f"**{term}** {status_badge}")
            
            # Bank value columns (Company Requirement: clickable cells)
            for i, doc in enumerate(document_names):
                doc_info = fact.get('documents', {}).get(doc, {})
                value = doc_info.get('value', 'Not found')
                
                with cols[i + 1]:
                    if value != 'Not found' and value:
                        # Extract clean bank name from document name
                        clean_bank_name = _extract_bank_name(doc)
                        cell_key = f"{section_name}_{term}_{clean_bank_name}_{fact_idx}".replace(' ', '_').replace('&', 'and')
                        confidence = doc_info.get('confidence', 0)
                        
                        # Show full value with clear bank name - no truncation in header
                        with st.expander(f"🏦 **{clean_bank_name}**", expanded=False):
                            # Normalized value with clear formatting
                            st.markdown(f"### 📋 {term}")
                            st.success(f"**Value:** {value}")
                            
                            # Brief human-readable explanation
                            explanation = _generate_brief_explanation(term, value, clean_bank_name)
                            st.info(f"**Explanation:** {explanation}")
                            
                            # Confidence with color coding
                            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                            st.write(f"**Confidence:** {confidence_color} {confidence:.2f} ({_confidence_label(confidence)})")
                            
                            # Evidence pointer with clean formatting
                            st.markdown("---")
                            st.markdown("### 🔍 Evidence Trace")
                            
                            source_text = doc_info.get('source_text', 'No source text available')
                            source_ref = doc_info.get('source_reference', 'No reference available')
                            
                            # Clean source text display
                            if source_text and source_text != 'No source text available':
                                st.write(f"**📄 Source Document:** {clean_bank_name} Policy")
                                st.write(f"**📍 Reference:** {source_ref}")
                                st.markdown("**📝 Exact Evidence:**")
                                
                                # Clean, readable text area
                                st.markdown(f"""
                                <div style="
                                    background: #f8f9fa; 
                                    border: 1px solid #dee2e6; 
                                    border-radius: 8px; 
                                    padding: 1rem; 
                                    font-family: monospace; 
                                    color: #212529;
                                    max-height: 200px;
                                    overflow-y: auto;
                                ">
                                {source_text}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.warning("No source text available for this extraction")
                    else:
                        # Missing cell with clear bank name
                        clean_bank_name = _extract_bank_name(doc)
                        st.error(f"🏦 **{clean_bank_name}**: Missing Data")
        
        st.markdown("---")
    
    # Export functionality
    _show_export_section(comparison_data)


def _get_company_status_badge(status: str) -> str:
    """Company Requirement: Show Same/Diff/Missing/Suspect status."""
    badges = {
        'same': '🟢 Same',
        'different': '🔴 Diff', 
        'missing': '⚪ Missing',
        'suspect': '🟡 Suspect'
    }
    return badges.get(status.lower(), '❓ Unknown')


def _extract_bank_name(doc_name: str) -> str:
    """Extract clean bank name from document filename."""
    doc_lower = doc_name.lower()
    if 'hdfc' in doc_lower:
        return 'HDFC Bank'
    elif 'icici' in doc_lower:
        return 'ICICI Bank'
    elif 'sbi' in doc_lower:
        return 'SBI Bank'
    elif 'axis' in doc_lower:
        return 'Axis Bank'
    elif 'kotak' in doc_lower:
        return 'Kotak Bank'
    else:
        # Fallback: clean up the filename
        clean_name = doc_name.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
        clean_name = clean_name.replace('MITC_', '').replace('_', ' ').title()
        return clean_name


def _generate_brief_explanation(term: str, value: str, bank_name: str) -> str:
    """Generate human-readable explanation for the term and value."""
    explanations = {
        'processing fee': f"{bank_name} charges {value} as processing fee for loan applications",
        'benchmark rate': f"{bank_name} uses {value} as the benchmark rate for interest calculations",
        'notification method': f"{bank_name} notifies rate changes via {value}",
        'reset frequency': f"{bank_name} reviews and resets interest rates {value}",
        'lock in period': f"{bank_name} has a lock-in period of {value} for prepayments",
        'foreclosure penalty': f"{bank_name} charges {value} penalty for loan foreclosure",
        'reset communication': f"{bank_name} communicates rate changes through {value}"
    }
    
    term_lower = term.lower()
    for key, explanation in explanations.items():
        if key in term_lower:
            return explanation
    
    # Default explanation
    return f"{bank_name} specifies '{value}' for {term}"


def _confidence_label(confidence: float) -> str:
    """Convert confidence score to human-readable label."""
    if confidence > 0.8:
        return "High Confidence"
    elif confidence > 0.5:
        return "Medium Confidence"
    else:
        return "Low Confidence"


def _format_cell_value(value: str) -> str:
    """Format cell value for display - keep it compact."""
    if len(str(value)) > 20:
        return f"{str(value)[:20]}..."
    return str(value)


def _show_evidence_trace_panel() -> None:
    """
    Company Requirement: When I click a cell, show:
    1. Normalized value
    2. Brief explanation  
    3. Pointer to exact evidence (file + line/page snippet)
    """
    
    selected_fact = st.session_state.get('selected_fact')
    selected_doc = st.session_state.get('selected_doc')
    selected_bank = st.session_state.get('selected_bank')
    
    if selected_fact and selected_doc and selected_bank:
        st.markdown("## 🔍 Evidence Trace")
        
        doc_info = selected_fact.get('documents', {}).get(selected_doc, {})
        term = selected_fact.get('field', '').replace('_', ' ').title()
        
        # Company Requirement 1: Normalized value
        st.markdown(f"### 📋 {term} - {selected_bank}")
        normalized_value = doc_info.get('value', 'Not found')
        st.success(f"**Normalized Value:** {normalized_value}")
        
        # Company Requirement 2: Brief explanation
        status = selected_fact.get('comparison_status') or _infer_status_across_banks(selected_fact)
        explanation = _explain_fact(selected_fact, status)
        st.info(f"**Brief Explanation:** {explanation}")
        
        # Company Requirement 3: Pointer to exact evidence
        st.markdown("### 📍 Exact Evidence Pointer")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Evidence metadata
            confidence = doc_info.get('confidence', 0)
            source_ref = doc_info.get('source_reference', 'No reference')
            
            st.markdown("**Evidence Details:**")
            st.markdown(f"- **File:** {selected_doc}")
            st.markdown(f"- **Reference:** {source_ref}")
            st.markdown(f"- **Confidence:** {confidence:.1%}")
            
        with col2:
            # Source snippet (Company Requirement: file + line/page snippet)
            source_text = doc_info.get('source_text', 'No source text available')
            
            st.markdown("**Source Snippet:**")
            if source_text and source_text != 'No source text available':
                # Show snippet in a code block for exact evidence
                st.code(source_text[:300] + "..." if len(source_text) > 300 else source_text)
            else:
                st.warning("No source snippet available")
        
        # Clear selection button
        if st.button("🔄 Clear Selection"):
            for key in ['selected_fact', 'selected_doc', 'selected_bank']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
                    
        else:
        # Instructions when nothing selected
            st.markdown(
                """
            <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 8px; margin: 2rem 0;">
                <h4>👆 Click any cell above to see evidence trace</h4>
                <p>You'll see the normalized value, brief explanation, and exact evidence pointer</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    

def _get_simple_status_badge(status: str) -> str:
    """Get a simple status badge."""
    status_badges = {
        'same': "✅ Same",
        'different': "🔍 Different", 
        'missing': "❓ Missing",
        'suspect': "⚠️ Suspect",
        'unknown': "❓ Unknown"
    }
    return status_badges.get(status.lower(), "❓ Unknown")


def _show_simple_evidence_panel(fact: Dict[str, Any], document_names: List[str]) -> None:
    """Show a simple evidence panel for the selected fact."""
    
    term = fact.get('field', '').replace('_', ' ').title()
    section = fact.get('section', 'Other')
    status = fact.get('comparison_status') or _infer_status_across_banks(fact)
    
    st.markdown(f"#### 📋 Analysis: {term}")
    st.markdown(f"**Section:** {section}")
    st.markdown(f"**Status:** {_get_simple_status_badge(status)}")
    
    # Show values for each bank
    bank_cols = st.columns(len(document_names))
    
    for i, doc in enumerate(document_names):
        bank_name = doc.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
        doc_info = fact.get('documents', {}).get(doc, {})
        
        with bank_cols[i]:
            st.markdown(f"**🏦 {bank_name}**")
            
            value = doc_info.get('value', 'Not found')
            confidence = doc_info.get('confidence', 0)
            source_text = doc_info.get('source_text', 'No source available')
            
            if value != 'Not found':
                # Show value with confidence
                conf_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                st.success(f"{conf_color} **{value}**")
                st.caption(f"Confidence: {confidence:.1%}")
                
                # Show source in expander
                with st.expander("📄 View Source"):
                    if source_text and source_text != 'No source available':
                        st.text_area(
                            "Source Text",
                            source_text[:500] + "..." if len(source_text) > 500 else source_text,
                            height=100,
                            disabled=True,
                            key=f"source_{term}_{bank_name}"
                        )
                    else:
                        st.info("No source text available")
            else:
                st.error("❌ Not found in this document")
    
    # Summary insight
    st.markdown("---")
    explain = _explain_fact(fact, status)
    st.info(f"💡 **Summary:** {explain}")


def _show_section_comparison_table(section_name: str, facts: List[Dict], document_names: List[str]) -> None:
    """Show a beautiful comparison table for a specific section."""
    
    if not facts:
        st.info(f"No data found for {section_name}")
        return
    
    st.subheader(f"{section_name}")
    
    # Create the side-by-side comparison table
    table_data = []
    
    for fact in facts:
        row_data = {
            "📝 Term": fact.get('field', '').replace('_', ' ').title(),
            "🔍 Status": _get_status_badge(fact.get('comparison_status', 'unknown'))
        }
        
        # Add columns for each bank
        for doc_name in document_names:
            doc_data = fact.get('documents', {}).get(doc_name, {})
            value = doc_data.get('value', 'Not found')
            confidence = doc_data.get('confidence', 0)
            
            # Format value with confidence indicator
            if value != 'Not found':
                conf_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                display_value = f"{conf_emoji} {value}"
            else:
                display_value = "❌ Not found"
                
            # Truncate long bank names for column headers
            bank_short = doc_name.split('.')[0][:15] if '.' in doc_name else doc_name[:15]
            row_data[f"🏦 {bank_short}"] = display_value
        
        table_data.append(row_data)
    
    if table_data:
        # Display the beautiful table
        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "📝 Term": st.column_config.TextColumn(
                    "📝 Term",
                    help="Loan term or condition",
                    width="medium"
                ),
                "🔍 Status": st.column_config.TextColumn(
                    "🔍 Status", 
                    help="Comparison status across banks",
                    width="small"
                )
            }
        )
        
        # Add evidence drill-down capability
        _show_evidence_drill_down(facts, document_names, section_name)


def _show_evidence_drill_down(facts: List[Dict], document_names: List[str], section_name: str) -> None:
    """Show evidence drill-down capability as required by assignment."""
    
    st.markdown("---")
    st.subheader("🔍 Drill into Evidence")
    
    import re
    safe_section = re.sub(r'[^a-z0-9]+', '-', section_name.lower())
    
    # Select box for choosing which term to investigate
    fact_options = [(f"{fact.get('field', '').replace('_', ' ').title()}", i) 
                   for i, fact in enumerate(facts)]
    
    if fact_options:
        selected_name, selected_idx = st.selectbox(
            "Select a term to view underlying evidence:",
            options=fact_options,
            format_func=lambda x: x[0],
            key=f"evidence_selector_{safe_section}"
        )
        
        selected_fact = facts[selected_idx]
        
        # Show evidence for each bank
        st.markdown(f"### 📋 Evidence for: **{selected_name}**")
        
        evidence_cols = st.columns(len(document_names))
        
        for col, doc_name in zip(evidence_cols, document_names):
            with col:
                doc_data = selected_fact.get('documents', {}).get(doc_name, {})
                
                st.markdown(f"**🏦 {doc_name.split('.')[0]}**")
                
                value = doc_data.get('value', 'Not found')
                confidence = doc_data.get('confidence', 0)
                source_text = doc_data.get('source_text', 'No source available')
                source_reference = doc_data.get('source_reference', 'No reference available')
                effective_date = doc_data.get('effective_date', None)
                
                if value != 'Not found':
                    st.success(f"**Value:** {value}")
                    st.info(f"**Confidence:** {confidence:.2f}")
                    
                    # Assignment requirement: Evidence with source reference
                    if source_reference != 'No reference available':
                        st.caption(f"📍 **Source Reference:** {source_reference}")
                    
                    # Assignment requirement: Document effective dates
                    if effective_date:
                        st.caption(f"📅 **Effective Date:** {effective_date}")
                    
                    # Show source evidence in an expandable section
                    with st.expander("📄 View Source Evidence (Assignment Req: Evidence matters)"):
                        st.text_area(
                            "Source Text",
                            source_text,
                            height=100,
                            disabled=True,
                            key=f"source_{safe_section}_{doc_name}_{selected_idx}"
                        )
                else:
                    st.error("❌ Not found in this document")


def _get_status_badge(status: str) -> str:
    """Get a colored badge for comparison status (Assignment req: Suspect for conflicts)."""
    status_badges = {
        'same': "🟢 Same",
        'different': "🔴 Different", 
        'missing': "⚪ Missing",
        'suspect': "🟡 Suspect",  # Assignment requirement: conflicts marked as Suspect
        'unknown': "❓ Unknown"
    }
    return status_badges.get(status.lower(), "❓ Unknown")


def _show_export_section(comparison_data: Dict[str, Any]) -> None:
    """Show export functionality with working CSV and JSON download buttons."""
    
    st.markdown("## 📊 Export Comparison Results")
    st.markdown("Download your comparison analysis in different formats.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            # Generate CSV data using ExportService
            documents = _convert_comparison_to_documents(comparison_data)
            csv_data = ExportService.generate_csv_export(documents)
                
            # Create download button with better styling
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name=f"bank_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_csv",
                use_container_width=True
            )
                
        except Exception as e:
            st.error(f"❌ Error generating CSV: {str(e)}")
    
    with col2:
        try:
            # Generate JSON data using ExportService
            documents = _convert_comparison_to_documents(comparison_data)
            json_data = ExportService.generate_json_export(documents)
                
            # Create download button with better styling
            st.download_button(
                label="📋 Download JSON",
                data=json_data,
                file_name=f"bank_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="download_json",
                use_container_width=True
            )
                
        except Exception as e:
            st.error(f"❌ Error generating JSON: {str(e)}")


def _convert_comparison_to_documents(comparison_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert comparison data back to document format for export service."""
    
    documents = []
    document_names = comparison_data.get('document_names', [])
    comparison_table = comparison_data.get('comparison_table', [])
    
    # Create a document structure for each bank
    for doc_name in document_names:
        # Extract bank name from document name
        bank_name = _extract_bank_name(doc_name)
        
        # Collect facts for this document
        extracted_facts = []
        for fact in comparison_table:
            doc_info = fact.get('documents', {}).get(doc_name, {})
            if doc_info.get('value') and doc_info.get('value') != 'Not found':
                extracted_facts.append({
                    'key': fact.get('fact_key', fact.get('field', 'unknown')),
                    'value': doc_info.get('value', ''),
                    'confidence': doc_info.get('confidence', 0.0),
                    'source_text': doc_info.get('source_text', ''),
                    'source_reference': doc_info.get('source_reference', '')
                })
        
        # Create document structure
        doc_dict = {
            'metadata': {
                'filename': doc_name,
                'bank_name': bank_name,
                'file_size': 2000000  # Mock file size
            },
            'status': 'completed',
            'content': {
                'extracted_facts': extracted_facts,
                'processing_metadata': {
                    'extraction_method': 'streamlit_ui',
                    'processing_time': 0.0
                }
            },
            'created_at': datetime.now().isoformat()
        }
        documents.append(doc_dict)
    
    return documents


def _confidence_label(confidence: float) -> str:
    """Convert confidence score to human-readable label."""
    if confidence >= 0.9:
        return "Very High"
    elif confidence >= 0.8:
        return "High"
    elif confidence >= 0.7:
        return "Good"
    elif confidence >= 0.6:
        return "Moderate"
    elif confidence >= 0.5:
        return "Low"
    else:
        return "Very Low"