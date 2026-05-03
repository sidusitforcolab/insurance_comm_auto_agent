#!/usr/bin/env python3
"""Quick test script for the insurance agent components."""

from src.premium.calculator import PremiumCalculator

def test_premium_calculator():
    """Test the premium calculator."""
    print("Testing Premium Calculator...")

    calc = PremiumCalculator()

    # Test case 1: Low risk truck
    vehicle_info = {'type': 'truck', 'year': 2020}
    risk_factors = {'claim_count': 0, 'violation_count': 0}

    result = calc.calculate_premium(vehicle_info, risk_factors)
    print(f"Low risk truck: ${result['final_premium']}")

    # Test case 2: High risk truck
    risk_factors_high = {'claim_count': 2, 'violation_count': 1}
    result_high = calc.calculate_premium(vehicle_info, risk_factors_high)
    print(f"High risk truck: ${result_high['final_premium']}")

    # Test decision
    decision = calc.assess_underwriting_decision(result, risk_factors)
    print(f"Decision: {decision['decision']} - {decision['reasoning']}")

    print("Premium calculator test completed!")

if __name__ == "__main__":
    test_premium_calculator()