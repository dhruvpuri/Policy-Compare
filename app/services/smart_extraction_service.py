#!/usr/bin/env python3
"""
Smart Extraction Service - Hybrid approach to minimize Gemini usage while maximizing coverage.
1. Rule-based extraction first
2. Identify gaps
3. Ask Gemini only for missing terms
4. Combine results
"""

from typing import List, Dict, Set, Optional
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app.models.document import ExtractedFact, Document
from app.services.rule_based_extraction import RuleBasedExtractionService
from app.services.llm_service import LLMExtractionService
from app.services.normalization_service import NormalizationService


class SmartExtractionService:
    """Smart hybrid extraction service to maximize coverage while minimizing API calls."""
    
    # FOCUSED ON 8 PRIORITY SECTIONS (aligned with user requirements)
    EXPECTED_TERMS = {
        "fees_and_charges": [
            "processing_fee", "administrative_fee", "legal_charges", "valuation_charges", 
            "documentation_charges", "conversion_fee", "handling_charges"
        ],
        "prepayment_and_foreclosure": [
            "prepayment_penalty", "foreclosure_charges", "prepayment_option", "lock_in_period", "partial_prepayment"
        ],
        "loan_amount_and_ltv": [
            "ltv_ratio", "ltv_bands", "property_value", "loan_amount_limit", "financing_ratio"
        ],
        "eligibility": [
            "minimum_income", "cibil_score", "age_limit", "employment_type", "experience_requirement", "salary_requirement"
        ],
        "repayment": [
            "tenure", "maximum_tenure", "minimum_tenure", "repayment_period", "term_period"
        ],
        "interest_rates": [
            "reset_frequency", "benchmark_rate", "rate_change_communication", "notification_method"
        ],
        "documents": [
            "required_documents", "kyc_documents", "income_proof", "identity_proof", "property_documents"
        ],
        "grievance": [
            "process", "complaint_procedure", "customer_service", "dispute_resolution"
        ],
        # NEW PRIORITY CATEGORIES
        "penal_charges": [
            "late_payment_penalty", "bounce_charges", "default_interest"
        ],
        "security_and_insurance": [
            "primary_security", "property_mortgage", "insurance_requirement", "insurance_coverage"
        ]
    }
    
    def __init__(self, llm_service: Optional[LLMExtractionService] = None, 
                 normalization_service: Optional[NormalizationService] = None):
        """Initialize smart extraction service."""
        self.rule_extractor = RuleBasedExtractionService()
        self.llm_service = llm_service
        self.normalization_service = normalization_service or NormalizationService()
        # Debug helpers
        self.last_focused_prompt: Optional[str] = None
        self.last_prompt_meta: Optional[Dict[str, str]] = None
    
    async def extract_facts_smart(self, document_text: str, filename: str, document_id: str) -> List[ExtractedFact]:
        """
        Smart extraction: Rule-based first, then targeted LLM for gaps.
        
        Args:
            document_text: Full document text
            filename: Document filename
            document_id: Document ID
            
        Returns:
            Combined list of extracted facts
        """
        
        print(f"\n[SMART] SMART EXTRACTION for {filename}")
        print("=" * 50)
        
        # PHASE 1: Rule-based extraction
        print("[PHASE] Phase 1: Rule-based extraction...")
        rule_facts = self.rule_extractor.extract(document_text, filename)
        print(f"   [OK] Rule-based found: {len(rule_facts)} facts")
        
        # PHASE 2: Gap analysis
        print("[PHASE] Phase 2: Analyzing gaps...")
        gaps = self._analyze_gaps(rule_facts)
        print(f"   [MISSING] Missing terms: {len(gaps)} categories")
        for category, missing_terms in gaps.items():
            if missing_terms:
                print(f"     - {category}: {len(missing_terms)} terms missing")
        
        # PHASE 3: Targeted LLM extraction (only for gaps)
        llm_facts = []
        if self.llm_service and gaps:
            print("[PHASE] Phase 3: Targeted LLM extraction for gaps...")
            llm_facts = await self._extract_missing_with_llm(document_text, gaps, filename, document_id)
            print(f"   [OK] LLM found additional: {len(llm_facts)} facts")
        
        # PHASE 4: Combine and normalize
        print("[PHASE] Phase 4: Combining and normalizing...")
        all_facts = rule_facts + llm_facts
        
        if self.normalization_service:
            all_facts = self.normalization_service.normalize_facts(all_facts)
        
        print(f"[DONE] SMART EXTRACTION COMPLETE: {len(all_facts)} total facts")
        self._show_coverage_summary(all_facts)
        
        return all_facts
    
    def _analyze_gaps(self, rule_facts: List[ExtractedFact]) -> Dict[str, List[str]]:
        """Analyze gaps, focusing on high-value terms likely to exist in template docs."""
        
        found_terms = set()
        for fact in rule_facts:
            # Extract the term from the fact key (e.g., "fees_and_charges.processing_fee" -> "processing_fee")
            if '.' in fact.key:
                section, term = fact.key.split('.', 1)
                found_terms.add(f"{section}.{term}")
            else:
                found_terms.add(fact.key)
        
        # Focus on high-value terms for template MITC documents
        HIGH_VALUE_TERMS = {
            "fees_and_charges": ["processing_fee", "administrative_fee", "legal_charges", "valuation_charges"],
            "prepayment_and_foreclosure": ["prepayment_penalty", "foreclosure_charges", "lock_in_period"],
            "interest_rates": ["reset_frequency", "benchmark_rate", "rate_change_communication", "notification_method"],
            "documents": ["required_documents", "kyc_documents"],
            "grievance": ["process", "complaint_procedure", "customer_service"],
            # Skip sections with likely blank template fields: loan_amount_and_ltv, eligibility, repayment
        }
        
        gaps = {}
        for section, high_value_terms in HIGH_VALUE_TERMS.items():
            missing = []
            for term in high_value_terms:
                full_key = f"{section}.{term}"
                if full_key not in found_terms:
                    missing.append(term)
            if missing:  # Only include sections with actual gaps
                gaps[section] = missing
        
        return gaps
    
    async def _extract_missing_with_llm(self, document_text: str, gaps: Dict[str, List[str]], 
                                      filename: str, document_id: str) -> List[ExtractedFact]:
        """Use LLM to extract only the missing terms."""
        focused_prompt = self.build_focused_prompt(document_text, gaps, filename)
        if not focused_prompt:
            return []
        # Record last prompt for debugging
        self.last_focused_prompt = focused_prompt
        self.last_prompt_meta = {"filename": filename, "document_id": document_id}
        
        try:
            print(f"   [ASK] Asking LLM for {sum(len(terms) for terms in gaps.values())} missing terms...")
            llm_facts = await self.llm_service.extract_facts_with_prompt(document_text, focused_prompt, document_id)
            
            # Filter to only the terms we actually asked for
            filtered_facts = []
            for fact in llm_facts:
                section_term = fact.key
                section = section_term.split('.')[0] if '.' in section_term else section_term
                term = section_term.split('.')[1] if '.' in section_term else section_term
                
                if section in gaps and term in gaps[section]:
                    filtered_facts.append(fact)
                    print(f"     [OK] Found missing: {fact.key} = {fact.value}")
            
            return filtered_facts
            
        except Exception as e:
            print(f"   [ERROR] LLM extraction failed: {e}")
            return []

    def build_focused_prompt(self, document_text: str, gaps: Dict[str, List[str]], filename: str) -> Optional[str]:
        """Build the focused LLM prompt for the given gaps without calling the LLM."""
        # Build a targeted prompt focusing only on missing terms
        missing_sections: List[str] = []
        for section, missing_terms in gaps.items():
            if missing_terms:
                missing_sections.append(f"{section}: {', '.join(missing_terms)}")
        if not missing_sections:
            return None

        # Detect bank from filename or content hints for bank-specific instructions
        bank_hint = ""
        fname_upper = (filename or "").upper()
        if any(tag in fname_upper for tag in ["SBI", "STATE BANK"]):
            bank_hint = "SBI"
        elif "HDFC" in fname_upper:
            bank_hint = "HDFC"
        elif "ICICI" in fname_upper:
            bank_hint = "ICICI"
        elif any(tag in fname_upper for tag in ["DBS", "HSBC"]):
            bank_hint = "DBS/HSBC"

        bank_specific = ""
        if bank_hint == "SBI":
            bank_specific = "\nBANK-SPECIFIC: Extract penal charges, tiered LTV, NRI/defense/PSU employee criteria.\n"
        elif bank_hint == "HDFC":
            bank_specific = "\nBANK-SPECIFIC: Extract individual vs non-individual prepayment rules and lock-in nuances.\n"
        elif bank_hint == "ICICI":
            bank_specific = "\nBANK-SPECIFIC: Extract insurance mandates and special eligibility clauses.\n"
        elif bank_hint == "DBS/HSBC":
            bank_specific = "\nBANK-SPECIFIC: Extract fee schedules and security interest details.\n"

        # Example blocks inserted as plain strings to avoid f-string brace issues (Windows-safe)
        examples_block = (
            '[{"section":"Penal Charges","field":"late_payment_penalty","value":"2% p.a. over EBR","source_text":"Penal interest @ 2% p.a. over EBR","confidence":0.9}]\n'
            '[{"section":"Loan Amount & LTV","field":"ltv_bands","value":"[{\\"ltv\\":\\"90%\\",\\"min_amount\\":0,\\"max_amount\\":3000000}]","source_text":"90% - Up to Rs.30 Lakhs","confidence":0.9}]\n'
            '[{"section":"Security & Insurance","field":"insurance_requirement","value":"INR 500,000 minimum","source_text":"Insurance coverage: Rs.5L minimum","confidence":0.9}]\n'
            # Added examples
            '[{"section":"Prepayment & Foreclosure","field":"lock_in_period","value":"6 months","source_text":"Lock-in period: 6 months","confidence":0.9}]\n'
            '[{"section":"Prepayment & Foreclosure","field":"lock_in_period","value":"first 12 EMI","source_text":"Lock-in period: first 12 EMI","confidence":0.9}]\n'
            '[{"section":"Documents","field":"required_documents","value":"List of documents: ID proof, address proof","source_text":"List of documents: ID proof, address proof","confidence":0.9}]\n'
            '[{"section":"Documents","field":"required_documents","value":"Duplicate copy of welcome pack, amortisation schedule, key fact statement","source_text":"Request for duplicate copy of welcome pack, amortisation schedule, key fact statement","confidence":0.9}]'
        )
        return_format_block = (
            '[{"section": "section_name", "field": "field_name", "value": "extracted_value", '
            '"source_text": "exact quote", "confidence": 0.9}]'
        )

        focused_prompt = f"""
PROMPT_VERSION: v1.3
{('THIS IS A ' + bank_hint + ' HOME-LOAN MITC DOCUMENT.' if bank_hint else '').strip()}

You are completing a loan document analysis. Advanced rule-based extraction has already found most terms, but these HARD-TO-FIND terms are still MISSING:

{chr(10).join(missing_sections)}

FOCUS ONLY on these specific missing terms. Our rules now handle common patterns, so look for:

DIFFICULT PATTERNS TO FIND:

PENAL CHARGES & LATE PAYMENTS:
- Look for: "Penal interest @ 2% p.a. over EBR", "Late payment charge: 2% p.a.", "Default interest rate: 2% over applicable rate"
- Bounce charges: "Bounce charge: Rs.500", "Returned cheque charges"
- Penal interest rates: Often buried in fine print or penalty sections

TIERED LTV RATIOS:
- Look for: "Loan-to-Value Ratio: Up to 90% for loans up to Rs.30 Lakhs", "LTV: Up to 80% for loans up to Rs.50 Lakhs"
- Table format: "90% - Up to Rs.30 Lakhs", "80% - Up to Rs.50 Lakhs", "75% - Above Rs.50 Lakhs"
- Maximum LTV: "Maximum LTV: 90% for loans up to Rs.30 Lakhs"

INSURANCE & SECURITY REQUIREMENTS:
- Insurance coverage: "Insurance coverage: Rs.5 Lakhs minimum", "Life insurance: Mandatory"
- Property insurance: "Property insurance: As per bank's requirement", "Fire insurance: Compulsory"
- Primary security: "Primary security: Property mortgage", "Security: Equitable mortgage"

SPECIAL ELIGIBILITY CATEGORIES:
- NRI: "NRI: Eligible with additional documentation", "Non-Resident Indian: Special rates"
- Defense personnel: "Defense personnel: Special rates available", "Armed forces: Concessional rates"
- Government employees: "Government employees: Concessional rates", "Public sector: Special rates"

COMPOUND FEES:
- Look for: "1.50% or Rs.4,500 whichever is higher", "2% or Rs.5,000 whichever is lower"
- Processing fees with minimum/maximum: "0.50% to 3.00% (min Rs.2,000, max Rs.10,000)"

FEES & CHARGES:
- Administrative fees: Often in fine print as "Admin fee", "Documentation charges", or in tariff schedules
- Legal/Valuation charges: May be listed as "As applicable", "As per actuals", or ranges
- Template fields: Look for "___", "[ ]", blank spaces after fee names

ELIGIBILITY CRITERIA:
- Income requirements: "Net monthly income", "Salary requirement", "Income criteria"
- CIBIL score: May be stated as "Credit score", "Credit rating", "Score requirement"
- Age limits: "Age criteria", "Maximum/Minimum age", "Age at loan maturity"
- Employment: "Service requirement", "Experience needed", "Employment criteria"

DOCUMENTS REQUIRED:
- Income proof: "Salary slips", "Income documents", "ITR", "Form 16"
- Identity/Address: "KYC documents", "ID proof", "Address proof"
- Property papers: "Sale deed", "NOC", "Approved plans"

GRIEVANCE & SUPPORT:
- Contact details: Phone numbers, email IDs, website URLs
- Escalation process: "Level 1", "Level 2", "Ombudsman", "Senior Manager"
- Timeline: "7 days", "15 days", response time commitments

ENHANCED EXTRACTION STRATEGY:{bank_specific}
- Check TABLES and SCHEDULES for fee structures and LTV bands
- Look in APPENDICES and separate sections for document lists
- Scan for NUMERICAL VALUES (age limits, income thresholds, percentages)
- Find CONTACT INFORMATION (phone, email, branch details)
- Look for POLICY STATEMENTS with specific criteria
- Check FOOTNOTES and small print sections
- Search for CLAUSE REFERENCES that might contain details
- Look for PENALTY SECTIONS and INSURANCE CLAUSES
- Check for SPECIAL CATEGORY MENTIONS (NRI, defense, government)

TEMPLATE HANDLING:
- If fields are blank ("___", "[ ]", empty spaces), return "Template field - value not specified"
- If values say "As applicable" or "As per actuals", include that exact text
- If ranges are given ("18 to 70 years"), extract the full range

EXAMPLE JSON OUTPUTS:
{examples_block}

Return JSON array format:
{return_format_block}

DOCUMENT TEXT:
{document_text[:8000]}

JSON RESPONSE:
"""
        return focused_prompt
    
    def _show_coverage_summary(self, all_facts: List[ExtractedFact]) -> None:
        """Show coverage summary by section."""
        
        print(f"\n[SUMMARY] SMART EXTRACTION SUMMARY:")
        print(f"   Total facts found: {len(all_facts)}")
        
        # Group facts by section
        found_by_section = {}
        for fact in all_facts:
            # Extract section from fact key (e.g., "fees_and_charges.processing_fee" -> "fees_and_charges")
            if '.' in fact.key:
                section = fact.key.split('.')[0]
            else:
                # Fallback to using the section attribute if available, or "other"
                section = getattr(fact, 'section', 'other')
            
            if section not in found_by_section:
                found_by_section[section] = []
            found_by_section[section].append(fact)
        
        # Show 8 priority sections
        priority_sections = [
            "fees_and_charges", "prepayment_and_foreclosure", "loan_amount_and_ltv", 
            "eligibility", "repayment", "interest_rates", "documents", "grievance"
        ]
        
        priority_facts_count = 0
        for section in priority_sections:
            section_facts = found_by_section.get(section, [])
            priority_facts_count += len(section_facts)
            
            if section_facts:
                print(f"   [OK] {section.replace('_', ' ').title()}: {len(section_facts)} facts")
                for fact in section_facts[:2]:  # Show top 2
                    # Extract field name from key (e.g., "fees_and_charges.processing_fee" -> "processing_fee")
                    field_name = fact.key.split('.')[-1] if '.' in fact.key else fact.key
                    short_value = fact.value[:45] + "..." if len(fact.value) > 45 else fact.value
                    print(f"      - {field_name}: {short_value}")
            else:
                print(f"   [NONE] {section.replace('_', ' ').title()}: 0 facts")
        
        # Show other sections
        other_sections = {k: v for k, v in found_by_section.items() if k not in priority_sections}
        if other_sections:
            print(f"   Other sections: {sum(len(facts) for facts in other_sections.values())} facts")
            for section, facts in other_sections.items():
                print(f"     - {section}: {len(facts)} facts")
        
        print(f"   Priority coverage: {priority_facts_count}/{len(all_facts)} facts in target sections")


