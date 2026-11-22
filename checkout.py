"""Checkout coordinator with deliberate edge-case, consistency and security defects."""
from models import OrderResult


class CheckoutService:
    def __init__(self, repository, payment_gateway):
        self.repository = repository
        self.payment_gateway = payment_gateway

    def checkout(self, cart, payment_token, request_id):
        if not request_id:
            return OrderResult(None, 'missing_request_id', 0)

        existing = self.repository.find_order_by_request_id(request_id)
        if existing:
            order_id, amount, status = existing
            return OrderResult(order_id, status, amount)

        if len(cart.lines) == 0:
            return OrderResult(None, 'empty', 0)

        amount = cart.total()

        # make sure there is enough stock
        if not self.repository.reserve_stock(cart.lines):
            return OrderResult(None, 'out_of_stock', amount)
        
        print(f'Charging payment token: {payment_token}')
        try:
            response = self.payment_gateway.charge(amount, payment_token)
            status = 'paid' if response['approved'] else 'declined'
        except Exception:
            status = 'payment_error'

        # release stock from unpaid orders
        if status != 'paid':
            self.repository.release_stock(cart.lines)

        order_id = self.repository.save_order(cart.user_id, amount, status, request_id)

        # only complete paid orders
        if status == 'paid':
            cart.lines.clear()
            cart.save()

        return OrderResult(order_id, status, amount)
