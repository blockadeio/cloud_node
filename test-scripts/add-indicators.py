"""Simple toy script to generate mock data for Blockade load tests."""
import hashlib
import json
import random
import requests
import string
import sys

CLOUD_HOST = "--YOUR-HOST--"
CLOUD_USER = "--YOUR-USER--"
CLOUD_KEY = "--YOUR-API-KEY--"


def id_generator(size=6, chars=string.ascii_lowercase):
    """Generate a random string."""
    return ''.join(random.choice(chars) for _ in range(size))


def gen_md5_urls(amount):
    """Generate a bunch of fake domains."""
    urls = list()
    for i in range(0, amount):
        rando = "{core}.com".format(core=id_generator(size=15))
        if rando[0].isdigit():
            rando = rando[1:]
        urls.append(hashlib.md5(rando).hexdigest())
    return list(set(urls))


def post_indicators(indicators):
    """Send indicators to the blockade cloud node."""
    headers = {'Content-Type': 'application/json'}
    data = {'indicators': indicators, 'email': CLOUD_USER,
            'api_key': CLOUD_KEY}
    url = "http://{}/admin/add-indicators".format(CLOUD_HOST)
    try:
        args = {'url': url, 'headers': headers, 'data': json.dumps(data),
                'timeout': 120}
        response = requests.post(**args)
    except Exception, e:
        raise Exception("Error Posting: %s" % str(e))
    if response.status_code not in range(200, 299):
        raise Exception("Error: {}".format(response.content))
    loaded = json.loads(response.content)
    return loaded


def main():
    """Input fake URLs for testing."""
    if len(sys.argv) < 2:
        print("Usage: python add-indicators.py <amount>")
        sys.exit(1)
    amount = int(sys.argv[1])
    test_domains = gen_md5_urls(amount)
    print(post_indicators(test_domains))


if __name__ == "__main__":
    main()
