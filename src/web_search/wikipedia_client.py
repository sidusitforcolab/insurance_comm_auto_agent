"""Wikipedia API client for company background research."""
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class WikipediaClient:
    """Client for Wikipedia API."""

    def __init__(self):
        """Initialize the Wikipedia search client."""
        self.base_url = "https://en.wikipedia.org/api/rest_v1/page/summary"

    def search_company_info(self, company_name: str, max_results: int = 5) -> Dict:
        """Search for company information on Wikipedia."""
        try:
            # Clean company name for URL
            clean_name = company_name.replace(" ", "_").replace("&", "and")

            response = requests.get(
                f"{self.base_url}/{clean_name}",
                timeout=10
            )

            if response.status_code == 404:
                return {
                    "results": [],
                    "summary": f"No Wikipedia page found for {company_name}",
                    "query": company_name
                }

            response.raise_for_status()
            data = response.json()

            # Extract relevant information
            results = []
            if "title" in data and "extract" in data:
                results.append({
                    "title": data.get("title", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "snippet": data.get("extract", ""),
                    "display_url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                })

            # Generate summary
            summary = self._generate_company_summary(results, company_name)

            return {
                "results": results,
                "summary": summary,
                "query": company_name,
                "total_results": len(results)
            }

        except requests.RequestException as e:
            logger.error(f"Wikipedia search failed: {e}")
            return {"results": [], "summary": f"Search failed: {str(e)}", "error": str(e)}
        except Exception as e:
            logger.error(f"Wikipedia processing failed: {e}")
            return {"results": [], "summary": f"Processing failed: {str(e)}", "error": str(e)}

    def _generate_company_summary(self, results: List[Dict], company_name: str) -> str:
        """Generate a summary of company information from Wikipedia results."""
        if not results:
            return f"No Wikipedia information found for {company_name}"

        result = results[0]
        snippet = result.get("snippet", "")

        # Extract key business information
        summary_parts = []

        # Look for founding information
        if "founded" in snippet.lower() or "incorporated" in snippet.lower():
            summary_parts.append("Company has established history with founding information available")

        # Look for industry information
        if any(term in snippet.lower() for term in ["company", "corporation", "inc", "ltd", "llc"]):
            summary_parts.append("Confirmed as a business entity")

        # Look for size indicators
        if any(term in snippet.lower() for term in ["employees", "revenue", "market cap", "billion", "million"]):
            summary_parts.append("Company size information available")

        if summary_parts:
            return f"Wikipedia: {'; '.join(summary_parts)}"
        else:
            return f"Wikipedia page exists for {company_name} with general business information"