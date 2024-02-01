import scrapy
from datetime import datetime
from csst.items import MySpiderItem 
import traceback


class MySpider(scrapy.Spider):
    name = 'my_spider'
    start_urls = ['http://journal26.magtechjournal.com/kjkxjs/CN/article/showOldVolumnSimple.do']

    def parse(self, response):
        for link in response.css('a::attr(href)').extract():
            next_url = f'http://journal26.magtechjournal.com/kjkxjs/CN{link.replace("..", "")}'
            yield scrapy.Request(next_url, callback=self.parse_issue_page)

    def parse_issue_page(self, response):
        for article_url in response.css('a.txt_biaoti::attr(href)').extract()[0:1]:
            yield scrapy.Request(article_url, callback=self.parse_article)

    def parse_article(self, response):

        try:

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

            published_date = None

            for span in response.css('ul.list-unstyled.code-style li span').getall():

                if "出版日期:" in span:

                    published_date = span.split(":</code>")[1].split("<")[0].strip()


            item['year_number'] = published_date.split("-")[0]

            item['publish_date'] = datetime.strptime(published_date, '%Y-%m-%d').date()
            
            item['title'] = response.css('h3.abs-tit::text').extract_first()
            
            item['article_number'] = response.css('div.col-md-12 p span::text').getall()[3].\
            split(":")[-1].\
            replace(".", "").\
            strip()
            
            authors_list = []

            for author in response.css('p[data-toggle="collapse"] span::text').getall():
                auth = author.replace("\r\n", "").replace("\t", "").replace("，", "").strip()
                if len(auth)>0:                                
                    authors_list.append(auth)

            item['authors'] = ", ".join(authors_list)

            abstracts = []
            
            for abs in response.css('div.panel-body.line-height.text-justify p::text').getall(): 
                if  "\r" not in abs and "\n" not in abs and "\t" not in abs:
                    abstracts.append(abs)

            item['abstract'] = abstracts[0] + "\n\n" + abstracts[1]

        except Exception as e:

            trcb = traceback.format_exc()

            with open("spider_ex.json", "a") as f:

                f.write(f"Problem with: {response.url} => {trcb}\n ***********************\n")

        yield item
