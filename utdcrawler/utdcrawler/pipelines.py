# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import pymongo

class MongoPipeline:
    def open_spider(self, spider):
        self.client = pymongo.MongoClient(spider.settings.get("MONGO_URI"))
        self.db = self.client[spider.settings.get("MONGO_DATABASE")]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db.pages.insert_one(dict(item))
        return item