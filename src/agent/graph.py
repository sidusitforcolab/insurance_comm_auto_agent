"""LangGraph workflow for insurance underwriting agent."""
import logging
import re
from typing import Dict, List, Optional, Any

from langgraph.graph import StateGraph
from pydantic import BaseModel

from src.config.settings import settings
from src.external.pinecone_client import PineconeClient
from src.external.tawily_client import TawilyClient
from src.model.sagemaker_client import SageMakerClient
from src.observability.arize_phoenix import ArizePhoenixClient
from src.observability.langsmith_integration import LangSmithTracer
from src.observability.ragas_client import RagasClient
from src.premium.calculator import PremiumCalculator
from src.retrieval.pgvector_client import PGVectorClient
from src.security.aws_waf import AwsWafManager
from src.security.llama_guard import LlamaGuard, validate_company_input
from src.web_search.web_search_agent import WebSearchAgent

logger = logging.getLogger(__name__)


class UnderwritingState(BaseModel):
    """State object for the underwriting workflow."""
    applicant_id: str
    company_name: Optional[str] = None
    business_age: Optional[int] = None
    number_of_vehicles: Optional[int] = None
    vehicle_types: List[str] = []
    previous_claims: Optional[int] = 0
    serious_accidents: Optional[int] = 0
    safety_program: Optional[bool] = False
    annual_mileage: Optional[int] = None
    vehicle_info: Dict = {}
    risk_factors: Dict = {}
    document_chunks: List[Dict] = []
    web_search_results: Optional[Dict] = None
    financial_data: Optional[Dict] = None
    premium_calculation: Optional[Dict] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    errors: List[str] = []


