import scrapy
from datetime import datetime
from cde.items import article_item
from logging import warning


class JnauSpider(scrapy.Spider):
    name = 'cde_spider'
    start_urls = ['http://jsj.journal.cssc709.net/CN/article/showOldVolumn.do']

    def parse(self, response):

        #Change needed: search for td tag insted of the direct link (a tag).

        for a in response.css("a.J_WenZhang:contains('No.')"):
            next_url = f'http://jsj.journal.cssc709.net/CN{a.attrib["href"].replace("..", "")}'
            i_n = a.css("::text").get().split(".")[1].replace("0", "")

            issue_number = {"issue_number":i_n}

            yield scrapy.Request(next_url, callback=self.parse_issue_page, cb_kwargs=issue_number)

    def parse_issue_page(self, response, issue_number):
        for article_url in response.css('a[href*="abstract/abstract"]::attr(href)').getall():
            url = f'http://jsj.journal.cssc709.net/CN{article_url.replace("..","")}'
            issue_number = {"issue_number":issue_number}

            yield scrapy.Request(url, callback=self.parse_article, cb_kwargs=issue_number)
    
    def parse_article(self, response, issue_number):

        def parse_date(tag):

            date = None

            for text in tag:

                if "-" in text:

                    date = text.split("\r")[0].strip()

                    break

            return date

        try:

            item = article_item()

            item['html_to_ingest'] = response.body.decode('utf-8')
            
            item['pdf_to_download'] = response.css('meta[name=citation_pdf_url]::attr(content)').get()
                
            item['original_link'] = response.url
            
            item['issue_number'] = issue_number

            dates = response.css("td.J_zhaiyao[height='25']::text").getall()

            try:
                
                item['year_number'] = parse_date(dates).split("-")[0]

                item['publish_date'] = datetime.strptime(parse_date(dates), '%Y-%m-%d').date()

            except Exception as e:

                item['year_number'] = None

                item['publish_date'] = None


            item['title'] = response.css("span.J_biaoti::text").get()
            
            try:

                item['article_number'] = response.css("span.txt_zhaiyao::text").get().split("\\")[0].strip()

            except Exception:

                item['article_number'] = None

            try:

                item['authors'] = response.css("td.J_zhaiyao_en::text").get().split(".")[0].replace("\r", "").replace("\n", "").replace("\t", "")

            except Exception:

                item['authors'] = None

            item['abstract'] = None

            yield item

        except Exception as e:

            warning(f"There's been a problem scraping the article: {response.url}, exception: {e}")