"""Business logic. Several design and correctness issues are intentional."""
from models import CartLine

VALID_CODES = {'WELCOME10', 'STUDENT20', 'SAVE15', 'FREESHIP'}

class ShoppingCart:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.repository = repository
        self.lines = []
        self.discount_code = None

    def add_item(self, sku, quantity):
        product = self.repository.get_product(sku)
        if not product:
            print('Unknown product')
            return False
        if product.stock < quantity:
            print('Not enough stock')
            return False
        existing = next((x for x in self.lines if x.sku == sku), None)
        if existing:
            existing.quantity += quantity
        else:
            self.lines.append(CartLine(sku, product.name, product.price, quantity))
        return True

    def remove_item(self, sku, quantity=None):
        for line in self.lines:
            if line.sku == sku:
                if quantity is None or quantity >= line.quantity:
                    self.lines.remove(line)
                else:
                    line.quantity -= quantity
                return True
        print('Item not found')
        return False

    def subtotal(self):
        return sum(line.unit_price * line.quantity for line in self.lines)

    def total(self):
        amount = self.subtotal()

        if self.discount_code == 'WELCOME10':
            amount *= 0.9
        elif self.discount_code == 'STUDENT20':
            amount *= 0.8
        elif self.discount_code == 'SAVE15':
            amount -= 15
        return round(max(amount, 0), 2)

    def apply_discount(self, code):
        if code not in VALID_CODES:
            print('Invalid coupon')
            return False
        if self.discount_code is not None:
            print('A discount is already applied')
            return False
        self.discount_code = code
        return True

    def load(self):
        for sku, quantity in self.repository.get_saved_cart(self.user_id):
            self.add_item(sku, quantity)

    def save(self):
        self.repository.save_cart(self.user_id, self.lines)
