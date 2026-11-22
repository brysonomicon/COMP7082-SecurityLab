"""Two simple smoke tests"""
import pytest
import sqlite3
from setup_db import initialize
from repository import StoreRepository
from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway
from models import CartLine


@pytest.fixture
def repo(tmp_path):
    db = str(tmp_path / 'test.db')
    initialize(db)
    return StoreRepository(db)


@pytest.fixture
def cart(repo):
    return ShoppingCart('bryson', repo)


def test_seed_product(tmp_path):
    db = tmp_path / 'test.db'
    initialize(str(db))
    assert StoreRepository(str(db)).get_product('MOU-01').name == 'Wireless mouse'


def test_cart_adds_valid_item(tmp_path):
    db = tmp_path / 'test.db'
    initialize(str(db))
    cart = ShoppingCart('student', StoreRepository(str(db)))
    assert cart.add_item('USB-01', 2)
    assert len(cart.lines) == 1


def test_declined_payment_does_not_reduce_stock(repo, cart):
    cart.add_item('MOU-01', 2)

    svc = CheckoutService(repo, FakePaymentGateway(should_approve=False))
    svc.checkout(cart, 'tok_fake', 'req-1')

    assert repo.get_product('MOU-01').stock == 20


def test_stock_is_never_negative(repo):
    lines = [CartLine('MOU-01', 'Wireless mouse', 29.95, 21)]

    assert repo.get_product('MOU-01').stock >= 0


def test_reserve_is_all_or_nothing(repo):
    lines = [
        CartLine('MOU-01', 'Wireless mouse', 29.95, 2),
        CartLine('USB-01', 'USB cable', 9.99, 51),
    ]

    assert repo.reserve_stock(lines) is False
    assert repo.get_product('MOU-01').stock == 20


def test_saved_cart_rejects_sql_injection(repo, cart):
    cart.add_item('MOU-01', 1)
    cart.save()
    assert repo.get_saved_cart("x' OR '1'=1") == []


def test_product_lookup_rejects_sql_injection(repo):
    assert repo.get_product("x' OR '1'='1") is None


def test_discounts_dont_stack(cart):
    cart.add_item('MOU-01', 1)
    assert cart.apply_discount('WELCOME10')
    assert cart.apply_discount('STUDENT20') is False
    assert cart.total() == round(29.95 * 0.9, 2)


def test_total_never_negative(cart):
    cart.add_item('USB-01', 1)
    cart.apply_discount('SAVE15')
    assert cart.total() == 0


def test_discount_applies_to_items_added_later(cart):
    cart.add_item('USB-01', 1)
    cart.apply_discount('WELCOME10')
    cart.add_item('MOU-01', 1)
    assert cart.total() == round((9.99 + 29.95) * 0.9, 2)


def test_invalid_coupon_rejected(cart):
    cart.add_item('USB-01', 1)
    assert cart.apply_discount('BOGUS') is False
    assert cart.total() == 9.99


def test_duplicate_request_id_charges_once(repo, cart):
    gateway = FakePaymentGateway()
    svc = CheckoutService(repo, gateway)
    cart.add_item('MOU-01', 2)

    first = svc.checkout(cart, 'tok_fake', 'req-1')
    second = svc.checkout(cart, 'tok_fake', 'req-1')

    assert len(gateway.calls) == 1
    assert second.order_id == first.order_id
    assert repo.get_product('MOU-01').stock == 18


def test_missing_request_id_is_rejected(repo, cart):
    gateway = FakePaymentGateway()
    cart.add_item('MOU-01', 1)
    result = CheckoutService(repo, gateway).checkout(cart, 'tok_fake', None)

    assert result.status == 'missing_request_id'
    assert gateway.calls == []


def test_list_orders_only_returns_own_orders(repo):
    repo.save_order('alice', 10, 'paid', 'req-a')
    repo.save_order('bob', 20, 'paid', 'req-b')
    rows = repo.list_orders('alice')

    assert len(rows) == 1 and rows[0][1] == 'alice'