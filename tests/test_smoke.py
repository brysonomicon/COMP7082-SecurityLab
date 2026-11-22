"""Two simple smoke tests"""
import pytest
import sqlite3
from setup_db import initialize
from repository import StoreRepository
from cart import ShoppingCart
from checkout import CheckoutService
from payments import FakePaymentGateway


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
    repo.update_stock('MOU-01', 21)

    assert repo.get_product('MOU-01').stock >= 0