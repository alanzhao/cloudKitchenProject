from kitchen import Kitchen
from flask import Flask
import redis
import types
from helpers import load_data


def setup_kitchen():
    app = Flask(__name__)
    app.config.from_mapping(
        LAMBDA=3.25,
        HOT_SHELF_SIZE=15,
        COLD_SHELF_SIZE=15,
        FROZEN_SHELF_SIZE=15,
        OVERFLOW_SHELF_SIZE=20,
        JSON_FILE='test_orders.json'
    )
    redis_store = redis.Redis(host='localhost', port=6379, db=0, encoding='utf-8', decode_responses=True)
    kitchen = Kitchen(app, redis_store)
    return kitchen


def test_stream_orders():
    kitchen = setup_kitchen()
    yield_value = kitchen.stream_orders()

    assert isinstance(yield_value, types.GeneratorType)


def test_did_orders_change():
    kitchen = setup_kitchen()

    orders = []
    previous_orders = []
    assert kitchen.did_orders_change(orders, previous_orders) == False

    previous_orders = [{'redisKey': 1}]
    assert kitchen.did_orders_change(orders, previous_orders) == True


def test_group_orders():
    kitchen = setup_kitchen()
    sample_order = [{
        "redisKey": "1",
        "id": "1",
        "expirationAge": "1",
        "temp": "hot",
        "shelfLife": 100,
        "decayRate": .5
    }]
    grouped = kitchen.group_orders(sample_order)
    assert len(grouped.keys()) == 4


def test_queue_orders():
    kitchen = setup_kitchen()
    size = kitchen.queue_orders()

    assert size != 0
    assert len(kitchen.redis_store.keys()) > 0


def test_process_order():
    kitchen = setup_kitchen()
    order = load_data(kitchen.app.config["JSON_FILE"])[0]
    order["id"] = "1"
    order["expirationAge"] = "1"
    order["temp"] = "hot"
    order["shelfLife"] = 100
    order["decayRate"] = .5
    kitchen.process_order(order)

    processed_order = kitchen.redis_store.hgetall(order['temp'] + ':' + order['id'])
    assert processed_order != None
    assert 'redisKey' in processed_order


def test_remove_expiring_order():
    kitchen = setup_kitchen()

    kitchen.queue_orders()
    key_lens = len(kitchen.redis_store.keys())

    kitchen.remove_expiring_order({
        'temp': 'cold'
    })

    new_key_lens = len(kitchen.redis_store.keys())
    assert new_key_lens < key_lens


def test_optimize_overflow_shelf():
    kitchen = setup_kitchen()

    kitchen.queue_orders()
    key_lens = len(kitchen.redis_store.keys())

    kitchen.optimize_overflow_shelf()
    new_key_lens = len(kitchen.redis_store.keys())

    assert key_lens == new_key_lens

    kitchen.redis_store.flushdb()

    order = {}
    order['id'] = '1'
    order['redisKey'] = 'overflow:cold:1'
    order["expirationAge"] = "1"
    order["temp"] = "cold"
    order["shelfLife"] = 100
    order["decayRate"] = .5

    kitchen.redis_store.hmset(order['redisKey'], order)
    kitchen.optimize_overflow_shelf()

    assert len(kitchen.redis_store.keys('overflow*')) == 0
    assert len(kitchen.redis_store.keys('cold*')) >= 0
