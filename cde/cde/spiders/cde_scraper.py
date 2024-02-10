import scrapy
from datetime import datetime
from cde.items import article_item
from logging import warning


class JnauSpider(scrapy.Spider):
    name = 'jnau_spider'
    start_urls = ['http://jsj.journal.cssc709.net/CN/article/showOldVolumn.do']

    def parse(self, response):

        #Change needed: search for td tag insted of the direct link (a tag).

        for a in response.css('a.J_WenZhang'):
            next_url = f'http://jsj.journal.cssc709.net/CN{a.attrib["href"].replace("..", "")}'
            i_n = a.css("::text").get().split(".")[1].replace("0", "")

            issue_number = {"issue_number":i_n}

            yield scrapy.Request(next_url, callback=self.parse_issue_page, cb_kwargs=issue_number)