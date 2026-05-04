"""Dun & Bradstreet API client for company financial data."""
import logging
from typing import Dict, Optional

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DnBClient:
    """Client for Dun & Bradstreet API to retrieve proprietary company data."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the DnB client."""
        self.api_key = api_key or settings.dnb_api_key
        self.base_url = "https://direct.dnb.com/V6.0/organizations"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "InsuranceAgent/1.0"
        }

    def search_company_financials(self, company_name: str, location: Optional[str] = None) -> Dict:
        """Search for company financial information from DnB."""
        if not self.api_key:
            logger.warning("DnB API key not configured")
            return {
                "company_name": company_name,
                "financial_data": {},
                "summary": "DnB API key not configured",
                "data_source": "Dun & Bradstreet",
                "available": False
            }

        try:
            # Search for company by name
            search_params = {
                "OrganizationName": company_name,
                "CountryISOAlpha2Code": "US"
            }

            if location:
                search_params["AddressLocality"] = location

            response = requests.get(
                f"{self.base_url}/find",
                headers=self.headers,
                params=search_params,
                timeout=15
            )

            if response.status_code == 401:
                return {
                    "company_name": company_name,
                    "financial_data": {},
                    "summary": "DnB API authentication failed",
                    "data_source": "Dun & Bradstreet",
                    "available": False,
                    "error": "Authentication failed"
                }

            response.raise_for_status()
            data = response.json()

            # Extract company matches
            candidates = data.get("FindCandidate", [])

            if not candidates:
                return {
                    "company_name": company_name,
                    "financial_data": {},
                    "summary": f"No DnB records found for {company_name}",
                    "data_source": "Dun & Bradstreet",
                    "available": False
                }

            # Get detailed information for the best match
            best_match = candidates[0]
            duns_number = best_match.get("DUNSNumber")

            if duns_number:
                detailed_data = self._get_company_details(duns_number)
                financial_data = self._extract_financial_data(detailed_data)
                summary = self._generate_financial_summary(financial_data, company_name)

                return {
                    "company_name": company_name,
                    "duns_number": duns_number,
                    "financial_data": financial_data,
                    "summary": summary,
                    "data_source": "Dun & Bradstreet",
                    "available": bool(financial_data),
                    "confidence": best_match.get("MatchQualityInformation", {}).get("ConfidenceCodeValue")
                }
            else:
                return {
                    "company_name": company_name,
                    "financial_data": {},
                    "summary": f"DnB match found but no DUNS number for {company_name}",
                    "data_source": "Dun & Bradstreet",
                    "available": False
                }

        except requests.RequestException as e:
            logger.error(f"DnB search failed for {company_name}: {e}")
            return {
                "company_name": company_name,
                "financial_data": {},
                "summary": f"DnB search failed: {str(e)}",
                "data_source": "Dun & Bradstreet",
                "available": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"DnB processing failed for {company_name}: {e}")
            return {
                "company_name": company_name,
                "financial_data": {},
                "summary": f"DnB processing failed: {str(e)}",
                "data_source": "Dun & Bradstreet",
                "available": False,
                "error": str(e)
            }

    def _get_company_details(self, duns_number: str) -> Dict:
        """Get detailed company information by DUNS number."""
        try:
            response = requests.get(
                f"{self.base_url}/{duns_number}",
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get DnB details for DUNS {duns_number}: {e}")
            return {}

    def _extract_financial_data(self, data: Dict) -> Dict:
        """Extract financial data from DnB response."""
        financial_data = {
            "revenue": None,
            "employee_count": None,
            "net_worth": None,
            "credit_score": None,
            "risk_indicators": [],
            "last_update": None
        }

        try:
            organization = data.get("organization", {})

            # Extract financial information
            financial = organization.get("financial", {})

            if "yearlyRevenue" in financial:
                for revenue in financial["yearlyRevenue"]:
                    if revenue.get("currency") == "USD":
                        financial_data["revenue"] = revenue.get("value")
                        break

            # Extract employee information
            employees = organization.get("numberOfEmployees", [])
            if employees:
                # Get most recent employee count
                latest_employees = max(employees, key=lambda x: x.get("informationScopeDescription", ""))
                financial_data["employee_count"] = latest_employees.get("value")

            # Extract DnB credit score if available
            assessment = organization.get("assessment", {})
            if "dnbAssessment" in assessment:
                financial_data["credit_score"] = assessment["dnbAssessment"].get("dnbRating")

            # Extract risk indicators
            risk_indicators = []
            if assessment.get("legalEvents"):
                risk_indicators.append("Legal events recorded")

            if organization.get("mostSeniorPrincipal", {}).get("currentPrincipal"):
                # Check for management changes or other indicators
                pass

            financial_data["risk_indicators"] = risk_indicators

        except Exception as e:
            logger.error(f"Failed to extract financial data from DnB response: {e}")

        return financial_data

    def _generate_financial_summary(self, financial_data: Dict, company_name: str) -> str:
        """Generate a summary of financial health from DnB data."""
        summary_parts = [f"Dun & Bradstreet data for {company_name}"]

        if financial_data.get("revenue"):
            summary_parts.append(f"Annual revenue: ${financial_data['revenue']:,.0f}")

        if financial_data.get("employee_count"):
            summary_parts.append(f"Employees: {financial_data['employee_count']}")

        if financial_data.get("credit_score"):
            summary_parts.append(f"DnB credit score: {financial_data['credit_score']}")

        risk_indicators = financial_data.get("risk_indicators", [])
        if risk_indicators:
            summary_parts.append(f"Risk indicators: {', '.join(risk_indicators)}")

        if len(summary_parts) == 1:
            return f"DnB record exists for {company_name} but limited financial data available"

        return ". ".join(summary_parts)