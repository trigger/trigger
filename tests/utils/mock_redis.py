# -*- coding: utf-8 -*-

"""
A mock py-redis (Redis) object for use in offline testing.

Licensed from John DeRosa, Source: http://bit.ly/19Lmnxx
Modified for Trigger by Jathan McCollum
"""
__all__ = ('Redis', 'MockRedis', 'install')


from collections import defaultdict
import re
import sys

class MockRedisLock(object):
    """
    Poorly imitate a Redis lock object so unit tests can run on our Hudson CI
    server without needing a real Redis server.
    """
    def __init__(self, redis, name, timeout=None, sleep=0.1):
        """Initialize the object."""
        self.redis = redis
        self.name = name
        self.acquired_until = None
        self.timeout = timeout
        self.sleep = sleep

    def acquire(self, blocking=True):  # pylint: disable=R0201,W0613
        """Emulate acquire."""
        return True

    def release(self):   # pylint: disable=R0201
        """Emulate release."""
        return None

class MockRedisPipeline(object):
    """
    Imitate a redis-python pipeline object so unit tests can run on our Hudson
    CI server without needing a real Redis server.
    """
    def __init__(self, redis):
        """Initialize the object."""
        self.redis = redis

    def execute(self):
        """
        Emulate the execute method. All piped commands are executed immediately
        in this mock, so this is a no-op.
        """
        pass

    def delete(self, key):
        """Emulate a pipelined delete."""

        # Call the MockRedis' delete method
        self.redis.delete(key)
        return self

    def srem(self, key, member):
        """Emulate a pipelined simple srem."""
        self.redis.redis[key].discard(member)
        return self

class MockRedis(object):
    """
    Imitate a Redis object so unit tests can run on our Hudson CI server without
    needing a real Redis server.
    """
    # The 'Redis' store
    redis = defaultdict(dict)

    def __init__(self):
        """Initialize the object."""
        pass

    def delete(self, key):  # pylint: disable=R0201
        """Emulate delete."""
        if key in MockRedis.redis:
            del MockRedis.redis[key]

    def exists(self, key):  # pylint: disable=R0201
        """Emulate get."""
        return key in MockRedis.redis

    def get(self, key):  # pylint: disable=R0201
        """Emulate get."""
        # Override the default dict
        result = '' if key not in MockRedis.redis else MockRedis.redis[key]
        return result

    def hget(self, hashkey, attribute):  # pylint: disable=R0201
        """Emulate hget."""
        # Return '' if the attribute does not exist
        result = MockRedis.redis[hashkey].get(attribute, '')
        return result

    def hgetall(self, hashkey):  # pylint: disable=R0201
        """Emulate hgetall."""
        return MockRedis.redis[hashkey]

    def hlen(self, hashkey):  # pylint: disable=R0201
        """Emulate hlen."""
        return len(MockRedis.redis[hashkey])

    def hmset(self, hashkey, value):  # pylint: disable=R0201
        """Emulate hmset."""
        # Iterate over every key:value in the value argument.
        for attributekey, attributevalue in value.items():
            MockRedis.redis[hashkey][attributekey] = attributevalue

    def hset(self, hashkey, attribute, value):  # pylint: disable=R0201
        """Emulate hset."""
        MockRedis.redis[hashkey][attribute] = value

    def keys(self, pattern):  # pylint: disable=R0201
        """Emulate keys."""

        # Make a regex out of pattern. The only special matching character we look for is '*'
        regex = '^' + pattern.replace('*', '.*') + '$'

        # Find every key that matches the pattern
        result = [key for key in MockRedis.redis.keys() if re.match(regex, key)]

        return result

    def lock(self, key, timeout=0, sleep=0):  # pylint: disable=W0613
        """Emulate lock."""
        return MockRedisLock(self, key)

    def pipeline(self):
        """Emulate a redis-python pipeline."""
        return MockRedisPipeline(self)

    def sadd(self, key, value):  # pylint: disable=R0201
        """Emulate sadd."""
        # Does the set at this key already exist?
        if key in MockRedis.redis:
            # Yes, add this to the set
            if value in MockRedis.redis[key]:
                return False
            MockRedis.redis[key].add(value)
        else:
            # No, override the defaultdict's default and create the set
            MockRedis.redis[key] = set([value])
        return True

    def srem(self, key, value):
        """Emulate srem."""
        # Does the set at this key already exist?
        if key in MockRedis.redis:
            # Yes, remove it from the set
            if value in MockRedis.redis[key]:
                MockRedis.redis[key].discard(value)
                return True
        return False

    def smembers(self, key):  # pylint: disable=R0201
        """Emulate smembers."""
        return MockRedis.redis[key]

    def save(self):
        """Emulate save"""
        return True

class Redis(MockRedis):
    """Redis object that supports kwargs"""
    def __init__(self, **kwargs):
        super(Redis, self).__init__()
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

def install():
    """Install into sys.modules as the Redis module"""
    for mod in ('redis', 'utils.mock_redis'):
        sys.modules.pop(mod, None)
    __import__('utils.mock_redis')
    sys.modules['redis'] = sys.modules['utils.mock_redis']
