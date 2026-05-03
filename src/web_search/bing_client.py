"""Bing Web Search API client for company background research."""
import json
import logging
from typing import Dict, List, Optional

import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)


class BingSearchClient:
    """Client for Bing Web Search API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Bing search client."""
        self.api_key = api_key or settings.bing_api_key
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"
        self.headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "User-Agent": "InsuranceAgent/1.0"
        }

    def search_company_info(self, company_name: str, location: Optional[str] = None,
                          max_results: int = 5) -> Dict:
        """Search for company background information."""
        if not self.api_key:
            logger.warning("Bing API key not configured, returning empty results")
            return {"results": [], "summary": "No API key configured"}

        # Build search query
        query = f'"{company_name}" company background business information'
        if location:
            query += f" {location}"

        params = {
            "q": query,
            "count": max_results,
            "responseFilter": "Webpages",
            "setLang": "en-US"
        }

        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Extract relevant results
            results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"][:max_results]:
                    results.append({
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "display_url": item.get("displayUrl", "")
                    })

            # Generate a summary of findings
            summary = self._generate_company_summary(results, company_name)

            return {
                "results": results,
                "summary": summary,
                "query": query,
                "total_results": len(results)
            }

        except requests.RequestException as e:
            logger.error(f"Bing search failed: {e}")
            return {"results": [], "summary": f"Search failed: {str(e)}", "error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bing response: {e}")
            return {"results": [], "summary": f"Response parsing failed: {str(e)}", "error": str(e)}

    def _generate_company_summary(self, results: List[Dict], company_name: str) -> str:
        """Generate a summary of company information from search results."""
        if not results:
            return f"No information found for {company_name}"

        # Extract key insights from snippets
        insights = []
        negative_indicators = []
        positive_indicators = []

        for result in results:
            snippet = result.get("snippet", "").lower()

            # Look for business indicators
            if any(term in snippet for term in ["incorporated", "founded", "established", "since"]):
                insights.append("Company has established history")

            if any(term in snippet for term in ["bankruptcy", "lawsuit", "investigation", "fined"]):
                negative_indicators.append("Legal or financial issues detected")

            if any(term in snippet for term in ["award", "recognition", "certified", "accredited"]):
                positive_indicators.append("Positive business recognition found")

            if any(term in snippet for term in ["years in business", "established", "since"]):
                insights.append("Established business presence")

        # Combine insights
        summary_parts = []

        if positive_indicators:
            summary_parts.append(f"Positive indicators: {', '.join(positive_indicators)}")

        if negative_indicators:
            summary_parts.append(f"Risk indicators: {', '.join(negative_indicators)}")

        if insights:
            summary_parts.append(f"Business profile: {', '.join(set(insights))}")

        if not summary_parts:
            summary_parts.append("Limited public information available")

        return f"Company research for {company_name}: {'; '.join(summary_parts)}"

    def search_risk_indicators(self, company_name: str, location: Optional[str] = None) -> Dict:
        """Search specifically for risk indicators."""
        risk_query = f'"{company_name}" safety violations accidents insurance claims'
        if location:
            risk_query += f" {location}"

        params = {
            "q": risk_query,
            "count": 10,
            "responseFilter": "Webpages",
            "setLang": "en-US"
        }

        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Analyze results for risk indicators
            risk_score = 0
            risk_factors = []

            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    snippet = item.get("snippet", "").lower()

                    # Check for various risk indicators
                    if any(term in snippet for term in ["accident", "collision", "crash"]):
                        risk_score += 1
                        risk_factors.append("Vehicle accident history")

                    if any(term in snippet for term in ["violation", "citation", "ticket"]):
                        risk_score += 0.5
                        risk_factors.append("Safety violations")

                    if any(term in snippet for term in ["lawsuit", "litigation", "claim"]):
                        risk_score += 1
                        risk_factors.append("Legal claims")

                    if any(term in snippet for term in ["bankruptcy", "insolvent", "liquidation"]):
                        risk_score += 2
                        risk_factors.append("Financial distress")

            # Normalize risk score (0-10 scale)
            normalized_score = min(risk_score * 2, 10)

            risk_level = "Low" if normalized_score < 3 else "Medium" if normalized_score < 7 else "High"

            return {
                "company_name": company_name,
                "risk_score": normalized_score,
                "risk_level": risk_level,
                "risk_factors": list(set(risk_factors)),  # Remove duplicates
                "search_query": risk_query
            }

        except Exception as e:
            logger.error(f"Risk indicator search failed: {e}")
            return {
                "company_name": company_name,
                "risk_score": 5.0,  # Default medium risk
                "risk_level": "Unknown",
                "risk_factors": ["Search failed"],
                "error": str(e)
            }