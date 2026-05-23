import redis
import os

r = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

def get_cached_response(key):
    return r.get(key)

def set_cached_response(key, value):
    r.set(key, value, ex=3600)
