"""Basic tests for the insurance underwriting agent."""
import pytest
from unittest.mock import Mock, patch

from src.agent.graph import InsuranceUnderwritingAgent, UnderwritingState
from src.premium.calculator import PremiumCalculator


class TestPremiumCalculator:
    """Test the premium calculation logic."""

    def test_base_premium_calculation(self):
        """Test base premium calculation for different vehicle types."""
        calculator = PremiumCalculator()

        # Test truck premium
        vehicle_info = {"type": "truck", "year": 2020}
        risk_factors = {"claim_count": 0, "violation_count": 0}

        result = calculator.calculate_premium(vehicle_info, risk_factors)

        assert result["base_premium"] == 1200.0
        assert result["final_premium"] > 0

    def test_risk_adjustments(self):
        """Test that risk factors increase premium."""
        calculator = PremiumCalculator()

        vehicle_info = {"type": "truck", "year": 2020}

        # Low risk
        low_risk = {"claim_count": 0, "violation_count": 0}
        low_result = calculator.calculate_premium(vehicle_info, low_risk)

        # High risk
        high_risk = {"claim_count": 3, "violation_count": 2}
        high_result = calculator.calculate_premium(vehicle_info, high_risk)

        assert high_result["final_premium"] > low_result["final_premium"]

    def test_underwriting_decision(self):
        """Test underwriting decision logic."""
        calculator = PremiumCalculator()

        # Test acceptance
        premium_result = {"final_premium": 1500, "total_adjustment_percentage": 0.5}
        risk_factors = {"claim_count": 1, "inspection_passed": True}

        decision = calculator.assess_underwriting_decision(premium_result, risk_factors)

        assert decision["decision"] == "accept"
        assert decision["premium"] == 1500

    def test_rejection_conditions(self):
        """Test automatic rejection conditions."""
        calculator = PremiumCalculator()

        # Test rejection due to too many claims
        premium_result = {"final_premium": 1500, "total_adjustment_percentage": 0.5}
        risk_factors = {"claim_count": 6, "inspection_passed": True}  # Too many claims

        decision = calculator.assess_underwriting_decision(premium_result, risk_factors)

        assert decision["decision"] == "reject"


class TestUnderwritingAgent:
    """Test the LangGraph underwriting agent."""

    @patch('src.agent.graph.PGVectorClient')
    @patch('src.agent.graph.BingSearchClient')
    def test_agent_initialization(self, mock_bing, mock_pg):
        """Test agent initialization."""
        mock_pg.return_value = Mock()
        mock_bing.return_value = Mock()

        agent = InsuranceUnderwritingAgent()

        assert agent.pg_client is not None
        assert agent.bing_client is not None
        assert agent.workflow is not None

    @patch('src.agent.graph.PGVectorClient')
    @patch('src.agent.graph.BingSearchClient')
    def test_data_extraction_node(self, mock_bing, mock_pg):
        """Test the data extraction node."""
        # Mock the database client
        mock_client = Mock()
        mock_client.get_applicant_documents.return_value = [
            {
                "id": 1,
                "filename": "test.pdf",
                "document_type": "mvr",
                "content": "Driver John Doe, License DL123456, Vehicle Ford F-150 2020"
            }
        ]
        mock_pg.return_value = mock_client
        mock_bing.return_value = Mock()

        agent = InsuranceUnderwritingAgent()

        # Test data extraction
        state = UnderwritingState(applicant_id="TEST001")
        result_state = agent._extract_data(state)

        assert result_state.applicant_id == "TEST001"
        assert len(result_state.document_chunks) > 0
        assert isinstance(result_state.vehicle_info, dict)
        assert isinstance(result_state.risk_factors, dict)


if __name__ == "__main__":
    # Run basic tests
    calculator = PremiumCalculator()

    # Test 1: Base premium
    vehicle_info = {"type": "truck", "year": 2020}
    risk_factors = {"claim_count": 0, "violation_count": 0}
    result = calculator.calculate_premium(vehicle_info, risk_factors)
    print(f"Base premium test: ${result['final_premium']}")

    # Test 2: Risk adjustment
    risk_factors_high = {"claim_count": 2, "violation_count": 1}
    result_high = calculator.calculate_premium(vehicle_info, risk_factors_high)
    print(f"High risk premium: ${result_high['final_premium']}")

    # Test 3: Decision
    decision = calculator.assess_underwriting_decision(result, risk_factors)
    print(f"Decision: {decision['decision']}")

    print("Basic tests completed successfully!")