from __future__ import annotations
import re
from typing import List, Dict, Optional

# Regex matches examples:
# "90% - Up to ₹30 Lakhs"  or  "Loan-to-Value Ratio: Up to 90% for loans up to ₹30 Lakhs"
LTV_ROW = re.compile(
    r"(?P<pct>[0-9]{1,3})\s*%\s*(?:-|–)?\s*(?:up\s*to\s*)?₹?\s*(?P<lower>[0-9,]+)?(?:\s*(?:-|–|to)\s*₹?\s*(?P<upper>[0-9,]+))?\s*(?P<unit>L|Lakh|Lac|Crore|Cr|K|Thousand)?",
    re.IGNORECASE,
)


def _to_int(num: Optional[str]) -> Optional[int]:
    if not num:
        return None
    return int(num.replace(",", ""))


def parse_ltv_table(text: str) -> List[Dict[str, Optional[int]]]:
    """Parse tiered LTV lines/tables and return structured band list.

    Each band dict contains:
        {
            "min_amount": <int|None>,  # lower rupee bound
            "max_amount": <int|None>,  # upper rupee bound
            "ltv": "90%"
        }
    """
    bands: List[Dict[str, Optional[int]]] = []
    for match in LTV_ROW.finditer(text):
        pct = f"{match.group('pct')}%"
        lower = _to_int(match.group('lower'))
        upper = _to_int(match.group('upper'))
        unit = (match.group('unit') or '').strip()
        bands.append({
            "min_amount": lower,
            "max_amount": upper,
            "unit": unit if unit else None,
            "ltv": pct
        })
    return bands

