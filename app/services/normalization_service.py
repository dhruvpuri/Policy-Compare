"""Service for normalizing and standardizing extracted facts."""

import re
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation

from app.models.document import ExtractedFact


class NormalizationService:
    """Service for normalizing extracted facts and values."""
    
    # Enhanced currency patterns and conversions (Assignment requirement: ₹/Rs, L/Lac, Cr)
    CURRENCY_PATTERNS = [
        r'₹\s*([0-9,]+(?:\.[0-9]{2})?)',  # ₹1,000 or ₹1,000.50
        r'Rs\.?\s*([0-9,]+(?:\.[0-9]{2})?)',  # Rs. 1,000 or Rs 1000.50
        r'INR\s*([0-9,]+(?:\.[0-9]{2})?)',  # INR 1,000
        r'[`]\s*([0-9,]+(?:\.[0-9]{2})?)',  # Backtick currency marker seen in some PDFs
        r'([0-9,]+(?:\.[0-9]*)?)\s*L(?:akh?s?|ac?s?)',  # 5L, 5 Lakhs, 5Lac, 5Lacs
        r'([0-9,]+(?:\.[0-9]*)?)\s*Cr(?:ore?s?)',  # 2Cr, 2 Crores
        r'([0-9,]+(?:\.[0-9]*)?)\s*(?:Thousand|K)',  # 500K, 500 Thousand
    ]
    
    # Term synonyms mapping for HOME LOANS
    TERM_SYNONYMS = {
        'cibil': ['credit_score', 'cibil_score', 'credit_rating', 'bureau_score'],
        'credit_score': ['cibil', 'cibil_score', 'credit_rating', 'bureau_score'],
        'processing_fee': ['admin_fee', 'administrative_charges', 'handling_charges'],
        # Bank-specific synonyms
        'processing_fee': ['login_fee', 'login_charges', 'login_fee_processing_fee'] + ['admin_fee', 'administrative_charges', 'handling_charges'],
        'prepayment': ['foreclosure', 'pre_closure', 'early_repayment', 'premature_closure'],
        'foreclosure': ['prepayment', 'pre_closure', 'early_repayment', 'premature_closure'],
        'ltv': ['loan_to_value', 'ltv_ratio', 'financing_ratio'],
        'tenure': ['term', 'loan_term', 'repayment_period', 'loan_period'],
        'term': ['tenure', 'loan_term', 'repayment_period', 'loan_period'],
        'emi': ['equated_monthly_installment', 'monthly_installment', 'installment'],
        'interest_rate': ['roi', 'rate_of_interest', 'lending_rate', 'home_loan_rate'],
        'property_value': ['property_cost', 'property_worth', 'asset_value'],
        'income_proof': ['salary_certificate', 'income_certificate', 'pay_slip'],
        'reset': ['revision', 'rate_change', 'adjustment'],
        'grievance': ['complaint', 'dispute', 'issue_resolution'],
    }
    
    # Percentage patterns
    PERCENTAGE_PATTERNS = [
        r'([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:per\s+annum|p\.a\.?|annually)?',
        r'([0-9]+(?:\.[0-9]+)?)\s*percent',
        r'([0-9]+(?:\.[0-9]+)?)\s*pc',
    ]

    BAD_VALUE_PATTERNS = [
        r"^\s*$",                             # empty / whitespace
        r"^[,.;]+$",                          # only punctuation
        r"^(template field.*|value not specified.*)$",  # template placeholders
        r"^_{3,}$",                           # ___ or ____
        r"^\[.*\]$",                         # [   ]
        r"^not\s*found$",                     # explicit not found
        r"^n\.a\.$",                          # N.A.
        r"^as applicable$",                   # As applicable
        r"^as per actuals$",                  # As per actuals
        r"^not specified$",                   # Not specified
        r"^to be filled$",                    # To be filled
        r"^_____+$"                           # Multiple underscores
    ]
    
    def __init__(self):
        """Initialize the normalization service."""
        self._compiled_currency_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.CURRENCY_PATTERNS]
        self._compiled_percentage_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.PERCENTAGE_PATTERNS]
        self._compiled_bad_value_patterns = [re.compile(pat, re.IGNORECASE) for pat in self.BAD_VALUE_PATTERNS]
    
    def normalize_facts(self, facts: List[ExtractedFact]) -> List[ExtractedFact]:
        """Normalize a list of extracted facts and drop obviously bad ones."""
        normalized_facts = []
        for fact in facts:
            normalized = self.normalize_single_fact(fact)
            if normalized and not self._looks_bad(normalized.value):
                normalized_facts.append(normalized)
        return normalized_facts
    
    def normalize_single_fact(self, fact: ExtractedFact) -> ExtractedFact:
        """Normalize a single fact.
        
        Args:
            fact: The fact to normalize
            
        Returns:
            Normalized fact
        """
        # Create a copy to avoid modifying the original
        normalized_fact = ExtractedFact(
            key=self._normalize_key(fact.key),
            value=self._normalize_value(fact.value, fact.key),
            confidence=fact.confidence,
            source_page=fact.source_page,
            source_text=fact.source_text,
            coordinates=fact.coordinates
        )
        
        return normalized_fact
    
    def _normalize_key(self, key: str) -> str:
        """Normalize fact keys using synonym mapping.
        
        Args:
            key: Original key
            
        Returns:
            Normalized key
        """
        # PRESERVE section.field format - don't normalize dots that separate sections from fields
        if '.' in key:
            section, field = key.split('.', 1)
            
            # Normalize each part separately
            normalized_section = re.sub(r'[^a-z0-9_]', '_', section.lower())
            normalized_section = re.sub(r'_+', '_', normalized_section).strip('_')
            
            normalized_field = re.sub(r'[^a-z0-9_]', '_', field.lower()) 
            normalized_field = re.sub(r'_+', '_', normalized_field).strip('_')
            
            # Apply synonym mapping to field only
            for canonical_term, synonyms in self.TERM_SYNONYMS.items():
                if any(synonym in normalized_field for synonym in synonyms):
                    for synonym in synonyms:
                        if synonym in normalized_field:
                            normalized_field = normalized_field.replace(synonym, canonical_term)
                            break
            
            return f"{normalized_section}.{normalized_field}"
        else:
            # Single term without section - normalize normally
            normalized = re.sub(r'[^a-z0-9_]', '_', key.lower())
            normalized = re.sub(r'_+', '_', normalized).strip('_')
            
            # Apply synonym mapping
            for canonical_term, synonyms in self.TERM_SYNONYMS.items():
                if any(synonym in normalized for synonym in synonyms):
                    for synonym in synonyms:
                        if synonym in normalized:
                            normalized = normalized.replace(synonym, canonical_term)
                            break
            
            return normalized
    
    def _normalize_value(self, value: str, key: str) -> str:
        """Normalize fact values based on type detection."""
        if not value or not isinstance(value, str):
            return str(value) if value is not None else ""

        value = value.strip()

        # Special handling for EMI currency indicator fields
        if 'emi_currency' in key.lower():
            lower_val = value.lower()
            if '₹' in value or '`' in value or 'rs' in lower_val or 'inr' in lower_val:
                return '₹'
            return value

        # Normalize phrases like "1.50% or ₹4,500 whichever is higher/lower"
        m_whichever = re.match(r"(?P<pct>[0-9]+(?:\.[0-9]+)?)%\s*or\s*(?:₹|rs\.?|inr)\s*(?P<amt>[0-9,]+)\s*whichever is\s*(?P<which>higher|lower)", value, re.IGNORECASE)
        if m_whichever:
            pct = m_whichever.group('pct')
            amt = m_whichever.group('amt')
            which = m_whichever.group('which').lower()
            comparator = 'min' if which == 'higher' else 'max'
            return f"{pct}% or ₹{amt} (use {comparator})"

        # Handle compound pct OR amount ("1.50% or ₹4,500")
        m = re.match(r"(?P<pct>[0-9]+(?:\.[0-9]+)?)%\s*or\s*(?:₹|rs\.?|inr)\s*(?P<amt>[0-9,]+)", value, re.IGNORECASE)
        if m:
            pct = m.group('pct')
            amt = m.group('amt')
            return f"{pct}% (min ₹{amt})"

        # EMI amount: ensure currency and filter out tiny numeric placeholders
        if key.lower().endswith('repayment.emi_amount') or 'emi_amount' in key.lower():
            # Force ₹ symbol if currency markers present in text
            if any(tok in value.lower() for tok in ['rs', 'inr', '₹', '`']):
                value = self._normalize_currency(value)
            # Filter implausibly small EMI values like '5'
            try:
                numbers = re.findall(r"\d+(?:\.\d+)?", value.replace(',', ''))
                if numbers:
                    num = float(numbers[0])
                    if num > 0 and num < 100:  # heuristic: EMI should not be < 100
                        return ''  # drop
            except Exception:
                pass

        # Normalize currency values
        if self._is_currency_field(key) or self._contains_currency(value):
            return self._normalize_currency(value)

        # Normalize percentage ranges ("1% to 3%")
        rng = re.match(r"(\d+(?:\.\d+)?)%\s*(?:to|-|–)\s*(\d+(?:\.\d+)?)%", value)
        if rng:
            return f"{rng.group(1)}%-{rng.group(2)}%"

        # Normalize percentage values
        if self._is_percentage_field(key) or self._contains_percentage(value):
            return self._normalize_percentage(value)

        # Normalize numerical values
        if self._is_numerical_field(key):
            return self._normalize_number(value)

        # Default text clean
        return self._normalize_text(value)
    
    def _is_currency_field(self, key: str) -> bool:
        """Check if a field typically contains currency values."""
        currency_keywords = ['fee', 'charge', 'amount', 'limit', 'income', 'salary', 'cost']
        return any(keyword in key.lower() for keyword in currency_keywords)
    
    def _is_percentage_field(self, key: str) -> bool:
        """Check if a field typically contains percentage values."""
        percentage_keywords = ['rate', 'apr', 'interest', 'roi', 'ltv', 'percent', 'penalty', 'spread']
        return any(keyword in key.lower() for keyword in percentage_keywords)
    
    def _is_numerical_field(self, key: str) -> bool:
        """Check if a field typically contains numerical values."""
        numerical_keywords = ['days', 'months', 'years', 'score', 'limit', 'period', 'tenure', 'term', 'age', 'experience']
        return any(keyword in key.lower() for keyword in numerical_keywords)
    
    def _contains_currency(self, value: str) -> bool:
        """Check if value contains currency indicators."""
        return any(pattern.search(value) for pattern in self._compiled_currency_patterns)
    
    def _contains_percentage(self, value: str) -> bool:
        """Check if value contains percentage indicators."""
        return any(pattern.search(value) for pattern in self._compiled_percentage_patterns)
    
    def _normalize_currency(self, value: str) -> str:
        """Normalize currency values to standard format (Assignment req: ₹/Rs, L/Lac, Cr).
        
        Args:
            value: Currency value string
            
        Returns:
            Normalized currency string
        """
        # Try each currency pattern
        for pattern in self._compiled_currency_patterns:
            match = pattern.search(value)
            if match:
                amount_str = match.group(1)
                value_upper = value.upper()
                
                # Handle special cases - Assignment requirement conversions
                if any(term in value_upper for term in ['L', 'LAKH', 'LAC']):
                    # Convert lakhs/lacs to actual number: 5L = 500,000
                    try:
                        amount = float(amount_str.replace(',', ''))
                        amount *= 100000  # 1 lakh = 100,000
                        return f"INR {amount:,.0f}"
                    except ValueError:
                        pass
                
                elif any(term in value_upper for term in ['CR', 'CRORE']):
                    # Convert crores to actual number: 2Cr = 20,000,000
                    try:
                        amount = float(amount_str.replace(',', ''))
                        amount *= 10000000  # 1 crore = 10,000,000
                        return f"INR {amount:,.0f}"
                    except ValueError:
                        pass
                
                elif any(term in value_upper for term in ['K', 'THOUSAND']):
                    # Convert thousands: 500K = 500,000
                    try:
                        amount = float(amount_str.replace(',', ''))
                        amount *= 1000  # 1K = 1,000
                        return f"INR {amount:,.0f}"
                    except ValueError:
                        pass
                
                else:
                    # Standard currency normalization (₹, Rs, INR)
                    try:
                        amount = float(amount_str.replace(',', ''))
                        return f"INR {amount:,.0f}"
                    except ValueError:
                        pass
        
        # If no pattern matched, return original value
        return value
    
    def _normalize_percentage(self, value: str) -> str:
        """Normalize percentage values.
        
        Args:
            value: Percentage value string
            
        Returns:
            Normalized percentage string
        """
        for pattern in self._compiled_percentage_patterns:
            match = pattern.search(value)
            if match:
                try:
                    percentage = float(match.group(1))
                    return f"{percentage}%"
                except ValueError:
                    pass
        
        return value
    
    def _normalize_number(self, value: str) -> str:
        """Normalize numerical values.
        
        Args:
            value: Number string
            
        Returns:
            Normalized number string
        """
        # Extract numbers from the string
        numbers = re.findall(r'\d+(?:\.\d+)?', value)
        if numbers:
            try:
                # Take the first number found
                num = float(numbers[0])
                if num.is_integer():
                    return str(int(num))
                else:
                    return f"{num:.2f}"
            except ValueError:
                pass
        
        return value
    
    def _normalize_text(self, value: str) -> str:
        """Normalize text values.
        
        Args:
            value: Text value
            
        Returns:
            Normalized text
        """
        # Clean up whitespace
        normalized = re.sub(r'\s+', ' ', value).strip()
        
        # Capitalize first letter of sentences
        sentences = normalized.split('. ')
        normalized = '. '.join(sentence.capitalize() for sentence in sentences if sentence)
        
        return normalized
    
    def detect_conflicts(self, facts: List[ExtractedFact]) -> List[Dict[str, Any]]:
        """Detect conflicts and contradictions in extracted facts.
        
        Args:
            facts: List of facts to check for conflicts
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Group facts by normalized key
        fact_groups = {}
        for fact in facts:
            key = fact.key
            if key not in fact_groups:
                fact_groups[key] = []
            fact_groups[key].append(fact)
        
        # Check for conflicts within each group
        for key, group_facts in fact_groups.items():
            if len(group_facts) > 1:
                group_conflicts = self._detect_group_conflicts(key, group_facts)
                conflicts.extend(group_conflicts)
        
        # Check for range overlaps (e.g., interest rates)
        range_conflicts = self._detect_range_conflicts(facts)
        conflicts.extend(range_conflicts)
        
        return conflicts
    
    def _detect_group_conflicts(self, key: str, facts: List[ExtractedFact]) -> List[Dict[str, Any]]:
        """Detect conflicts within a group of facts with the same key."""
        conflicts = []
        
        # Compare all pairs of facts
        for i, fact1 in enumerate(facts):
            for fact2 in facts[i+1:]:
                if self._values_conflict(fact1.value, fact2.value):
                    conflicts.append({
                        'type': 'value_contradiction',
                        'key': key,
                        'conflicting_values': [fact1.value, fact2.value],
                        'sources': [fact1.source_text, fact2.source_text],
                        'confidence_scores': [fact1.confidence, fact2.confidence],
                        'severity': 'high' if abs(fact1.confidence - fact2.confidence) < 0.2 else 'medium'
                    })
        
        return conflicts
    
    def _detect_range_conflicts(self, facts: List[ExtractedFact]) -> List[Dict[str, Any]]:
        """Detect overlapping or contradictory ranges (Assignment req: LTV thresholds, etc.)."""
        conflicts = []
        
        # Group range-related facts
        range_facts = {}
        range_keywords = ['ltv', 'interest_rate', 'processing_fee', 'age', 'income', 'tenure']
        
        for fact in facts:
            for keyword in range_keywords:
                if keyword in fact.key.lower():
                    if keyword not in range_facts:
                        range_facts[keyword] = []
                    range_facts[keyword].append(fact)
        
        # Check for overlapping/contradictory ranges
        for category, category_facts in range_facts.items():
            if len(category_facts) > 1:
                ranges = self._extract_ranges(category_facts)
                
                # Detect overlapping ranges
                for i, range1 in enumerate(ranges):
                    for range2 in ranges[i+1:]:
                        if self._ranges_overlap_contradictory(range1, range2):
                            conflicts.append({
                                'type': 'overlapping_ranges',
                                'category': category,
                                'conflicting_ranges': [range1, range2],
                                'severity': 'high',
                                'recommendation': 'Mark as SUSPECT - contradictory range information'
                            })
        
        return conflicts
    
    def _extract_ranges(self, facts: List[ExtractedFact]) -> List[Dict]:
        """Extract numeric ranges from fact values."""
        ranges = []
        
        for fact in facts:
            value = fact.value
            
            # Look for range patterns: "10% - 15%", "up to 80%", "minimum 2L", etc.
            range_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:%|L|Cr|K)?\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:%|L|Cr|K)?',  # 10-15%, 2L–5Cr
                r'up\s+to\s+(\d+(?:\.\d+)?)\s*(?:%|L|Cr|K)?',  # up to 80%
                r'minimum\s+(\d+(?:\.\d+)?)\s*(?:%|L|Cr|K)?',  # minimum 2L
                r'maximum\s+(\d+(?:\.\d+)?)\s*(?:%|L|Cr|K)?',  # maximum 5Cr
            ]
            
            for pattern in range_patterns:
                match = re.search(pattern, value, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:  # Range with two values
                        ranges.append({
                            'fact': fact,
                            'min': float(match.group(1)),
                            'max': float(match.group(2)),
                            'type': 'range'
                        })
                    elif 'up to' in value.lower():
                        ranges.append({
                            'fact': fact,
                            'min': 0,
                            'max': float(match.group(1)),
                            'type': 'upper_bound'
                        })
                    elif 'minimum' in value.lower():
                        ranges.append({
                            'fact': fact,
                            'min': float(match.group(1)),
                            'max': float('inf'),
                            'type': 'lower_bound'
                        })
                    elif 'maximum' in value.lower():
                        ranges.append({
                            'fact': fact,
                            'min': 0,
                            'max': float(match.group(1)),
                            'type': 'upper_bound'
                        })
                    break
        
        return ranges
    
    def _ranges_overlap_contradictory(self, range1: Dict, range2: Dict) -> bool:
        """Check if two ranges are contradictory/overlapping in a problematic way."""
        
        # If both are point values and different, that's a conflict
        if range1['min'] == range1['max'] and range2['min'] == range2['max']:
            return range1['min'] != range2['min']
        
        # Check for contradictory bounds
        if (range1['type'] == 'upper_bound' and range2['type'] == 'lower_bound' and 
            range1['max'] < range2['min']):
            return True  # max 5% but min 10% - contradiction
        
        if (range1['type'] == 'lower_bound' and range2['type'] == 'upper_bound' and 
            range1['min'] > range2['max']):
            return True  # min 10% but max 5% - contradiction
            
        # Check for suspicious overlaps in ranges
        if (range1['type'] == 'range' and range2['type'] == 'range'):
            # Calculate overlap percentage
            overlap_start = max(range1['min'], range2['min'])
            overlap_end = min(range1['max'], range2['max'])
            
            if overlap_start <= overlap_end:
                overlap_size = overlap_end - overlap_start
                range1_size = range1['max'] - range1['min']
                range2_size = range2['max'] - range2['min']
                
                # If overlap is small compared to range sizes, might be suspicious
                avg_range_size = (range1_size + range2_size) / 2
                if overlap_size < 0.3 * avg_range_size:  # Less than 30% overlap
                    return True
        
        return False
    
    def _values_conflict(self, value1: str, value2: str) -> bool:
        """Check if two values are conflicting.
        
        Args:
            value1: First value
            value2: Second value
            
        Returns:
            True if values conflict
        """
        if value1 == value2:
            return False
        
        # Try to parse as numbers and check if significantly different
        try:
            num1 = float(re.sub(r'[^\d.-]', '', value1))
            num2 = float(re.sub(r'[^\d.-]', '', value2))
            
            # Consider values conflicting if they differ by more than 10%
            if max(num1, num2) > 0:
                diff_ratio = abs(num1 - num2) / max(num1, num2)
                return diff_ratio > 0.1
        except (ValueError, TypeError):
            # If not numeric, consider different strings as potential conflicts
            # But allow for minor variations (case, punctuation)
            normalized1 = re.sub(r'[^\w]', '', value1.lower())
            normalized2 = re.sub(r'[^\w]', '', value2.lower())
            return normalized1 != normalized2 and len(normalized1) > 0 and len(normalized2) > 0
        
        return False

    def _looks_bad(self, value: str) -> bool:
        """Return True if the value is empty / placeholder / garbage."""
        if value is None:
            return True
        test_val = str(value).strip()
        for pat in self._compiled_bad_value_patterns:
            if pat.match(test_val):
                return True
        return False
