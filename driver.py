import random
import threading


class Driver():
    def __init__(self, redis_store, app):
        self.redis_store = redis_store
        self.app = app
        self.key_to_delete = ""

    def dispatch(self, order):
        # randomly delay pick up from 2 to 8 seconds
        delay = random.randint(2, 8)
        self.key_to_delete = order['redisKey']

        # this timer needs to be non-blocking with a callback
        timer = threading.Timer(delay, self.remove_order)
        timer.start()

    def remove_order(self):
        if self.redis_store.exists(self.key_to_delete):
            self.redis_store.delete(self.key_to_delete)
