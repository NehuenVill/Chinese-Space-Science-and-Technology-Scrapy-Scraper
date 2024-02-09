from inspect import trace
import scrapy
from datetime import datetime
from amt.items import article_item
import traceback
from logging import warn


class AmtSpider(scrapy.Spider):
    name = 'amt_spider'
    start_urls = ['https://www.yhclgy.com/yhclgy/issue/get_year_info?_=1707420395312']

    def parse(self, response):
        
        all_years = response.text.split("#")

        years = {"years": all_years}

        yield scrapy.Request("https://www.yhclgy.com/yhclgy/issue/get_all_issue_info?_=1707420395314", callback=self.parse_issue_page, cb_kwargs=years)

    def parse_issue_page(self, response, years):

        all_issues = response.text.split("><")

        issues = {i.split(">")[0].replace("<",""):i.split(">")[1].split("<")[0] for i in all_issues}

        for year in years:

            base_url = "https://www.yhclgy.com/yhclgy/article/issue/"

            try:

                y,v = year.split(",")

            except Exception:

                y = year.replace(",", "")

                v = None

            try:


                iss = issues[y].split(":")

            except Exception:

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

        base_url = "https://www.yhclgy.com/"

        for href in response.css("div.article_title a"):

            article_url = f"{base_url}{href.attrib['href']}"
            issue_number = {"issue_number":issue_number}

            yield scrapy.Request(article_url, callback=self.parse_article, cb_kwargs=issue_number)


    def parse_article(self, response, issue_number):

        def parse_date(spans) -> str:

            published_date = None

            for span in spans:

                if "出版日期:" in span:

                    published_date = span.split(":</code>")[1].split("<")[0].strip()

                    return published_date

            for span in spans:

                if "发布日期:" in span:

                    published_date = span.split(":</code>")[1].split("<")[0].strip()

                    return published_date

        def parse_authors(title_tag, abs_tag) -> str:

            authors_list = []

            for author in title_tag:

                auth = author.replace("\r\n", "").replace("\t", "").replace("，", "").replace(", ", "").strip()
                
                if len(auth)>0:                                
                
                    authors_list.append(auth)

            if len(authors_list) > 0:

                return ", ".join(authors_list)

            else:

                try:

                    auth_ch, auth_en = abs_tag.css("p::text").getall()[0], abs_tag.css("p::text").getall()[2]

                    return " - ".join((auth_ch, auth_en))

                except IndexError:

                    auths = []

                    for element in abs_tag.css("p::text").getall():

                        if "," in element and "." in element:

                            auth = element.split(".")[0]

                            auths.append(auth)

                    return " - ".join(auths)

        def parse_abstract(tag) -> str:

            try:

                abstracts = []
                
                for abs in tag: 
                    if  "\r" not in abs and "\n" not in abs and "\t" not in abs:
                        abstracts.append(abs)

                return abstracts[0] + "\n\n" + abstracts[1]

            except Exception:

                return response.css("div.primary-border p::text").get()

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

        item['title'] = response.css("div.zh div.title::text").get() + " - " + response.css("div.en div.title::text").get()
        
        try:

            item['article_number'] = response.css("span#all_issue_position::text").getall()[1].split(".")[0].replace(">", "").strip()

        except Exception as e:

            item['article_number'] = None

        item['authors'] = None #in the search of another way of scraping them since they are dynamically loaded.

        item['abstract'] = response.css("p#CnAbstractValue::text").get() + " \n " + response.css("p#EnAbstractValue::text").get()

        yield item