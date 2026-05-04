"""SEC EDGAR API client for company financial data."""
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class SECClient:
    """Client for SEC EDGAR API to retrieve company financial data."""

    def __init__(self):
        """Initialize the SEC client."""
        self.base_url = "https://www.sec.gov/edgar/searchedgar"
        self.company_search_url = "https://www.sec.gov/edgar/searchedgar/ccompanies.htm"
        self.headers = {
            "User-Agent": "InsuranceAgent/1.0 (contact@example.com)"
        }

    def search_company_financials(self, company_name: str) -> Dict:
        """Search for company financial information from SEC filings."""
        try:
            # First, try to find the company's CIK (Central Index Key)
            cik = self._find_company_cik(company_name)

            if not cik:
                return {
                    "company_name": company_name,
                    "financial_data": {},
                    "summary": f"No SEC filings found for {company_name}",
                    "data_source": "SEC EDGAR",
                    "available": False
                }

            # Get recent filings
            filings = self._get_recent_filings(cik)

            # Extract financial data from 10-K/10-Q filings
            financial_data = self._extract_financial_data(filings)

            # Generate summary
            summary = self._generate_financial_summary(financial_data, company_name)

            return {
                "company_name": company_name,
                "cik": cik,
                "financial_data": financial_data,
                "summary": summary,
                "data_source": "SEC EDGAR",
                "available": bool(financial_data),
                "filings_count": len(filings)
            }

        except Exception as e:
            logger.error(f"SEC search failed for {company_name}: {e}")
            return {
                "company_name": company_name,
                "financial_data": {},
                "summary": f"SEC search failed: {str(e)}",
                "data_source": "SEC EDGAR",
                "available": False,
                "error": str(e)
            }

    def _find_company_cik(self, company_name: str) -> Optional[str]:
        """Find the CIK for a company name."""
        try:
            # Use SEC's company search
            search_url = f"https://www.sec.gov/edgar/searchedgar/companies.htm"
            params = {"company": company_name}

            response = requests.get(search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse the HTML response to find CIK
            # This is a simplified implementation - in production, you'd use proper HTML parsing
            content = response.text.lower()

            # Look for CIK patterns in the response
            import re
            cik_match = re.search(r'cik=(\d{10})', content)
            if cik_match:
                return cik_match.group(1)

            return None

        except Exception as e:
            logger.error(f"CIK lookup failed for {company_name}: {e}")
            return None

    def _get_recent_filings(self, cik: str) -> List[Dict]:
        """Get recent filings for a company."""
        try:
            # Get company filings
            filings_url = f"https://data.sec.gov/submissions/CIK{cik}.json"

            response = requests.get(filings_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            filings = []
            recent_filings = data.get("filings", {}).get("recent", {})

            if recent_filings:
                form_types = recent_filings.get("form", [])
                filing_dates = recent_filings.get("filingDate", [])
                primary_docs = recent_filings.get("primaryDocument", [])

                # Get last 5 filings
                for i in range(min(5, len(form_types))):
                    if form_types[i] in ["10-K", "10-Q", "8-K"]:
                        filings.append({
                            "form_type": form_types[i],
                            "filing_date": filing_dates[i],
                            "primary_document": primary_docs[i]
                        })

            return filings

        except Exception as e:
            logger.error(f"Failed to get filings for CIK {cik}: {e}")
            return []

    def _extract_financial_data(self, filings: List[Dict]) -> Dict:
        """Extract financial data from filings."""
        financial_data = {
            "revenue": None,
            "net_income": None,
            "total_assets": None,
            "total_liabilities": None,
            "latest_filing_date": None,
            "filing_types": []
        }

        for filing in filings:
            financial_data["filing_types"].append(filing["form_type"])

            if not financial_data["latest_filing_date"]:
                financial_data["latest_filing_date"] = filing["filing_date"]

        # In a real implementation, you'd parse the actual XBRL financial data
        # from the filings. This is a placeholder that would extract real data.

        return financial_data

    def _generate_financial_summary(self, financial_data: Dict, company_name: str) -> str:
        """Generate a summary of financial health."""
        if not financial_data.get("filing_types"):
            return f"No recent SEC filings found for {company_name}"

        filing_types = financial_data.get("filing_types", [])
        latest_date = financial_data.get("latest_filing_date")

        summary_parts = [f"SEC filings available for {company_name}"]

        if latest_date:
            summary_parts.append(f"Latest filing: {latest_date}")

        if "10-K" in filing_types:
            summary_parts.append("Annual report (10-K) available")
        if "10-Q" in filing_types:
            summary_parts.append("Quarterly reports (10-Q) available")

        return ". ".join(summary_parts)