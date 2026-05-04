"""Financial data agent that decides between SEC and DnB data sources."""
import logging
from typing import Dict, Optional

from src.financial.dnb_client import DnBClient
from src.financial.sec_client import SECClient

logger = logging.getLogger(__name__)


class FinancialDataAgent:
    """Agent that selects and retrieves financial data from appropriate sources."""

    def __init__(self):
        """Initialize the financial data agent."""
        self.sec_client = SECClient()
        self.dnb_client = DnBClient()

    def get_company_financials(self, company_name: str, location: Optional[str] = None,
                             data_preference: str = "auto") -> Dict:
        """Get financial data for a company using appropriate data sources.

        Args:
            company_name: Name of the company
            location: Optional company location
            data_preference: "auto", "public", "proprietary", "both"

        Returns:
            Dictionary with financial data and metadata
        """
        try:
            # Decide which data sources to use
            sources_to_use = self._select_data_sources(company_name, data_preference)

            results = {}

            # Collect data from selected sources
            for source in sources_to_use:
                if source == "sec":
                    results["sec"] = self.sec_client.search_company_financials(company_name)
                elif source == "dnb":
                    results["dnb"] = self.dnb_client.search_company_financials(company_name, location)

            # Combine and prioritize results
            combined_result = self._combine_financial_data(results, company_name, data_preference)

            return combined_result

        except Exception as e:
            logger.error(f"Financial data agent failed for {company_name}: {e}")
            return {
                "company_name": company_name,
                "financial_data": {},
                "summary": f"Financial data retrieval failed: {str(e)}",
                "data_sources": [],
                "available": False,
                "error": str(e)
            }

    def _select_data_sources(self, company_name: str, data_preference: str) -> list:
        """Select which data sources to use based on preference and company type."""
        if data_preference == "public":
            return ["sec"]
        elif data_preference == "proprietary":
            return ["dnb"]
        elif data_preference == "both":
            return ["sec", "dnb"]
        else:  # "auto"
            # For public companies, prefer SEC; for private, use DnB
            # This is a simplified heuristic - in practice, you'd check if company is public
            return ["sec", "dnb"]  # Try both and let quality decide

    def _combine_financial_data(self, results: Dict, company_name: str, data_preference: str) -> Dict:
        """Combine financial data from multiple sources."""
        combined_data = {
            "company_name": company_name,
            "financial_data": {},
            "summary": "",
            "data_sources": list(results.keys()),
            "available": False,
            "source_details": {}
        }

        # Extract successful results
        successful_sources = {}
        summaries = []

        for source_name, result in results.items():
            if result.get("available", False):
                successful_sources[source_name] = result
                summaries.append(result.get("summary", ""))
                combined_data["source_details"][source_name] = {
                    "available": True,
                    "summary": result.get("summary", "")
                }
            else:
                combined_data["source_details"][source_name] = {
                    "available": False,
                    "error": result.get("error", "No data available")
                }

        # Combine financial data
        if successful_sources:
            combined_data["available"] = True
            combined_data["financial_data"] = self._merge_financial_metrics(successful_sources)
            combined_data["summary"] = self._create_combined_summary(summaries, company_name)
        else:
            combined_data["summary"] = f"No financial data available for {company_name} from any source"

        return combined_data

    def _merge_financial_metrics(self, sources: Dict) -> Dict:
        """Merge financial metrics from different sources."""
        merged = {}

        # Collect all available metrics
        all_metrics = {}
        for source_name, source_data in sources.items():
            financial_data = source_data.get("financial_data", {})
            for key, value in financial_data.items():
                if value is not None:
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append({
                        "value": value,
                        "source": source_name
                    })

        # For each metric, choose the best value
        for metric, values in all_metrics.items():
            if len(values) == 1:
                merged[metric] = values[0]["value"]
                merged[f"{metric}_source"] = values[0]["source"]
            else:
                # Prefer SEC for public financials, DnB for proprietary
                if metric in ["revenue", "net_income", "total_assets"]:
                    # Use SEC if available for standardized financials
                    sec_value = next((v for v in values if v["source"] == "sec"), None)
                    if sec_value:
                        merged[metric] = sec_value["value"]
                        merged[f"{metric}_source"] = "sec"
                    else:
                        merged[metric] = values[0]["value"]
                        merged[f"{metric}_source"] = values[0]["source"]
                else:
                    # Use most recent or highest quality source
                    merged[metric] = values[0]["value"]
                    merged[f"{metric}_source"] = values[0]["source"]

        return merged

    def _create_combined_summary(self, summaries: list, company_name: str) -> str:
        """Create a combined summary from multiple data sources."""
        if not summaries:
            return f"No financial summaries available for {company_name}"

        if len(summaries) == 1:
            return summaries[0]

        # Combine summaries intelligently
        combined_parts = [f"Financial data for {company_name} from multiple sources:"]

        for summary in summaries:
            # Extract key points from each summary
            if "revenue" in summary.lower():
                combined_parts.append("Revenue information available")
            if "employee" in summary.lower():
                combined_parts.append("Employee data available")
            if "credit" in summary.lower():
                combined_parts.append("Credit assessment available")
            if "filing" in summary.lower():
                combined_parts.append("Regulatory filings available")

        if len(combined_parts) == 1:
            return f"Financial data available for {company_name} from {len(summaries)} sources"

        return ". ".join(combined_parts)