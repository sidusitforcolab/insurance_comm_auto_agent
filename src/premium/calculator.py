"""Rules-based premium calculation engine."""
import logging
from typing import Dict, List, Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)


class PremiumCalculator:
    """Calculate insurance premiums using rules-based logic."""

    def __init__(self):
        """Initialize the premium calculator."""
        self.base_premiums = settings.base_premium_by_vehicle
        self.adjustment_rules = settings.premium_adjustment_rules

    def calculate_premium(self, vehicle_info: Dict, risk_factors: Dict,
                         web_search_results: Optional[Dict] = None) -> Dict:
        """Calculate the final premium based on vehicle and risk information."""
        try:
            # Start with base premium
            base_premium = self._get_base_premium(vehicle_info)

            # Apply risk-based adjustments
            adjustments = self._calculate_adjustments(vehicle_info, risk_factors, web_search_results)

            # Calculate final premium
            total_adjustment = sum(adjustments.values())
            final_premium = base_premium * (1 + total_adjustment)

            # Ensure minimum premium
            final_premium = max(final_premium, 300.0)  # Minimum $300

            # Round to nearest dollar
            final_premium = round(final_premium)

            return {
                "base_premium": base_premium,
                "adjustments": adjustments,
                "total_adjustment_percentage": total_adjustment,
                "final_premium": final_premium,
                "calculation_breakdown": self._generate_breakdown(base_premium, adjustments)
            }

        except Exception as e:
            logger.error(f"Premium calculation failed: {e}")
            # Return a conservative default
            return {
                "base_premium": 500.0,
                "adjustments": {"error_fallback": 0.5},
                "total_adjustment_percentage": 0.5,
                "final_premium": 750,
                "calculation_breakdown": "Error in calculation, using conservative estimate"
            }

    def _get_base_premium(self, vehicle_info: Dict) -> float:
        """Get base premium based on vehicle type."""
        vehicle_type = vehicle_info.get('type', 'sedan').lower()

        # Map to our predefined categories
        if 'truck' in vehicle_type or 'pickup' in vehicle_type:
            return self.base_premiums['truck']
        elif 'van' in vehicle_type or 'suv' in vehicle_type:
            return self.base_premiums['van']
        elif 'fleet' in vehicle_type:
            return self.base_premiums['fleet']
        else:
            return self.base_premiums['sedan']

    def _calculate_adjustments(self, vehicle_info: Dict, risk_factors: Dict,
                             web_search_results: Optional[Dict] = None) -> Dict[str, float]:
        """Calculate all premium adjustments."""
        adjustments = {}

        # Claims history adjustment
        claim_count = risk_factors.get('claim_count', 0)
        if claim_count > 0:
            adjustments['claims_history'] = claim_count * self.adjustment_rules['claim_multiplier']

        # Serious accident adjustment
        serious_accidents = risk_factors.get('serious_accident_count', 0)
        if serious_accidents > 0:
            adjustments['serious_accidents'] = serious_accidents * self.adjustment_rules['serious_accident_multiplier']

        # Violation adjustment
        violation_count = risk_factors.get('violation_count', 0)
        if violation_count > 0:
            adjustments['violations'] = violation_count * self.adjustment_rules['violation_multiplier']

        # Business age adjustment
        business_age_years = risk_factors.get('business_age_years', 5)
        if business_age_years < 1:
            adjustments['new_business'] = self.adjustment_rules['new_business_multiplier']
        elif business_age_years < 3:
            adjustments['young_business'] = self.adjustment_rules['young_business_multiplier']

        # Vehicle age adjustment (older vehicles might be riskier)
        vehicle_year = vehicle_info.get('year', 2020)
        current_year = 2024
        vehicle_age = current_year - vehicle_year
        if vehicle_age > 10:
            adjustments['vehicle_age'] = 0.2  # +20% for vehicles over 10 years old
        elif vehicle_age > 5:
            adjustments['vehicle_age'] = 0.1  # +10% for vehicles over 5 years old

        # Inspection results adjustment
        inspection_passed = risk_factors.get('inspection_passed', True)
        if not inspection_passed:
            failed_items = risk_factors.get('failed_items', 0)
            adjustments['inspection_failures'] = min(failed_items * 0.1, 0.5)  # Max 50% increase

        # Web search risk indicators
        if web_search_results:
            risk_score = web_search_results.get('risk_score', 0)
            if risk_score > 7:  # High risk
                adjustments['web_risk_high'] = self.adjustment_rules['bing_negative_flag_multiplier']
            elif risk_score > 4:  # Medium risk
                adjustments['web_risk_medium'] = self.adjustment_rules['bing_negative_flag_multiplier'] * 0.5

        # Territory adjustment (simplified - would need more location data)
        territory = risk_factors.get('territory', 'urban')
        if territory == 'urban':
            adjustments['urban_territory'] = 0.1  # +10% for urban areas

        return adjustments

    def _generate_breakdown(self, base_premium: float, adjustments: Dict[str, float]) -> str:
        """Generate a human-readable breakdown of the premium calculation."""
        lines = [f"Base Premium: ${base_premium:.2f}"]

        for factor, adjustment in adjustments.items():
            percentage = adjustment * 100
            amount = base_premium * adjustment
            factor_name = factor.replace('_', ' ').title()
            lines.append(f"{factor_name}: +{percentage:.1f}% (+${amount:.2f})")

        total_adjustment = sum(adjustments.values()) * 100
        final_premium = base_premium * (1 + sum(adjustments.values()))

        lines.append(f"Total Adjustment: +{total_adjustment:.1f}%")
        lines.append(f"Final Premium: ${final_premium:.2f}")

        return "\n".join(lines)

    def assess_underwriting_decision(self, premium_result: Dict, risk_factors: Dict) -> Dict:
        """Make an underwriting decision based on calculated premium and risk factors."""
        final_premium = premium_result['final_premium']
        total_adjustment = premium_result['total_adjustment_percentage']

        # Decision criteria
        max_acceptable_premium = 5000  # Maximum premium we'll offer
        max_acceptable_adjustment = 2.0  # Maximum 200% increase

        # Automatic reject conditions
        reject_conditions = []

        if risk_factors.get('claim_count', 0) > 5:
            reject_conditions.append("Too many claims (>5 in 3 years)")

        if risk_factors.get('serious_accident_count', 0) > 2:
            reject_conditions.append("Too many serious accidents (>2)")

        if not risk_factors.get('inspection_passed', True):
            reject_conditions.append("Failed vehicle inspection")

        if risk_factors.get('business_age_years', 5) < 0.5:
            reject_conditions.append("Business too new (<6 months)")

        # Make decision
        if reject_conditions:
            decision = "reject"
            reasoning = f"Rejected due to: {', '.join(reject_conditions)}"
        elif final_premium > max_acceptable_premium:
            decision = "reject"
            reasoning = f"Premium too high (${final_premium:.0f} > ${max_acceptable_premium})"
        elif total_adjustment > max_acceptable_adjustment:
            decision = "reject"
            reasoning = f"Risk adjustment too high ({total_adjustment*100:.0f}% > {max_acceptable_adjustment*100:.0f}%)"
        else:
            decision = "accept"
            reasoning = f"Accepted with premium ${final_premium:.0f}"

        return {
            "decision": decision,
            "premium": final_premium if decision == "accept" else None,
            "reasoning": reasoning,
            "risk_assessment": self._generate_risk_assessment(risk_factors)
        }

    def _generate_risk_assessment(self, risk_factors: Dict) -> str:
        """Generate a risk assessment summary."""
        assessments = []

        claim_count = risk_factors.get('claim_count', 0)
        if claim_count == 0:
            assessments.append("Clean claims history")
        elif claim_count <= 2:
            assessments.append(f"Moderate claims history ({claim_count} claims)")
        else:
            assessments.append(f"High claims frequency ({claim_count} claims)")

        violation_count = risk_factors.get('violation_count', 0)
        if violation_count == 0:
            assessments.append("No violations on record")
        else:
            assessments.append(f"{violation_count} violations noted")

        inspection_passed = risk_factors.get('inspection_passed', True)
        if inspection_passed:
            assessments.append("Vehicle inspection passed")
        else:
            assessments.append("Vehicle inspection failed")

        business_age = risk_factors.get('business_age_years', 5)
        if business_age >= 5:
            assessments.append("Established business")
        elif business_age >= 1:
            assessments.append("Relatively new business")
        else:
            assessments.append("Very new business")

        return "; ".join(assessments)