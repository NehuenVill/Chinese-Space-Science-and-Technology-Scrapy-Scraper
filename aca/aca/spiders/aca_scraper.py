from inspect import trace
import scrapy
from datetime import datetime
from aca.items import MySpiderItem 
import traceback


class CsstSpider(scrapy.Spider):
    name = 'aca_spider'
    start_urls = ['http://journal01.magtech.org.cn/Jwk3_kjkzjs/CN/1674-1579/home.shtml']

    def parse(self, response):
        for a in response.css("table.table.table-striped.table-hover.table-bordered.text-center a"):
            next_url = f'http://journal01.magtech.org.cn/Jwk3_kjkzjs/CN{a.attrib["href"].replace("..", "")}'
            try:

                i_n = a.css("::text").get().split(".")[1].replace("0", "")

            except Exception:

                continue

            issue_number = {"issue_number":i_n}

            yield scrapy.Request(next_url, callback=self.parse_issue_page, cb_kwargs=issue_number)

    def parse_issue_page(self, response, issue_number):
        for article_url in response.css('a.biaoti::attr(href)').extract():
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

        item = MySpiderItem()

        item['html_to_ingest'] = response.body.decode('utf-8')
        
        try:

            item['pdf_to_download'] = "http://journal01.magtech.org.cn/Jwk3_kjkzjs/CN/article/downloadArticleFile.do?attachType=PDF&id=" + response.css('a.black-bg.btn-menu::attr("onclick")').\
            extract_first().\
            split(",")[1].\
            replace("'", "")

        except Exception:

            item['pdf_to_download'] = response.css("meta[name='citation_pdf_url']::attr('content')").get()
            
        item['original_link'] = response.url
        
        item['issue_number'] = issue_number

        dates = response.css('ul.list-unstyled.code-style li span').getall()

        item['year_number'] = parse_date(dates).split("-")[0]

        item['publish_date'] = datetime.strptime(parse_date(dates), '%Y-%m-%d').date()

        item['title'] = response.css('h3.abs-tit::text').extract_first()
        
        try:

            item['article_number'] = response.css('div.col-md-12 p span::text').getall()[3].\
            split(":")[-1].\
            replace(".", "").\
            strip()

        except Exception as e:

            trcb = traceback.format_exc()

            with open("spider_ex.json", "a") as f:

                f.write(f"Problem with: {response.url} => {trcb}\n ***********************\n")

            item['article_number'] = None

        title_auth = response.css('p[data-toggle="collapse"] span::text').getall()
            
        abs_auth = response.css('div.primary-border')[0]

        item['authors'] = parse_authors(title_auth, abs_auth)

        abstract_tag = response.css('div.panel-body.line-height.text-justify p::text').getall()

        item['abstract'] = parse_abstract(abstract_tag)

        yield item