class InsuranceUnderwritingAgent:
    """LangGraph-based agent for commercial auto insurance underwriting."""

    def __init__(self):
        """Initialize the underwriting agent."""
        self.pg_client = PGVectorClient()
        self.embedding_client = EmbeddingClient()
        self.web_search_agent = WebSearchAgent()
        self.financial_data_agent = FinancialDataAgent()
        self.premium_calculator = PremiumCalculator()
        self.security_guard = LlamaGuard()
        self.pinecone_client = PineconeClient(settings.pinecone_api_key, settings.pinecone_environment)
        self.tawily_client = TawilyClient(settings.tawily_api_key)
        self.sagemaker_client = SageMakerClient(settings.sagemaker_region)
        self.langsmith_tracer = LangSmithTracer(settings.langsmith_api_key, settings.langsmith_project)
        self.ragas_client = RagasClient(settings.ragas_api_key)
        self.arize_client = ArizePhoenixClient(settings.arize_api_key)
        self.waf_manager = AwsWafManager(settings.aws_waf_region)

        # Build the LangGraph workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the LangGraph workflow and compile it."""
        workflow = StateGraph(UnderwritingState)

        # Add nodes
        workflow.add_node("data_extraction", self._extract_data)
        workflow.add_node("web_search", self._perform_web_search)
        workflow.add_node("financial_data", self._get_financial_data)
        workflow.add_node("risk_assessment", self._assess_risk)
        workflow.add_node("premium_calculation", self._calculate_premium)
        workflow.add_node("llm_reasoning", self._llm_reasoning)
        workflow.add_node("decision", self._make_decision)

        # Define the flow
        workflow.set_entry_point("data_extraction")
        workflow.set_finish_point("decision")

        # Add edges with conditional logic
        workflow.add_edge("data_extraction", "web_search")
        workflow.add_edge("web_search", "financial_data")
        workflow.add_edge("financial_data", "risk_assessment")
        workflow.add_edge("risk_assessment", "premium_calculation")
        workflow.add_edge("premium_calculation", "llm_reasoning")
        workflow.add_edge("llm_reasoning", "decision")

        return workflow.compile()

    def _extract_data(self, state: UnderwritingState) -> UnderwritingState:
        """Extract data from documents and structure it."""
        try:
            logger.info(f"Extracting data for applicant {state.applicant_id}")

            # Get documents for this applicant
            documents = self.pg_client.get_applicant_documents(state.applicant_id)

            if not documents:
                state.errors.append("No documents found for applicant")
                return state

            # Search for relevant document chunks using vector similarity
            query = f"insurance underwriting data for {state.company_name or 'company'} commercial auto policy"
            query_embedding = self.embedding_client.generate_query_embedding(query)

            # Search for similar documents in pgvector
            search_results = self.pg_client.search_similar_documents(
                query_embedding=query_embedding,
                applicant_id=state.applicant_id,
                top_k=10
            )

            # Format results for state
            state.document_chunks = []
            for result in search_results:
                state.document_chunks.append({
                    "text": result["chunk_text"],
                    "document_type": result["document_type"],
                    "filename": result["filename"],
                    "similarity_score": result["similarity_score"],
                    "metadata": result["metadata"]
                })

            # Assess retrieval quality with Ragas
            self.ragas_client.evaluate_retrieval(query, state.document_chunks)

            # Extract structured data from chunks
            vehicle_info = self._extract_vehicle_info(state.document_chunks)
            risk_factors = self._extract_risk_factors(state.document_chunks)

            state.vehicle_info = vehicle_info
            state.risk_factors = risk_factors

            logger.info(f"Extracted {len(all_chunks)} chunks, vehicle info: {vehicle_info.keys()}")

        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            state.errors.append(f"Data extraction error: {str(e)}")

        return state

    def _perform_web_search(self, state: UnderwritingState) -> UnderwritingState:
        """Perform web search for company background."""
        try:
            if not state.company_name:
                logger.info("No company name provided, skipping web search")
                return state

            # Validate company name for security
            validation = validate_company_input(state.company_name)
            if not validation['safe']:
                logger.warning(f"Company name validation failed: {validation['issues']}")
                state.errors.append("Company name validation failed")
                return state

            logger.info(f"Performing web search for company: {state.company_name}")

            # Search for company information
            search_results = self.web_search_agent.search_company_info(state.company_name)

            # Also check for risk indicators
            risk_results = self.web_search_agent.search_risk_indicators(state.company_name)
            tawily_results = self.tawily_client.fetch_company_risk(state.company_name)

            state.web_search_results = {
                "company_info": search_results,
                "risk_indicators": risk_results,
                "tawily": tawily_results
            }

            logger.info(f"Web search completed, found {len(search_results.get('results', []))} results")

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            state.errors.append(f"Web search error: {str(e)}")

        return state

    def _get_financial_data(self, state: UnderwritingState) -> UnderwritingState:
        """Retrieve financial data for the company."""
        try:
            if not state.company_name:
                logger.info("No company name provided, skipping financial data retrieval")
                return state

            logger.info(f"Retrieving financial data for company: {state.company_name}")

            # Get financial data using the financial data agent
            financial_results = self.financial_data_agent.get_company_financials(state.company_name)

            state.financial_data = financial_results

            logger.info(f"Financial data retrieval completed, data available: {financial_results.get('available', False)}")

        except Exception as e:
            logger.error(f"Financial data retrieval failed: {e}")
            state.errors.append(f"Financial data error: {str(e)}")

        return state

    def _assess_risk(self, state: UnderwritingState) -> UnderwritingState:
        """Assess overall risk based on extracted data and web search."""
        try:
            logger.info("Assessing risk factors")

            risk_factors = state.risk_factors.copy()

            # Incorporate web search results
            if state.web_search_results:
                risk_score = state.web_search_results.get('risk_indicators', {}).get('risk_score', 0)
                risk_factors['web_risk_score'] = risk_score

                if state.web_search_results.get('tawily'):
                    tawily_level = state.web_search_results['tawily'].get('risk_level', 'medium').lower()
                    risk_factors['tawily_risk_level'] = tawily_level
                    if tawily_level == 'high':
                        risk_factors['high_external_risk'] = True

                # Estimate business age from search results
                company_info = state.web_search_results.get('company_info', {}).get('summary', '')
                if 'established' in company_info.lower() or 'years in business' in company_info.lower():
                    risk_factors['business_age_years'] = 5  # Assume established
                else:
                    risk_factors['business_age_years'] = 2  # Assume relatively new

            # Set defaults for missing risk factors
            risk_factors.setdefault('claim_count', 0)
            risk_factors.setdefault('violation_count', 0)
            risk_factors.setdefault('serious_accident_count', 0)
            risk_factors.setdefault('inspection_passed', True)
            risk_factors.setdefault('business_age_years', 3)
            risk_factors.setdefault('territory', 'urban')

            state.risk_factors = risk_factors

            logger.info(f"Risk assessment complete: {len(risk_factors)} factors evaluated")

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            state.errors.append(f"Risk assessment error: {str(e)}")

        return state

    def _calculate_premium(self, state: UnderwritingState) -> UnderwritingState:
        """Calculate premium using rules-based engine."""
        try:
            logger.info("Calculating premium")

            premium_result = self.premium_calculator.calculate_premium(
                state.vehicle_info,
                state.risk_factors,
                state.web_search_results
            )

            state.premium_calculation = premium_result

            logger.info(f"Premium calculated: ${premium_result['final_premium']}")

        except Exception as e:
            logger.error(f"Premium calculation failed: {e}")
            state.errors.append(f"Premium calculation error: {str(e)}")

        return state

    def _llm_reasoning(self, state: UnderwritingState) -> UnderwritingState:
        """Use LLM for final reasoning and justification."""
        try:
            logger.info("Performing LLM reasoning")

            # Prepare context for LLM
            context = self._prepare_llm_context(state)

            # If a SageMaker endpoint is configured, invoke it for reasoning
            llm_insight = None
            if settings.sagemaker_endpoint_name:
                payload = {
                    "input": context,
                    "premium": state.premium_calculation
                }
                model_response = self.sagemaker_client.invoke_text_model(
                    endpoint_name=settings.sagemaker_endpoint_name,
                    payload=str(payload)
                )
                if model_response:
                    llm_insight = model_response

            if llm_insight is None:
                llm_insight = self._simulate_llm_reasoning(context, state.premium_calculation)

            # Update premium calculation with LLM insights
            if state.premium_calculation:
                state.premium_calculation['llm_reasoning'] = llm_insight

            logger.info("LLM reasoning completed")

        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            state.errors.append(f"LLM reasoning error: {str(e)}")

        return state

    def _make_decision(self, state: UnderwritingState) -> UnderwritingState:
        """Make final underwriting decision."""
        try:
            logger.info("Making underwriting decision")

            if not state.premium_calculation:
                state.decision = "reject"
                state.reasoning = "Unable to calculate premium due to missing data"
                return state

            decision_result = self.premium_calculator.assess_underwriting_decision(
                state.premium_calculation,
                state.risk_factors
            )

            state.decision = decision_result['decision']
            state.reasoning = decision_result['reasoning']

            # Update premium if accepted
            if state.decision == "accept":
                state.premium_calculation['final_premium'] = decision_result['premium']

            # Tracing and production monitoring
            self.langsmith_tracer.log_event("underwriting_decision", {
                "applicant_id": state.applicant_id,
                "decision": state.decision,
                "premium": state.premium_calculation.get('final_premium'),
                "risk_factors": state.risk_factors
            })
            self.arize_client.publish_event("underwriting_decision", {
                "applicant_id": state.applicant_id,
                "decision": state.decision,
                "premium": state.premium_calculation.get('final_premium')
            })

            logger.info(f"Decision made: {state.decision}")

        except Exception as e:
            logger.error(f"Decision making failed: {e}")
            state.decision = "reject"
            state.reasoning = f"Decision error: {str(e)}"

        return state

    def _chunk_text_simple(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Simple text chunking (production would use more sophisticated methods)."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                # Try to break at sentence
                sentence_end = text.rfind('.', end - 100, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end
        return chunks

    def _extract_vehicle_info(self, chunks: List[Dict]) -> Dict:
        """Extract vehicle information from document chunks."""
        vehicle_info = {}

        for chunk in chunks:
            text = chunk['text'].lower()

            # Extract vehicle type
            if 'truck' in text and not vehicle_info.get('type'):
                vehicle_info['type'] = 'truck'
            elif 'van' in text and not vehicle_info.get('type'):
                vehicle_info['type'] = 'van'

            # Extract year (simple pattern)
            year_match = re.search(r'\b(20\d{2})\b', chunk['text'])
            if year_match and not vehicle_info.get('year'):
                vehicle_info['year'] = int(year_match.group(1))

        # Set defaults
        vehicle_info.setdefault('type', 'truck')  # Default for commercial auto
        vehicle_info.setdefault('year', 2020)

        return vehicle_info

    def _extract_risk_factors(self, chunks: List[Dict]) -> Dict:
        """Extract risk factors from document chunks."""
        risk_factors = {
            'claim_count': 0,
            'violation_count': 0,
            'serious_accident_count': 0,
            'inspection_passed': True,
            'failed_items': 0
        }

        for chunk in chunks:
            text = chunk['text'].lower()

            # Count claims
            risk_factors['claim_count'] += text.count('claim')

            # Count violations
            risk_factors['violation_count'] += text.count('violation') + text.count('citation')

            # Check for serious accidents
            serious_terms = ['injury', 'fatality', 'hospital', 'serious']
            for term in serious_terms:
                if term in text:
                    risk_factors['serious_accident_count'] += 1
                    break

            # Check inspection results
            if 'fail' in text:
                risk_factors['inspection_passed'] = False
                risk_factors['failed_items'] += 1

        return risk_factors

    def _prepare_llm_context(self, state: UnderwritingState) -> str:
        """Prepare context for LLM reasoning."""
        context_parts = []

        context_parts.append(f"Applicant ID: {state.applicant_id}")

        if state.company_name:
            context_parts.append(f"Company: {state.company_name}")

        context_parts.append(f"Vehicle: {state.vehicle_info}")

        context_parts.append(f"Risk Factors: {state.risk_factors}")

        if state.premium_calculation:
            context_parts.append(f"Calculated Premium: ${state.premium_calculation['final_premium']}")

        if state.web_search_results:
            summary = state.web_search_results.get('company_info', {}).get('summary', '')
            context_parts.append(f"Web Search Summary: {summary}")
            tawily_info = state.web_search_results.get('tawily', {})
            if tawily_info:
                context_parts.append(f"Tawily Risk Level: {tawily_info.get('risk_level')}")
                context_parts.append(f"Tawily Notes: {tawily_info.get('notes')}")

        return "\n".join(context_parts)

    def _simulate_llm_reasoning(self, context: str, premium_calc: Optional[Dict]) -> str:
        """Simulate LLM reasoning (would call actual LLM in production)."""
        if not premium_calc:
            return "Unable to assess premium due to missing calculation data."

        final_premium = premium_calc['final_premium']

        # Simple rule-based reasoning simulation
        if final_premium > 3000:
            return f"Premium of ${final_premium} is high due to significant risk factors. Consider requiring additional safety measures."
        elif final_premium < 800:
            return f"Premium of ${final_premium} reflects low risk profile. Good candidate for coverage."
        else:
            return f"Premium of ${final_premium} is reasonable based on assessed risk factors and market conditions."

    def process_underwriting(
        self,
        applicant_id: str,
        company_name: Optional[str] = None,
        business_age: Optional[int] = None,
        number_of_vehicles: Optional[int] = None,
        vehicle_types: Optional[List[str]] = None,
        previous_claims: Optional[int] = None,
        serious_accidents: Optional[int] = None,
        safety_program: Optional[bool] = None,
        annual_mileage: Optional[int] = None
    ) -> Dict:
        """Process an underwriting request."""
        try:
            # Check cache first
            cached_result = self.pg_client.get_underwriting_decision(applicant_id)
            if cached_result:
                logger.info(f"Returning cached decision for applicant {applicant_id}")
                return {
                    "applicant_id": applicant_id,
                    "decision": cached_result["decision"],
                    "premium": cached_result["premium_amount"],
                    "reasoning": cached_result["reasoning"],
                    "cached": True
                }

            # Initialize state
            initial_state = UnderwritingState(
                applicant_id=applicant_id,
                company_name=company_name,
                business_age=business_age,
                number_of_vehicles=number_of_vehicles,
                vehicle_types=vehicle_types or [],
                previous_claims=previous_claims or 0,
                serious_accidents=serious_accidents or 0,
                safety_program=safety_program if safety_program is not None else False,
                annual_mileage=annual_mileage
            )

            # Evaluate WAF recommendations and trace the request
            waf_recommendations = self.waf_manager.get_recommendations()
            self.langsmith_tracer.log_event("waf_recommendations", waf_recommendations)

            # Execute workflow
            final_state_dict = self.workflow.invoke(initial_state.model_dump())
            final_state = UnderwritingState(**final_state_dict)

            # Cache result
            if final_state.decision:
                self.pg_client.cache_underwriting_decision(
                    applicant_id,
                    final_state.decision,
                    final_state.premium_calculation.get('final_premium') if final_state.decision == 'accept' else None,
                    final_state.reasoning or "No reasoning provided"
                )

            # Return result
            result = {
                "applicant_id": applicant_id,
                "decision": final_state.decision,
                "premium": final_state.premium_calculation.get('final_premium') if final_state.decision == 'accept' else None,
                "reasoning": final_state.reasoning,
                "errors": final_state.errors,
                "cached": False
            }

            logger.info(f"Underwriting completed for {applicant_id}: {final_state.decision}")
            return result

        except Exception as e:
            logger.error(f"Underwriting processing failed: {e}")
            return {
                "applicant_id": applicant_id,
                "decision": "error",
                "premium": None,
                "reasoning": f"Processing error: {str(e)}",
                "errors": [str(e)],
                "cached": False
            }