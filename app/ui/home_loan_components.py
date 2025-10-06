"""Specialized UI components for home loan document processing."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any


def show_home_loan_facts_summary(facts: List[Dict[str, Any]], bank_name: str = "Unknown Bank"):
    """Display a structured summary of home loan facts with modern styling."""
    if not facts:
        st.markdown(
            """
            <div style="text-align: center; padding: 2rem; background: var(--bg); 
                       border-radius: 16px; border: 2px dashed var(--border);">
                <div style="font-size: 2rem; margin-bottom: 1rem;">📄</div>
                <h3 style="color: var(--muted); margin: 0;">No facts extracted from this document</h3>
                <p style="color: var(--muted); margin: 0.5rem 0 0 0;">
                    Try uploading a different document or check if the file is readable
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return
    
    # Clean bank name for display
    clean_bank_name = bank_name.replace('.pdf', '').replace('.docx', '').replace('.txt', '').replace('_', ' ')
    
    # Modern header for the bank summary
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 2rem; padding: 2rem; 
                   background: linear-gradient(135deg, var(--primary) 0%, #F4C430 100%); 
                   border-radius: 20px; box-shadow: 0 4px 20px rgba(255, 215, 0, 0.2);">
            <h2 style="margin: 0; color: var(--dark); font-weight: 800;">
                🏠 {clean_bank_name}
            </h2>
            <p style="margin: 0.5rem 0 0 0; color: var(--secondary); opacity: 0.8; font-size: 1.1rem;">
                Extracted {len(facts)} key terms from loan document
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Organize facts by home loan sections with modern icons
    sections = {
        "LTV Bands": {"icon": "📊", "color": "var(--primary)", "facts": []},
        "Processing Fees And Charges": {"icon": "💰", "color": "var(--success)", "facts": []},
        "Prepayment And Foreclosure": {"icon": "⚡", "color": "var(--warning)", "facts": []},
        "Eligibility Criteria": {"icon": "✅", "color": "var(--success)", "facts": []},
        "Tenure Options": {"icon": "📅", "color": "var(--primary)", "facts": []},
        "Interest Reset And Communication": {"icon": "🔄", "color": "var(--warning)", "facts": []},
        "Required Documents": {"icon": "📄", "color": "var(--muted)", "facts": []},
        "Grievance And Customer Service": {"icon": "🎧", "color": "var(--error)", "facts": []}
    }
    
    # Categorize facts into sections
    for fact in facts:
        fact_key = fact.get('key', '').lower()
        section_assigned = False
        
        # Try to match to a section
        for section_name, section_data in sections.items():
            section_keywords = section_name.lower().split()
            if any(keyword in fact_key for keyword in section_keywords):
                section_data["facts"].append(fact)
                section_assigned = True
                break
        
        # If no match, put in "Other"
        if not section_assigned:
            if "Other" not in sections:
                sections["Other"] = {"icon": "❓", "color": "var(--muted)", "facts": []}
            sections["Other"]["facts"].append(fact)
    
    # Display each section
    for section_name, section_data in sections.items():
        if not section_data["facts"]:
            continue
            
        st.markdown(f"### {section_data['icon']} {section_name}")
        
        # Create columns for facts in this section
        fact_cols = st.columns(min(len(section_data["facts"]), 3))
        
        for i, fact in enumerate(section_data["facts"]):
            with fact_cols[i % len(fact_cols)]:
                # Extract key information
                fact_key = fact.get('key', 'Unknown').replace('_', ' ').title()
                fact_value = fact.get('value', 'Not specified')
                confidence = fact.get('confidence', 0.0)
                
                # Determine confidence color
                if confidence > 0.8:
                    conf_color = "var(--success)"
                elif confidence > 0.5:
                    conf_color = "var(--warning)"
                else:
                    conf_color = "var(--error)"
                
                # Display fact card
                st.markdown(
                    f"""
                    <div style="background: var(--card); border-radius: 16px; border: 1px solid var(--border); 
                               padding: 1rem; margin-bottom: 1rem; text-align: center;">
                        <h4 style="margin: 0 0 0.5rem 0; color: var(--dark); font-size: 1rem; font-weight: 600;">
                            {fact_key}
                        </h4>
                        <p style="margin: 0; color: var(--secondary); font-size: 1.1rem; font-weight: 500;">
                            {fact_value}
                        </p>
                        <div style="margin-top: 0.5rem;">
                            <div style="background: {conf_color}; border-radius: 8px; padding: 0.3rem 0.6rem; 
                                       font-size: 0.8rem; color: white; font-weight: 600;">
                                {confidence:.1%} Confidence
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        st.markdown("---")


def show_processing_progress(document_status: str, facts_count: int = 0, conflicts_count: int = 0):
    """Show processing progress for a document."""
    st.subheader("🔄 Processing Status")
    
    if document_status == "pending":
        st.info("⏳ Document queued for processing...")
        st.progress(0.2)
        
    elif document_status == "processing":
        st.info("🤖 AI is analyzing your home loan document...")
        st.progress(0.6)
        
    elif document_status == "completed":
        st.success("✅ Document processed successfully!")
        st.progress(1.0)
        
        # Show results summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Facts Extracted", facts_count, delta="Complete")
        with col2:
            st.metric("Conflicts Found", conflicts_count, delta="Review needed" if conflicts_count > 0 else "Clean")
        with col3:
            st.metric("Status", "Ready", delta="For comparison")
            
    elif document_status == "failed":
        st.error("❌ Processing failed")
        st.progress(0.0)
        
        # Show troubleshooting tips
        with st.expander("🛠️ Troubleshooting"):
            st.markdown("""
            **Common issues:**
            - Document might be password protected
            - File might be corrupted or unreadable
            - Document might not contain home loan terms
            - API rate limit exceeded (try again in a moment)
            
            **Solutions:**
            - Try uploading a different format (PDF → TXT or vice versa)
            - Ensure the document contains home loan policy information
            - Check that the document is not scanned (needs to be text-selectable)
            """)


def show_comparison_summary_cards(comparison_stats: Dict[str, int]):
    """Show summary cards for comparison results."""
    st.subheader("📊 Comparison Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total = sum(comparison_stats.values())
    
    with col1:
        same_pct = (comparison_stats.get('same', 0) / max(total, 1)) * 100
        st.metric(
            "✅ Same Policies", 
            comparison_stats.get('same', 0),
            delta=f"{same_pct:.1f}%",
            delta_color="normal"
        )
        
    with col2:
        diff_pct = (comparison_stats.get('different', 0) / max(total, 1)) * 100
        st.metric(
            "🔴 Different Terms", 
            comparison_stats.get('different', 0),
            delta=f"{diff_pct:.1f}%",
            delta_color="inverse"
        )
        
    with col3:
        missing_pct = (comparison_stats.get('missing', 0) / max(total, 1)) * 100
        st.metric(
            "⚪ Missing Info", 
            comparison_stats.get('missing', 0),
            delta=f"{missing_pct:.1f}%",
            delta_color="off"
        )
        
    with col4:
        suspect_pct = (comparison_stats.get('suspect', 0) / max(total, 1)) * 100
        st.metric(
            "🟡 Suspect Data", 
            comparison_stats.get('suspect', 0),
            delta=f"{suspect_pct:.1f}%",
            delta_color="off"
        )
    
    # Add interpretation
    st.markdown("---")
    if same_pct > 60:
        st.success("🎯 **High similarity** - Banks have similar policies in most areas")
    elif diff_pct > 40:
        st.warning("⚠️ **Significant differences** - Review varying terms carefully")
    else:
        st.info("📋 **Mixed results** - Some similarities and differences found")


def show_bank_selector(documents: List[Dict], max_selections: int = 4):
    """Enhanced bank selector with modern Butter Money styling."""
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h3 style="color: var(--dark); margin-bottom: 0.5rem;">🏦 Select Banks to Compare</h3>
            <p style="color: var(--muted); margin: 0;">Choose 2-4 documents from different banks for comprehensive analysis</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if not documents:
        st.markdown(
            """
            <div style="text-align: center; padding: 3rem; background: var(--diff-bg); 
                       border-radius: 16px; border: 2px solid var(--diff-border);">
                <div style="font-size: 2rem; margin-bottom: 1rem;">📄</div>
                <h3 style="color: var(--dark); margin: 0;">No processed documents available</h3>
                <p style="color: var(--muted); margin: 0.5rem 0 0 0;">
                    Upload some home loan documents first to start comparing
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return []
    
    # Create enhanced options with modern preview cards
    bank_options = {}
    
    # Display available documents as cards first
    st.markdown("### 📚 Available Documents")
    
    # Show documents in a grid
    cols = st.columns(3)
    for idx, doc in enumerate(documents):
        col_idx = idx % 3
        
        with cols[col_idx]:
            bank_name = doc['metadata'].get('bank_name', 'Unknown Bank')
            filename = doc['metadata']['filename']
            facts_count = len(doc.get('content', {}).get('extracted_facts', []))
            status = doc.get('status', 'unknown')
            
            # Clean filename for display
            clean_filename = filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
            
            # Status styling
            status_styles = {
                'completed': {'icon': '✅', 'color': 'var(--butter-success)', 'text': 'Ready'},
                'processing': {'icon': '⏳', 'color': 'var(--butter-warning)', 'text': 'Processing'},
                'failed': {'icon': '❌', 'color': 'var(--butter-error)', 'text': 'Failed'}
            }
            style = status_styles.get(status, {'icon': '❓', 'color': 'var(--butter-muted)', 'text': 'Unknown'})
            
            # Create document card
            display_name = f"{bank_name} - {clean_filename}"
            bank_options[display_name] = doc
            
            st.markdown(
                f"""
                <div style="background: var(--butter-card); border-radius: 12px; border: 1px solid var(--butter-border); 
                           padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);">
                    <div style="display: flex; justify-content: between; align-items: start; margin-bottom: 1rem;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 0.3rem 0; color: var(--butter-dark); font-size: 1.1rem;">
                                {bank_name}
                            </h4>
                            <p style="margin: 0; color: var(--butter-muted); font-size: 0.9rem;">
                                {clean_filename}
                            </p>
                        </div>
                        <span style="background: {style['color']}; color: white; padding: 0.2rem 0.5rem; 
                                    border-radius: 12px; font-size: 0.75rem; font-weight: 600;">
                            {style['icon']} {style['text']}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--butter-secondary); font-size: 0.9rem; font-weight: 500;">
                            📊 {facts_count} terms extracted
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Multi-select with better styling
    st.markdown("### 🎯 Make Your Selection")
    selected_banks = st.multiselect(
        f"Choose documents to compare (2-{max_selections} recommended):",
        options=list(bank_options.keys()),
        max_selections=max_selections,
        help="Select documents from different banks for meaningful comparison",
        placeholder="Select banks to compare..."
    )
    
    # Show selected documents preview
    if selected_banks:
        st.markdown("### ✅ Selected for Comparison")
        
        selected_cols = st.columns(min(len(selected_banks), 4))  # Max 4 columns
        
        for idx, bank_display in enumerate(selected_banks):
            col_idx = idx % 4
            doc = bank_options[bank_display]
            
            with selected_cols[col_idx]:
                bank_name = doc['metadata'].get('bank_name', 'Unknown')
                facts_count = len(doc.get('content', {}).get('extracted_facts', []))
                
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, var(--butter-primary) 0%, #F4C430 100%); 
                               border-radius: 12px; padding: 1rem; text-align: center; 
                               box-shadow: 0 2px 8px rgba(255, 215, 0, 0.3);">
                        <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">🏦</div>
                        <h4 style="margin: 0; color: var(--butter-dark); font-size: 0.9rem; font-weight: 700;">
                            {bank_name}
                        </h4>
                        <p style="margin: 0.3rem 0 0 0; color: var(--butter-secondary); font-size: 0.8rem;">
                            {facts_count} terms
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        
        # Show comparison readiness
        if len(selected_banks) >= 2:
            st.success(f"✅ Ready to compare {len(selected_banks)} banks! Scroll down to see the analysis.")
        elif len(selected_banks) == 1:
            st.info("💡 Select at least one more bank to start comparison.")
    
    return [bank_options[name] for name in selected_banks]


def show_export_options(selected_docs: List[Dict]):
    """Enhanced export options with previews."""
    if not selected_docs:
        return
        
    st.subheader("📥 Export Comparison Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Excel Analysis (CSV)")
        st.markdown("""
        - Tabular format for spreadsheet analysis
        - Includes confidence scores and status
        - Easy filtering and sorting
        - Perfect for operational review
        """)
        
        if st.button("📄 Generate CSV Report", key="csv_export"):
            from app.services.export_service import ExportService
            csv_data = ExportService.generate_csv_export(selected_docs)
            bank_names = [doc['metadata'].get('bank_name', 'Unknown') for doc in selected_docs]
            filename = f"home_loan_comparison_{'_vs_'.join(bank_names[:2])}.csv"
            
            st.download_button(
                label="💾 Download CSV Report",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
                help="Download structured comparison data for Excel analysis"
            )
    
    with col2:
        st.markdown("#### 🔧 System Integration (JSON)")
        st.markdown("""
        - Complete metadata and analysis
        - Structured for programmatic use
        - Includes confidence scores and evidence
        - API-ready format
        """)
        
        if st.button("📄 Generate JSON Report", key="json_export"):
            from app.services.export_service import ExportService
            json_data = ExportService.generate_json_export(selected_docs)
            bank_names = [doc['metadata'].get('bank_name', 'Unknown') for doc in selected_docs]
            filename = f"home_loan_analysis_{'_vs_'.join(bank_names[:2])}.json"
            
            st.download_button(
                label="💾 Download JSON Report", 
                data=json_data,
                file_name=filename,
                mime="application/json",
                help="Download complete analysis data for system integration"
            )