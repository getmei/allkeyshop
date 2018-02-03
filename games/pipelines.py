from elasticsearch import Elasticsearch, helpers
import json
import hashlib
import types
import logging
from datetime import datetime


class GamesPipeline(object):

    items_buffer = []

    def __init__(self):
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    @staticmethod
    def get_unique_key(item):
        key = item['URL'].encode('utf-8')
        key = hashlib.sha1(key).hexdigest()
        return key

    def index_item(self, item):

        index_action = {
            '_index': 'games',
            '_type': 'game_keys',
            '_source': dict(item),
            '_id': self.get_unique_key(item)
        }

        self.items_buffer.append(index_action)

        if len(self.items_buffer) >= 200:
            self.send_items()
            print("200 added  - ".format(x=len(self.items_buffer)), datetime.now().time())
            self.items_buffer = []

    def send_items(self):
        helpers.bulk(self.es, self.items_buffer)

    def process_item(self, item, spider):
        if isinstance(item, types.GeneratorType) or isinstance(item, list):
            for each in item:
                self.process_item(each, spider)
        else:
            self.index_item(item)
            logging.debug('Item sent to ElasticSearch job_items')
            return item

    def close_spider(self, spider):
        if len(self.items_buffer):
            print("{x} added  - ".format(x=len(self.items_buffer)), datetime.now().time())
            self.send_items()


