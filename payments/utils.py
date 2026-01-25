# payments/utils.py
from decimal import Decimal, ROUND_HALF_UP

def calculate_payment(request_type: str):
    """
    Calculates payment for an ID request.
    - NEW ID: 10 cedis
    - LOST / EXPIRED: 15 cedis
    - Service fee: 20% of base
    - Paystack fee: 2% of (base + service fee)
    
    Returns:
        base_amount, service_fee, paystack_fee, total_amount (all Decimal)
    """
    # Base price
    if request_type == "NEW":
        base = Decimal("10.00")
    elif request_type in ["LOST", "EXPIRED"]:
        base = Decimal("15.00")
    else:
        raise ValueError(f"Invalid request type: {request_type}")

    # Service fee 20%
    service_fee = (base * Decimal("0.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Subtotal for Paystack fee calculation
    subtotal = base + service_fee

    # Paystack fee 2%
    paystack_fee = (subtotal * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Total amount to pay
    total = (subtotal + paystack_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return base, service_fee, paystack_fee, total
