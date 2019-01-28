from driver import Driver
from flask import Flask
import redis


def test_dispatch():
    app = Flask(__name__)
    redis_store = redis.Redis(host='localhost', port=6379, db=0, encoding='utf-8', decode_responses=True)

    driver = Driver(redis_store, app)
    order = {"redisKey": 1}
    driver.dispatch(order)

    redis_store.hmset(order['redisKey'], order)
    assert driver.key_to_delete == 1


def test_remove_order():
    app = Flask(__name__)
    redis_store = redis.Redis(host='localhost', port=6379, db=0, encoding='utf-8', decode_responses=True)

    driver = Driver(redis_store, app)
    order = {"redisKey": "abc"}
    redis_store.hmset(order['redisKey'], order)

    driver.dispatch(order)
    driver.remove_order()

    assert not redis_store.exists("abc")
