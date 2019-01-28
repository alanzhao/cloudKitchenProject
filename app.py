from kitchen import Kitchen
from flask import Flask, Response
from helpers import stream_template
import redis

app = Flask(__name__)
app.config.from_mapping(
    LAMBDA=3.25,
    REDIS_HOST='localhost',
    REDIS_PORT=6379,
    REDIS_DB=0,
    HOT_SHELF_SIZE=15,
    COLD_SHELF_SIZE=15,
    FROZEN_SHELF_SIZE=15,
    OVERFLOW_SHELF_SIZE=20,
    JSON_FILE='orders.json'
)

redis_store = redis.Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'],
                          encoding='utf-8', decode_responses=True)

# clear out the db so each run is independent
redis_store.flushdb()


@app.route('/orders/stream')
def stream_orders():
    kitchen = Kitchen(app, redis_store)
    return Response(stream_template(app, 'index.html', data=kitchen.stream_orders()))


@app.route('/orders/queue')
def queue_orders():
    kitchen = Kitchen(app, redis_store)
    size = kitchen.queue_orders()

    return str(size) + 'Orders queued'


if __name__ == '__main__':
    app.run(debug=True)
