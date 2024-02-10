import scrapy
from datetime import datetime
from jnau.items import article_item
from logging import warning


class JnauSpider(scrapy.Spider):
    name = 'jnau_spider'
    start_urls = ['http://hjhyxb.ijournals.cn/hjhkgcx/issue/get_year_info?_=1707534609618']

    def parse(self, response):
        
        all_years = response.text.split("#")

        years = {"years": all_years}

        yield scrapy.Request("http://hjhyxb.ijournals.cn/hjhkgcx/issue/get_all_issue_info?_=1707534609620", callback=self.parse_issue_page, cb_kwargs=years)

    def parse_issue_page(self, response, years):

        all_issues = response.text.split("><")

        issues = {i.split(">")[0].replace("<",""):i.split(">")[1].split("<")[0] for i in all_issues}

        for year in years:

            base_url = "http://hjhyxb.ijournals.cn/hjhkgcx/article/issue/"

            try:

                y,v = year.split(",")

            except Exception:

                y = year.replace(",", "")

                v = None

            try:

                iss = issues[y].split(":")

            except Exception as e:

                continue

            for i in iss:

                issue = i.split(",")[0]

                if v:

                    url = f"{base_url}{y}_{v}_{issue}"

                else:

                    url = f"{base_url}{y}_{issue}"

                issue_number = {"issue_number":issue}

                yield scrapy.Request(url, callback=self.parse_all_article_url, cb_kwargs=issue_number)

    def parse_all_article_url(self, response, issue_number):

        for href in response.css("div.article_title a"):

            base_url = "http://hjhyxb.ijournals.cn/"

            article_url = f"{base_url}{href.attrib['href']}"
            issue_number = {"issue_number":issue_number}

            yield scrapy.Request(article_url, callback=self.parse_article, cb_kwargs=issue_number)

    def parse_article(self, response, issue_number):

        try:

            item = article_item()

            item['html_to_ingest'] = response.body.decode('utf-8')
            
            try:

                item['pdf_to_download'] = response.css("a#PdfUrl").attrib["href"]

            except Exception:

                item['pdf_to_download'] = None
                
            item['original_link'] = response.url
            
            item['issue_number'] = issue_number

            date = response.css("span#PublishTimeValue::text").get()

            item['year_number'] = date.split("-")[0]

            item['publish_date'] = datetime.strptime(date, '%Y-%m-%d').date()

            t_en = response.css("div.en div.title::text").get()

            t_ch = response.css("div.zh div.title::text").get()

            if t_ch and t_en:

                item['title'] = t_ch + " \n " + t_en

            elif t_ch:

                item['title'] = t_ch

            elif t_en:

                item['title'] = t_en

            else:

                item['title'] = None
            
            try:

                item['article_number'] = response.css("span#all_issue_position::text").getall()[1].split(".")[0].replace(">", "").strip()

            except Exception as e:

                item['article_number'] = None

            item['authors'] = None #in the search of another way of scraping them since they are dynamically loaded.

            abs_ch = response.css("p#CnAbstractValue::text").get()

            abs_en =  response.css("p#EnAbstractValue::text").get()

            if abs_ch and abs_en:

                item['abstract'] = abs_ch + " \n " + abs_en

            elif abs_ch:

                item['abstract'] = abs_ch

            elif abs_en:

                item['abstract'] = abs_en

            else:

                item['abstract'] = None

            yield item
        
        except Exception as e:

            warning(f"There's been a problem scraping the article: {response.url}, exception: {e}")