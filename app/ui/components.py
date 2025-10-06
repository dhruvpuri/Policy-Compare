"""UI components for the Streamlit application."""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any


def show_document_details(documents: List[Dict[str, Any]]):
    """Display document details in a formatted way."""
    
    if not documents:
        st.info("No documents uploaded yet.")
        return
    
    st.subheader("📄 Uploaded Documents")
    
    for doc in documents:
        with st.expander(f"📋 {doc.get('metadata', {}).get('filename', 'Unknown Document')}"):
            metadata = doc.get('metadata', {})
            content = doc.get('content', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**File Details:**")
                st.write(f"• **Filename:** {metadata.get('filename', 'N/A')}")
                st.write(f"• **Format:** {metadata.get('format', 'N/A')}")
                st.write(f"• **Size:** {metadata.get('size_bytes', 'N/A')} bytes")
                st.write(f"• **Bank:** {metadata.get('bank_name', 'N/A')}")
            
            with col2:
                st.write("**Processing Status:**")
                status = doc.get('processing_status', 'Unknown')
                if status == 'completed':
                    st.success(f"✅ {status.title()}")
                elif status == 'processing':
                    st.info(f"⏳ {status.title()}")
                elif status == 'failed':
                    st.error(f"❌ {status.title()}")
                else:
                    st.warning(f"⚠️ {status.title()}")
            
            # Show extracted facts count
            facts = content.get('extracted_facts', [])
            if facts:
                st.write(f"**Extracted Facts:** {len(facts)}")
                
                # Show first few facts as preview
                if len(facts) > 0:
                    st.write("**Preview of extracted facts:**")
                    preview_facts = facts[:3]
                    for fact in preview_facts:
                        st.write(f"• **{fact.get('key', 'Unknown')}:** {fact.get('value', 'N/A')[:100]}...")


def show_processing_stats(documents: List[Dict[str, Any]]):
    """Display processing statistics."""
    
    if not documents:
        return
    
    total_docs = len(documents)
    completed_docs = sum(1 for doc in documents if doc.get('processing_status') == 'completed')
    processing_docs = sum(1 for doc in documents if doc.get('processing_status') == 'processing')
    failed_docs = sum(1 for doc in documents if doc.get('processing_status') == 'failed')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Documents", total_docs)
    
    with col2:
        st.metric("✅ Completed", completed_docs)
    
    with col3:
        st.metric("⏳ Processing", processing_docs)
    
    with col4:
        st.metric("❌ Failed", failed_docs)
    
    # Show progress bar
    if total_docs > 0:
        progress = completed_docs / total_docs
        st.progress(progress)
        st.write(f"Overall Progress: {progress:.1%}")


def show_fact_comparison_table(documents: List[Dict[str, Any]]):
    """Display extracted facts in a comparison table format."""
    
    if not documents:
        st.info("No documents to compare yet.")
        return
    
    # Filter completed documents
    completed_docs = [doc for doc in documents if doc.get('processing_status') == 'completed']
    
    if not completed_docs:
        st.warning("No completed documents to display facts for.")
        return
    
    st.subheader("🔍 Extracted Facts Comparison")
    
    # Collect all unique fact keys
    all_fact_keys = set()
    for doc in completed_docs:
        facts = doc.get('content', {}).get('extracted_facts', [])
        for fact in facts:
            all_fact_keys.add(fact.get('key', ''))
    
    if not all_fact_keys:
        st.info("No extracted facts found in the documents.")
        return
    
    # Build comparison data
    comparison_data = {}
    
    for fact_key in sorted(all_fact_keys):
        comparison_data[fact_key] = {}
        
        for doc in completed_docs:
            filename = doc.get('metadata', {}).get('filename', 'Unknown')
            bank_name = doc.get('metadata', {}).get('bank_name', 'Unknown Bank')
            doc_key = f"{bank_name} ({filename})"
            
            # Find the fact value for this document
            facts = doc.get('content', {}).get('extracted_facts', [])
            fact_value = "Not found"
            
            for fact in facts:
                if fact.get('key') == fact_key:
                    fact_value = fact.get('value', 'N/A')
                    break
            
            comparison_data[fact_key][doc_key] = fact_value
    
    # Convert to DataFrame for better display
    df_data = []
    for fact_key, doc_values in comparison_data.items():
        row = {'Fact': fact_key}
        row.update(doc_values)
        df_data.append(row)
    
    if df_data:
        df = pd.DataFrame(df_data)
        
        # Use expandable sections for different categories
        categories = {}
        for fact_key in all_fact_keys:
            if '.' in fact_key:
                category = fact_key.split('.')[0]
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append(fact_key)
        
        # Display facts by category
        for category, fact_keys in categories.items():
            with st.expander(f"📋 {category.replace('_', ' ').title()} ({len(fact_keys)} facts)"):
                category_data = [row for row in df_data if row['Fact'] in fact_keys]
                if category_data:
                    category_df = pd.DataFrame(category_data)
                    st.dataframe(category_df, use_container_width=True, hide_index=True)
    else:
        st.info("No facts to display in comparison table.")



