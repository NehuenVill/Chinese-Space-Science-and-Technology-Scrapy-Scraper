import scrapy
from datetime import datetime
from csst.items import MySpiderItem 

class MySpider(scrapy.Spider):
    name = 'my_spider'
    start_urls = ['http://journal26.magtechjournal.com/kjkxjs/CN/article/showOldVolumnSimple.do']

    def parse(self, response):
        for link in response.css('a::attr(href)').extract()[0:2]:
            next_url = f'http://journal26.magtechjournal.com/kjkxjs/CN{link.replace("..", "")}'
            yield scrapy.Request(next_url, callback=self.parse_issue_page)

    def parse_issue_page(self, response):
        for article_url in response.css('a.txt_biaoti::attr(href)').extract()[0:6]:
            yield scrapy.Request(article_url, callback=self.parse_article)

    def parse_article(self, response):

        item = MySpiderItem()

        item['html_to_ingest'] = response.body.decode('utf-8')
        
        item['pdf_to_download'] = "http://journal26.magtechjournal.com/kjkxjs//CN/article/downloadArticleFile.do?attachType=PDF&id=" + response.css('a.black-bg.btn-menu::attr("onclick")').\
        extract_first().\
        split(",")[1].\
        replace("'", "")
        
        item['original_link'] = response.url
        
        item['issue_number'] = response.css('div.col-md-12 p span a:contains("Issue")::text').extract_first().\
        split("(")[1].\
        replace(")", "")
        
        item['year_number'] = response.css('ul.list-unstyled.code-style li span:contains("出版日期:")::text').extract_first().\
        replace("出版日期:", "").\
        strip().\
        split("-")[0]
        
        item['title'] = response.css('h3.abs-tit::text').extract_first()
        
        item['article_number'] = response.css('div.col-md-12 p span::text').extract_first().\
        split(":")[-1].\
        replace(".", "").\
        strip()
        
        item['publish_date'] = self.extract_publish_date(response)
        
        item['authors'] = response.css('p.collapsed span::text').extract_first()
        
        item['abstract'] = response.css('div.panel-body.line-height.text-justify p::text').extract_first() + "\n\n" + response.css('div.panel-body.line-height.text-justify form[name="refForm"]::text').extract_first() 

        yield item

    def extract_publish_date(self, response):
        date_str = response.css('ul.list-unstyled.code-style li span:contains("出版日期:") + span::text').extract_first().\
        replace("出版日期:", "").\
        strip()

        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return date_str
