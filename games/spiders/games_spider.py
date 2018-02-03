import scrapy
from scrapy import Selector
import requests
import json
from games.items import GamesItem
from games.notify import notify_slack
from scrapy import signals
from datetime import datetime, date
import urllib.parse as urlparse


class GamesSpider(scrapy.Spider):
    name = "games"
    start = datetime.now()
    count = 0
    page_count = 0 

    def start_requests(self):
        yield scrapy.Request(url="http://www.allkeyshop.com/catalogue/allpcgames.php?q&page=5000000&sort=releasedateDesc", callback=self.get_page)

    def get_page(self, response):
        sel = Selector(response=response)
        url = sel.xpath("//div[@class='navigation']/a/@href").extract()[-1]
        p = response.urljoin(url)
        parsed = urlparse.urlparse(url)
        page = urlparse.parse_qs(parsed.query)['page'][0]
        url = "http://www.allkeyshop.com/catalogue/allpcgames.php?q&page="
        after_page_url = "&sort=releasedateDesc"
        for i in range(1, int(page) + 1):
            yield scrapy.Request(url=url+str(i)+after_page_url, callback=self.parse)

    def parse(self, response):
        self.page_count += 1
        sel = Selector(response=response)
        url = sel.xpath("//div[@class='searchresults']/table/tr/td/a/@href").extract()
        game_name = sel.xpath("//div[@class='searchresults']/table/tr[*]/td[2]/text()").extract()
        for n, _ in enumerate(url):
            url_in_es = "http://localhost:9200/games/_search/?q=URL:" + '\"' + url[n] + '\"'
            r = requests.get(url_in_es)
            r = r.content.decode('utf8')
            jsn = json.loads(r)
            try:
                if jsn['hits']['hits'][0]['_source']['URL']:
                    pass
            except:
                yield scrapy.Request(url=url[n].strip(), callback=self.parse_content,
                                     meta={'game_name': game_name[n].strip()})

    @staticmethod
    def check_availability(stock):
        if stock == 'in_stock':
            return "True"
        else:
            return "False" 

    def parse_content(self, response):
        item = GamesItem()
        price_map = dict()

        sel = Selector(response=response)
        shops = sel.xpath("//tr[@itemprop='offerDetails']/td[1]/a/@title").extract()
        prices = sel.xpath("//tr[@itemprop='offerDetails']/td[5]")
        availability = sel.xpath("//td[@itemprop='availability']/@content").extract()
        user_rating = sel.xpath("//span[@itemprop='rating']/text()").extract_first()
        category = sel.xpath("//li[contains(text(), 'Genre(s)')]/a/text()").extract()
        release_date = sel.xpath("//li[contains(text(), 'Release Date')]/text()").extract_first()
        votes = sel.xpath("//span[@itemprop='votes']/text()").extract_first()
        try:
            dym = release_date.strip()    
            dd = dym[14:].replace('/', '-')
            y, m, d = dd[6:], dd[:2], dd[3:5]
            date_list = [y, m, d]
            s = '-'.join(date_list)
            release_date = datetime.strptime(s, '%Y-%m-%d').strftime("%Y-%m-%d")
        except:
            release_date = date.today().strftime('%Y-%m-%d')

        if not category:
            category = ["Unspecified"]
        if user_rating is None:
            user_rating = 0
        else:
            user_rating = float(user_rating)

        if votes is None:
            votes = 0
        else:
            votes = float(votes)

        global shop_name
        shop_name = ''

        for i in range(len(shops)):
            if '.' in shops[i]:
                sh_name = shops[i].strip()
                shop_name = sh_name[:sh_name.index('.')]
            else:
                shop_name = shops[i].strip()
            if prices[i].css("div[class=prix] strong::text").extract():
                pr = prices[i].css("div[class=prix] strong::text").extract_first()
                percent = pr[1:pr.index("%")]
                try:
                    discounted = float(float(prices[i].css(
                                                         "span[itemprop=price]::attr(content)").extract_first()) * (
                                                                   100 - float(percent)) / 100)

                    stock = self.check_availability(availability[i])
                    price_map["shop_" + shop_name] = {"price_" + shop_name: float("%.2f"%discounted), shop_name + "_discount": pr, 'stock_' + shop_name: stock}
                except:
                    stock = self.check_availability(availability[i])
                    price_map["shop_" + shop_name] = {"price_" + shop_name: float(prices[i].css("span[itemprop=price]::attr(content)").extract_first()), 
                                                    shop_name + "_discount": pr, 'stock_' + shop_name: stock}
            else:
                stock = self.check_availability(availability[i])
                price_map["shop_" + shop_name] = {"price_" + shop_name: float(prices[i].css("strong[itemprop=price]::attr(content)").extract_first()), 
                                                "stock_" + shop_name: stock}

        item['Shops'] = price_map
        item['Category'] = category
        item['User_Rating'] = user_rating
        item['Name_Of_Game'] = response.meta['game_name']
        item['Release_Date'] = release_date
        item['URL'] = response.url
        item["Votes"] = votes

        self.count += 1
        yield item

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(GamesSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        crawler.signals.connect(spider.spider_opened, signals.spider_opened)
        return spider

    # do stuff after spider closes
    def spider_closed(self, spider):
        notify_slack(" ")
        notify_slack("**************************************************************")
        notify_slack("Finished in {x}".format(x=str(datetime.now() - self.start)))
        notify_slack("{x} items were added in ElasticSearch".format(x=self.count))
        notify_slack("Crawled {x} pages".format(x=self.page_count))

    # do stuff when spider starts
    def spider_opened(self, spider):
        notify_slack("[----STARTED----]")
