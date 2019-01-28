from helpers import load_data
from driver import Driver
import numpy as np
import time
import uuid
import random


class Kitchen():
    def __init__(self, app, redis_store):
        self.app = app
        self.redis_store = redis_store

    def stream_orders(self):

        previous_orders = []

        while True:
            orders = []

            for key in self.redis_store.keys():
                order = self.redis_store.hgetall(key)
                orders.append(order)

            # if orders changes, stream the change to frontend
            if self.did_orders_change(orders, previous_orders):
                previous_orders = orders

                yield self.group_orders(orders)
            else:
                previous_orders = orders

            # check changes every second
            time.sleep(1)

    def did_orders_change(self, orders, previous_orders):
        if len(orders) != len(previous_orders):
            # if size changes, see if we can move item from overflow shelf to regular shelf
            self.optimize_overflow_shelf()

            return True
        elif set([order['id'] for order in orders]) != set([order['id'] for order in previous_orders]):
            return True
        else:
            return False

    def group_orders(self, orders):
        grouped_orders = {
            'hot': [],
            'cold': [],
            'frozen': [],
            'overflow': [],
        }

        # calculate the corresponding attributes for each order for displaying in the frontend
        for order in orders:
            order['currentAge'] = int(order['expirationAge']) - self.redis_store.ttl(order['redisKey'])

            if order['redisKey'].lower().startswith('overflow'):
                order['normalizedValue'] = (int(order['shelfLife']) - int(order['currentAge']) - 2.0 * float(
                    order['decayRate']) * int(order['currentAge'])) / int(order['shelfLife'])

                if order['normalizedValue'] <= 0:
                    self.redis_store.delete(order['redisKey'])
                else:
                    grouped_orders['overflow'].append(order)
            else:
                order['normalizedValue'] = (int(order['shelfLife']) - int(order['currentAge']) - float(
                    order['decayRate']) * int(order['currentAge'])) / int(order['shelfLife'])

                if order['normalizedValue'] <= 0:
                    self.redis_store.delete(order['redisKey'])
                else:
                    grouped_orders[order['temp'].lower()].append(order)

        return grouped_orders

    def queue_orders(self):
        orders = load_data(self.app.config["JSON_FILE"])
        order_size = len(orders)
        sample_size = round(order_size * self.app.config['LAMBDA'])
        samples = np.random.poisson(self.app.config['LAMBDA'], sample_size)

        # assign uuid to each order
        for order in orders:
            order['id'] = str(uuid.uuid4())

            # expiration time in seconds if sitting on a regular shelf
            order['expirationAge'] = round(order['shelfLife'] * 1.0 / (1 + order['decayRate']))

            # expiration time in seconds if sitting on a overflow shelf
            order['shortenedExpirationAge'] = round(order['shelfLife'] * 1.0 / (1 + 2 * order['decayRate']))

            # record order accept time
            order['acceptedAt'] = round(time.time())

        for sample in samples:
            if sample > 0:
                orders_in_a_second = orders[0:sample]
                orders = orders[sample:]

                # sequentially process each order
                if len(orders_in_a_second) > 0:

                    for order in orders_in_a_second:
                        self.process_order(order)
                else:
                    break

            # sleep 1 second for the poisson distribution
            time.sleep(1)

        return order_size

    def process_order(self, order):
        overflow = False

        # check which shelf to put the item
        temp = order['temp'].lower()
        if len(self.redis_store.keys(pattern=temp + '*')) < self.app.config[temp.upper() + '_SHELF_SIZE']:
            order['redisKey'] = temp + ':' + order['id']
            self.redis_store.hmset(order['redisKey'], order)
            self.redis_store.expire(order['redisKey'], order['expirationAge'])

            driver = Driver(self.redis_store, self.app)
            driver.dispatch(order)
        else:
            overflow = True

        # see if we can place it into overflow
        if overflow:
            overflow = False

            if len(self.redis_store.keys(pattern='overflow*')) < self.app.config['OVERFLOW_SHELF_SIZE']:
                order['redisKey'] = 'overflow:' + order['temp'].lower() + ':' + order['id']
                order['expirationAge'] = order['shortenedExpirationAge']

                self.redis_store.hmset(order['redisKey'], order)
                self.redis_store.expire(order['redisKey'], order['shortenedExpirationAge'])

                driver = Driver(self.redis_store, self.app)
                driver.dispatch(order)
            else:
                overflow = True

            # if overflow shelf is full
            # remove the order that is expiring soon
            # find the item with least time to live and replace it with current order
            # then recursively call self
            if overflow:
                self.remove_expiring_order(order)
                self.process_order(order)

    def remove_expiring_order(self, order_to_add):
        # first select all orders from the shelf with same temp
        keys = self.redis_store.keys(pattern=order_to_add['temp'].lower() + '*')

        # also select overflow shelf
        keys.extend(self.redis_store.keys(pattern='overflow*'))

        key_to_remove = ''

        for key in keys:
            if key_to_remove == '':
                key_to_remove = key
            elif self.redis_store.ttl(key) < self.redis_store.ttl(key_to_remove):
                key_to_remove = key

        if key_to_remove != '':
            self.redis_store.delete(key_to_remove)

    # remove one item from overflow shelf if possible
    def optimize_overflow_shelf(self):
        # goal is to remove 1 item from overflow shelf and put it back to a regular shelf to prolong the life
        keys = self.redis_store.keys(pattern='overflow*')

        if len(keys) > 0:
            index = random.randint(0, len(keys) - 1)
            key = keys[index]
            order = self.redis_store.hgetall(key)

            # key is in this format: overflow:cold:uuid
            temp = key.split(':')[1]
            new_redis_key = key[9:]

            # move pack only if there's space
            if len(self.redis_store.keys(pattern=temp + '*')) < self.app.config[temp.upper() + '_SHELF_SIZE']:
                # move it to *new* shelf by renaming the key
                self.redis_store.delete(key)

                # convert to int and float
                order['shelfLife'] = int(order['shelfLife'])
                order['decayRate'] = float(order['decayRate'])
                order['acceptedAt'] = round(time.time())
                order['currentAge'] = 0
                order['redisKey'] = new_redis_key

                # get current value, which will become the new shelfLife
                current_value = round(order['shelfLife'] - order['currentAge'] - (
                        2.0 * order['decayRate'] * order['currentAge']))
                order['shelfLife'] = current_value

                # expiration time in seconds if sitting on a regular shelf
                order['expirationAge'] = round(order['shelfLife'] * 1.0 / (1 + order['decayRate']))

                # expiration time in seconds if sitting on a overflow shelf
                order['shortenedExpirationAge'] = round(order['shelfLife'] * 1.0 / (1 + 2 * order['decayRate']))

                self.redis_store.hmset(order['redisKey'], order)
                self.redis_store.expire(order['redisKey'], order['expirationAge'])
        pass
