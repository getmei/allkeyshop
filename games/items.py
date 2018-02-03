# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class GamesItem(scrapy.Item):
    Name_Of_Game = scrapy.Field()	
    Category = scrapy.Field()
    User_Rating = scrapy.Field()
    Release_Date = scrapy.Field()
    Shops = scrapy.Field()
    URL = scrapy.Field()
    Votes = scrapy.Field()