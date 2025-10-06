"""LLM service for document analysis and fact extraction using Google Gemini."""

import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import time
from pathlib import Path
import hashlib

import google.generativeai as genai
from pydantic import BaseModel

from app.models.document import ExtractedFact


class MITCSection(BaseModel):
    """Represents a MITC document section."""
    name: str
    description: str
    key_fields: List[str]


class LLMExtractionService:
    """Service for LLM-powered document analysis and fact extraction."""
    
    # Define the 7 key HOME LOAN MITC sections to extract
    MITC_SECTIONS = [
        MITCSection(
            name="LTV Bands",
            description="Loan-to-Value ratio bands and corresponding interest rates",
            key_fields=["ltv_ratio", "interest_rate", "ltv_bands", "property_value_bands", "loan_amount_limits"]
        ),
        MITCSection(
            name="Processing Fees and Charges", 
            description="Processing fees, administrative charges, and other costs",
            key_fields=["processing_fee", "admin_fee", "legal_charges", "valuation_charges", "insurance_charges"]
        ),
        MITCSection(
            name="Prepayment and Foreclosure",
            description="Prepayment penalties, foreclosure charges, and terms",
            key_fields=["prepayment_penalty", "foreclosure_charges", "partial_prepayment", "lock_in_period", "prepayment_conditions"]
        ),
        MITCSection(
            name="Eligibility Criteria",
            description="Income, employment, age, and other eligibility requirements",
            key_fields=["minimum_income", "employment_type", "age_limits", "cibil_score", "work_experience", "existing_obligations"]
        ),
        MITCSection(
            name="Tenure Options",
            description="Loan tenure ranges, repayment terms, and EMI structure",
            key_fields=["minimum_tenure", "maximum_tenure", "emi_frequency", "interest_calculation", "tenure_bands"]
        ),
        MITCSection(
            name="Interest Reset and Communication",
            description="Interest rate reset mechanisms and communication policies",
            key_fields=["reset_frequency", "benchmark_rate", "spread", "rate_change_notification", "reset_conditions"]
        ),
        MITCSection(
            name="Required Documents",
            description="Documentation requirements for loan processing",
            key_fields=["income_documents", "identity_proof", "address_proof", "property_documents", "employment_proof"]
        ),
        MITCSection(
            name="Grievance and Customer Service",
            description="Grievance redressal mechanisms and customer service policies",
            key_fields=["grievance_process", "escalation_matrix", "response_timeline", "nodal_officer", "ombudsman_details"]
        )
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM service.
        
        Args:
            api_key: Google Gemini API key. If None, will read from environment
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Try different model names in order of preference
        model_names = ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash-exp']
        self.model = None
        self.model_name = None
        
        for model_name in model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                self.model_name = model_name
                print(f"✅ Using Gemini model: {model_name}")
                break
            except Exception as e:
                print(f"⚠️  Model {model_name} not available: {e}")
                continue
        
        if not self.model:
            raise ValueError("No available Gemini model found. Please check your API key and model access.")

        # --- Rate limiting & caching set-up (to avoid 429s on free tier) ---
        # Requests-per-minute guard (default 2 for free tier)
        self.requests_per_minute = int(os.getenv("LLM_REQUESTS_PER_MINUTE", "2"))
        # Minimum interval between calls in seconds
        self._min_interval_s = max(60.0 / max(self.requests_per_minute, 1), 1.0)
        # Serialize LLM calls globally within this process
        self._call_lock: asyncio.Lock = asyncio.Lock()
        # Keep track of last call time
        self._last_call_ts: float = 0.0

        # Disk cache by document content hash
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def _enforce_rate_limit(self) -> None:
        """Ensure spacing between requests to respect RPM limits."""
        now = time.time()
        wait_s = self._min_interval_s - (now - self._last_call_ts)
        if wait_s > 0:
            await asyncio.sleep(wait_s)

    def _doc_hash(self, text: str) -> str:
        # Hash only the portion we send to keep stable cache keys
        data = (text or "")[:6000].encode("utf-8", errors="ignore")
        return hashlib.sha1(data).hexdigest()

    def _cache_path(self, text: str) -> Path:
        return self.cache_dir / f"facts_{self._doc_hash(text)}.json"

    def _save_facts_cache(self, text: str, facts: List[ExtractedFact]) -> None:
        try:
            serializable = [
                {
                    "key": f.key,
                    "value": f.value,
                    "confidence": f.confidence,
                    "source_text": f.source_text,
                    "source_reference": getattr(f, "source_reference", None),
                    "effective_date": getattr(f, "effective_date", None),
                }
                for f in facts
            ]
            self._cache_path(text).write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load_facts_cache(self, text: str) -> Optional[List[ExtractedFact]]:
        try:
            p = self._cache_path(text)
            if not p.exists():
                return None
            data = json.loads(p.read_text(encoding="utf-8"))
            facts: List[ExtractedFact] = []
            for item in data:
                facts.append(
                    ExtractedFact(
                        key=item.get("key", ""),
                        value=item.get("value", ""),
                        confidence=float(item.get("confidence", 0.0)),
                        source_text=item.get("source_text", ""),
                        source_page=None,
                        source_reference=item.get("source_reference", None),
                        effective_date=item.get("effective_date", None),
                    )
                )
            return facts
        except Exception:
            return None

    def _is_quota_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        return "quota" in msg or "rate limit" in msg or "429" in msg

    def _is_per_day_limit(self, err: Exception) -> bool:
        msg = str(err)
        return "PerDay" in msg or "PerDayPerProjectPerModel" in msg or "per day" in msg.lower()

    def _parse_retry_delay(self, err: Exception) -> float:
        # Try to extract suggested retry seconds from error text
        msg = str(err)
        m = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", msg)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                pass
        m2 = re.search(r"Please retry in ([0-9.]+)s", msg)
        if m2:
            try:
                return float(m2.group(1))
            except Exception:
                pass
        # Default small backoff
        return max(self._min_interval_s, 5.0)

    async def _generate_with_backoff(self, prompt: str) -> Any:
        """Call Gemini with RPM guard, exponential backoff, model fallback, and jitter."""
        # Serialize all calls through a single lock
        async with self._call_lock:
            await self._enforce_rate_limit()
            try:
                resp = self.model.generate_content(prompt)
                self._last_call_ts = time.time()
                return resp
            except Exception as e:
                self._last_call_ts = time.time()
                if not self._is_quota_error(e):
                    raise

                delay = self._parse_retry_delay(e)
                # If daily limit, attempt model fallback once
                if self._is_per_day_limit(e):
                    fallback_chain = [
                        m for m in ['gemini-2.5-flash', 'gemini-2.0-flash-exp'] if m != self.model_name
                    ]
                    for fb in fallback_chain:
                        try:
                            print(f"⚠️  Daily limit hit on {self.model_name}. Falling back to {fb}...")
                            self.model = genai.GenerativeModel(fb)
                            self.model_name = fb
                            await asyncio.sleep(delay)
                            resp = self.model.generate_content(prompt)
                            self._last_call_ts = time.time()
                            return resp
                        except Exception as e2:
                            if not self._is_quota_error(e2):
                                raise
                            delay = self._parse_retry_delay(e2)
                    # All fallbacks failed due to daily limit
                    raise

                # Per-minute limit: wait then single retry
                print(f"⏳ Rate limit hit. Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay + 0.5)
                resp = self.model.generate_content(prompt)
                self._last_call_ts = time.time()
                return resp
    
    async def extract_facts(self, document_text: str, document_id: str) -> List[ExtractedFact]:
        """Extract ALL structured facts in a single API call to avoid rate limits.
        
        Args:
            document_text: The cleaned document text
            document_id: Document identifier for tracking
            
        Returns:
            List of extracted facts with evidence mapping
        """
        print("🤖 Extracting all home loan facts in single comprehensive API call...")
        
        # Enhanced universal prompt with date detection and source tracking (Assignment requirements)
        prompt = f"""
FIRST: Look for EFFECTIVE DATE or UPDATED DATE in document (Assignment req: prefer doc dates over today):
- "Effective from", "Valid from", "Updated on", "Version dated", "Revised on"
- Extract and note any found dates

SECOND: Validate if this is a HOME LOAN document by checking for these indicators:
- "home loan", "housing loan", "mortgage", "property loan"
- "MITC", "most important terms", "loan agreement"
- "EMI", "interest rate", "tenure", "LTV"

IF NOT A LOAN DOCUMENT: Return {{"document_type": "non_loan", "message": "This does not appear to be a home loan document"}}

IF LOAN DOCUMENT: Extract facts from this BANK LOAN MITC document (works for HDFC/ICICI/SBI/DBS formats):

UNIVERSAL SECTIONS TO FIND:

1. LOAN AMOUNT & LTV: Sanctioned amount, principal amount, loan-to-value ratios, property value, maximum loan limits
2. INTEREST RATES: Fixed/floating rates, benchmark rates (RPLR/IHPLR/EBLR/REPO), margins, reset frequency (monthly/quarterly), rate change periods
3. REPAYMENT: EMI amount, tenure/term, installment type, repayment schedule, EMI calculation method
4. FEES & CHARGES: Processing fees (% ranges like 0.50% to 3.00%), admin charges, legal fees, valuation charges, login fees
5. PREPAYMENT: Foreclosure charges, partial prepayment options (like 25% of principal), lock-in period, penalties, prepayment conditions
6. ELIGIBILITY: Income criteria, CIBIL/credit score, age limits, employment type, experience requirements
7. DOCUMENTS: Income proof, identity, address, property papers required, KYC documents
8. PENAL CHARGES: Late payment penalties (% per annum), bounce charges, irregular payment fees, default interest
9. COMMUNICATION: Rate change notifications, customer service, grievance process, reset notification methods

BANK-SPECIFIC PATTERNS to look for:
- HDFC: "RPLR", "Interest chargeable: X% p.a.", "Sanctioned Amount", "prepay up to 25% of the opening principal amount", numbered sections
- ICICI: "IHPLR", "Facility Agreement", "Reset Period: Monthly", "0.50% to 3.00%", "principal amount of the Facility", checkbox format, "Adjustable Rate"
- SBI: "EBLR linked RBI REPO rate", "Penal CHARGES", LTV tables
- DBS: "Smart Home", "Smart LAP", "tariff section", "Late Payment Charge (LPC)"
- General: "EMI: ₹X", "Processing Fee: Y%", "Tenure: Z years", "Login Fee/Processing Fee"

SPECIFIC PATTERNS TO EXTRACT (from audit findings):
- Loan amounts: "Sanctioned Amount", "principal amount", "loan amount"  
- Processing fees: "0.50% to 3.00%", "Login Fee/Processing Fee"
- Reset frequency: "Reset Period: Monthly", "Monthly", "rate change"
- Prepayment: "prepay up to 25%", "partial prepayment", "foreclosure"

Return JSON array with enhanced source tracking (Assignment req: Evidence matters):
[{{"section": "Interest Rates", "field": "benchmark_rate", "value": "RPLR + 0.5%", "source_text": "exact quote from document", "confidence": 0.9, "source_reference": "filename + approximate location", "effective_date": "document effective date if found"}}]

DOCUMENT TEXT: {document_text[:6000]}

JSON RESPONSE:"""
        
        try:
            # Cache check (avoid re-calling for same document content)
            cached = self._load_facts_cache(document_text)
            if cached is not None:
                print(f"🗄️  Using cached facts: {len(cached)}")
                return cached

            # Guarded LLM call with backoff
            response = await self._generate_with_backoff(prompt)
            
            if not response.text:
                print("⚠️  No response from LLM")
                return []
            
            # Parse the comprehensive response
            facts = self._parse_comprehensive_response(response.text, document_id)
            # Save to cache
            self._save_facts_cache(document_text, facts)
            print(f"✅ Extracted {len(facts)} facts in single API call")
            return facts
            
        except Exception as e:
            print(f"❌ Error in comprehensive extraction: {str(e)}")
            
            # Fallback: try priority sections only if comprehensive fails
            # Fallback: try priority sections only if comprehensive fails (also guarded)
            return await self._extract_priority_sections_only(document_text, document_id)
    
    async def _extract_section_facts(self, document_text: str, section: MITCSection, document_id: str) -> List[ExtractedFact]:
        """Extract facts for a specific section.
        
        Args:
            document_text: The document text
            section: The section to extract
            document_id: Document identifier
            
        Returns:
            List of extracted facts for this section
        """
        prompt = self._build_extraction_prompt(section, document_text)
        
        try:
            response = await self._generate_with_backoff(prompt)
            
            if not response.text:
                return []
            
            # Parse the structured response
            facts = self._parse_extraction_response(response.text, section.name, document_id)
            return facts
            
        except Exception as e:
            print(f"Error extracting facts for section {section.name}: {str(e)}")
            return []
    
    def _build_extraction_prompt(self, section: MITCSection, document_text: str) -> str:
        """Build a structured prompt for fact extraction.
        
        Args:
            section: The section to extract
            document_text: The document text
            
        Returns:
            Formatted prompt for the LLM
        """
        key_fields_str = ", ".join(section.key_fields)
        
        prompt = f"""
You are analyzing a HOME LOAN MITC (Most Important Terms and Conditions) document from an Indian bank. 
Extract information for the "{section.name}" section.

SECTION DESCRIPTION: {section.description}
KEY FIELDS TO FIND: {key_fields_str}

CONTEXT: This is a home loan policy document. Look for terms related to housing finance, mortgage lending, property loans.

INSTRUCTIONS:
1. Find information related to {section.name.lower()} in the document
2. For each piece of information found:
   - Extract the specific value or text
   - Include the source text snippet (exact quote from document)
   - Assign a confidence score (0.0-1.0) based on how certain you are
3. Handle Indian financial notation: ₹, Rs, Lakhs (L), Crores (Cr), % per annum (p.a.)
4. Look for synonyms: foreclosure/pre-closure, tenure/term, CIBIL/credit score
5. Return results in JSON format as an array of objects
6. Use this exact structure:
   [
     {{
       "field": "field_name",
       "value": "extracted_value", 
       "source_text": "exact quote from document",
       "confidence": 0.9
     }}
   ]

DOCUMENT TEXT:
{document_text}

RESPONSE (JSON only):
"""
        return prompt
    
    def _parse_extraction_response(self, response_text: str, section_name: str, document_id: str) -> List[ExtractedFact]:
        """Parse the LLM response into ExtractedFact objects.
        
        Args:
            response_text: Raw LLM response
            section_name: Name of the section being processed
            document_id: Document identifier
            
        Returns:
            List of ExtractedFact objects
        """
        facts = []
        
        try:
            # Clean up the response text to extract JSON
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                return facts
            
            json_str = json_match.group(0)
            extracted_data = json.loads(json_str)
            
            for item in extracted_data:
                if not isinstance(item, dict):
                    continue
                
                fact = ExtractedFact(
                    key=f"{section_name.lower().replace(' ', '_')}.{item.get('field', 'unknown')}",
                    value=str(item.get('value', '')),
                    confidence=float(item.get('confidence', 0.0)),
                    source_text=item.get('source_text', ''),
                    # Note: page numbers would need PDF coordinate extraction
                    source_page=None
                )
                facts.append(fact)
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error parsing extraction response for {section_name}: {str(e)}")
            # Fallback: create a single fact with raw response
            if response_text.strip():
                fact = ExtractedFact(
                    key=f"{section_name.lower().replace(' ', '_')}.raw_response",
                    value=response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    confidence=0.5,
                    source_text=response_text[:200] + "..." if len(response_text) > 200 else response_text
                )
                facts.append(fact)
        
        return facts
    
    def _parse_comprehensive_response(self, response_text: str, document_id: str) -> List[ExtractedFact]:
        """Parse comprehensive response with all facts from all sections.
        
        Args:
            response_text: Raw LLM response with all facts
            document_id: Document identifier
            
        Returns:
            List of ExtractedFact objects
        """
        facts = []
        
        try:
            # First check for non-loan document detection
            non_loan_match = re.search(r'\{"document_type":\s*"non_loan"', response_text)
            if non_loan_match:
                print("🚫 Document identified as non-loan document")
                fact = ExtractedFact(
                    key="document_validation.document_type",
                    value="non_loan_document", 
                    confidence=0.9,
                    source_text="Document does not appear to be a home loan document",
                    source_page=None
                )
                facts.append(fact)
                return facts
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if not json_match:
                print("⚠️  No JSON array found in comprehensive response")
                return facts
            
            json_str = json_match.group(0)
            extracted_data = json.loads(json_str)
            
            for item in extracted_data:
                if not isinstance(item, dict):
                    continue
                
                # Get section and field names
                section = item.get('section', 'unknown').lower().replace(' ', '_').replace('&', '_and')
                field = item.get('field', 'unknown')
                
                # Clean section name to match our naming convention
                section_clean = section.replace('_and_charges', '_and_charges')
                section_clean = section_clean.replace('_and_ltv', '_and_ltv')
                section_clean = section_clean.replace('interest_rates', 'interest_rates')
                section_clean = section_clean.replace('penal_charges', 'penal_charges')
                
                fact = ExtractedFact(
                    key=f"{section_clean}.{field}",
                    value=str(item.get('value', '')),
                    confidence=float(item.get('confidence', 0.0)),
                    source_text=item.get('source_text', ''),
                    source_page=None,
                    source_reference=item.get('source_reference', ''),
                    effective_date=item.get('effective_date', None)
                )
                facts.append(fact)
                
            print(f"✅ Parsed {len(facts)} facts from comprehensive response")
            return facts
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"❌ Error parsing comprehensive response: {str(e)}")
            
            # Check if response indicates empty/corrupted document
            if len(response_text.strip()) < 50:
                print("⚠️  Very short response - possibly empty/corrupted document")
                fact = ExtractedFact(
                    key="document_validation.status",
                    value="empty_or_corrupted",
                    confidence=0.8,
                    source_text="Document appears to be empty or corrupted"
                )
                facts.append(fact)
            else:
                # Fallback: create facts from raw response if parsing fails
                fact = ExtractedFact(
                    key="comprehensive_extraction.raw_response",
                    value=response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    confidence=0.5,
                    source_text=response_text[:200] + "..." if len(response_text) > 200 else response_text
                )
                facts.append(fact)
        
        return facts
    
    async def _extract_priority_sections_only(self, document_text: str, document_id: str) -> List[ExtractedFact]:
        """Fallback: Extract only the 3 most important sections to stay within rate limits.
        
        Args:
            document_text: The document text
            document_id: Document identifier
            
        Returns:
            List of extracted facts from priority sections
        """
        print("⚠️  Using fallback: extracting priority sections only")
        
        # Most important sections for home loan comparison
        priority_sections = [
            self.MITC_SECTIONS[0],  # LTV Bands
            self.MITC_SECTIONS[1],  # Processing Fees and Charges  
            self.MITC_SECTIONS[2],  # Prepayment and Foreclosure
        ]
        
        all_facts = []
        
        for section in priority_sections:
            try:
                section_facts = await self._extract_section_facts(document_text, section, document_id)
                all_facts.extend(section_facts)
                print(f"✅ Priority section {section.name}: {len(section_facts)} facts")
            except Exception as e:
                print(f"❌ Error in priority section {section.name}: {str(e)}")
                
        print(f"✅ Total priority facts extracted: {len(all_facts)}")
        return all_facts
    
    async def analyze_document_structure(self, document_text: str) -> Dict[str, Any]:
        """Analyze the overall structure and content of the document.
        
        Args:
            document_text: The document text to analyze
            
        Returns:
            Analysis results including sections found, document type, etc.
        """
        prompt = f"""
Analyze this HOME LOAN bank document and identify:
1. Document type (MITC, Terms & Conditions, Policy Document, Home Loan Policy, etc.)
2. Bank name (if mentioned)
3. Product type (should be Home Loan, Housing Loan, Mortgage, Property Loan, etc.)
4. Main sections present (look for: LTV, Processing Fees, Prepayment, Eligibility, Tenure, etc.)
5. Document quality assessment (complete/incomplete, clear/unclear)
6. Effective date or last updated date (if mentioned)

Return results in JSON format:
{{
    "document_type": "type",
    "bank_name": "name",
    "product_type": "type", 
    "sections_found": ["section1", "section2"],
    "quality_score": 0.8,
    "quality_notes": "assessment notes",
    "effective_date": "date if found"
}}

DOCUMENT TEXT:
{document_text[:2000]}...

RESPONSE (JSON only):
"""
        
        try:
            response = await self._generate_with_backoff(prompt)
            if response.text:
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            
        except Exception as e:
            print(f"Error analyzing document structure: {str(e)}")
        
        # Fallback response
        return {
            "document_type": "Unknown",
            "bank_name": "Unknown",
            "product_type": "Unknown",
            "sections_found": [],
            "quality_score": 0.5,
            "quality_notes": "Could not analyze document structure"
        }
    
    async def extract_facts_with_prompt(self, document_text: str, custom_prompt: str, document_id: str) -> List[ExtractedFact]:
        """Extract facts using a custom prompt (for smart extraction)."""
        
        try:
            print(f"🤖 Using custom prompt for targeted extraction...")
            
            # Use the cached generation method with custom prompt (FIXED: only pass prompt)
            response = await self._generate_with_backoff(custom_prompt)
            
            if not response or not hasattr(response, 'text') or not response.text.strip():
                print("⚠️  Empty response from LLM")
                return []
            
            # Parse the response using existing logic
            facts = self._parse_comprehensive_response(response.text, document_id)
            return facts
            
        except Exception as e:
            print(f"❌ Custom prompt extraction failed: {e}")
            return []
