"""Web search agent that decides between multiple search APIs."""
import logging
from typing import Dict, Optional

from src.web_search.bing_client import BingSearchClient
from src.web_search.wikipedia_client import WikipediaClient

logger = logging.getLogger(__name__)


class WebSearchAgent:
    """Agent that selects and uses appropriate web search APIs."""

    def __init__(self):
        """Initialize the web search agent."""
        self.bing_client = BingSearchClient()
        self.wikipedia_client = WikipediaClient()

    def search_company_info(self, company_name: str, location: Optional[str] = None,
                          search_type: str = "comprehensive") -> Dict:
        """Search for company information using appropriate APIs.

        Args:
            company_name: Name of the company to search
            location: Optional location for more specific results
            search_type: Type of search - "comprehensive", "background", "financial"

        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Decide which APIs to use based on search type and company characteristics
            apis_to_use = self._select_search_apis(company_name, search_type)

            all_results = []
            summaries = []

            # Execute searches
            for api_name in apis_to_use:
                if api_name == "wikipedia":
                    wiki_results = self.wikipedia_client.search_company_info(company_name)
                    if wiki_results.get("results"):
                        all_results.extend(wiki_results["results"])
                        summaries.append(f"Wikipedia: {wiki_results.get('summary', '')}")

                elif api_name == "bing":
                    bing_results = self.bing_client.search_company_info(company_name, location)
                    if bing_results.get("results"):
                        all_results.extend(bing_results["results"])
                        summaries.append(f"Bing: {bing_results.get('summary', '')}")

            # Combine and deduplicate results
            unique_results = self._deduplicate_results(all_results)

            # Generate combined summary
            combined_summary = self._combine_summaries(summaries, company_name)

            return {
                "results": unique_results[:10],  # Limit to top 10 results
                "summary": combined_summary,
                "apis_used": apis_to_use,
                "total_results": len(unique_results),
                "query": company_name
            }

        except Exception as e:
            logger.error(f"Web search agent failed: {e}")
            return {
                "results": [],
                "summary": f"Search failed: {str(e)}",
                "apis_used": [],
                "error": str(e)
            }

    def _select_search_apis(self, company_name: str, search_type: str) -> list:
        """Select which APIs to use based on company and search type."""
        apis = []

        # Always try Wikipedia for established companies
        if search_type in ["comprehensive", "background"]:
            apis.append("wikipedia")

        # Use Bing for broader web search
        if search_type in ["comprehensive", "financial"]:
            apis.append("bing")

        # For financial searches, prioritize Bing for current data
        if search_type == "financial":
            apis = ["bing"] + [api for api in apis if api != "bing"]

        return apis

    def _deduplicate_results(self, results: list) -> list:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("url", "").lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    def _combine_summaries(self, summaries: list, company_name: str) -> str:
        """Combine summaries from multiple APIs."""
        if not summaries:
            return f"No information found for {company_name}"

        # Remove empty summaries
        valid_summaries = [s for s in summaries if s and not s.endswith(": ")]

        if not valid_summaries:
            return f"Search completed for {company_name} but no detailed information extracted"

    def search_risk_indicators(self, company_name: str, location: Optional[str] = None) -> Dict:
        """Search specifically for risk indicators using Bing."""
        return self.bing_client.search_risk_indicators(company_name, location)