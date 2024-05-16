import scrapy
from datetime import datetime
from csst.items import article_item 

class CsstSpider(scrapy.Spider):
    name = 'csst_spider'
    start_urls = ['http://journal26.magtechjournal.com/kjkxjs/CN/article/showOldVolumnSimple.do']

    def parse(self, response):
        for a in response.css('a'):
            next_url = f'http://journal26.magtechjournal.com/kjkxjs/CN{a.attrib["href"].replace("..", "")}'
            i_n = a.css("::text").get().split(".")[1].replace("0", "")
            issue_number = i_n
            yield scrapy.Request(next_url, callback=self.parse_issue_page, meta={"issue_number": issue_number})

    def parse_issue_page(self, response):
        for i,article_url in enumerate(response.css('a.txt_biaoti::attr(href)').extract()[1:2]):
            yield scrapy.Request(article_url, callback=self.get_article_details, meta={"issue_number": response.meta["issue_number"], "article_number":i+1})

    def get_article_details(self, response):

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
            abstracts = []
            for abs in tag: 
                if  "\r" not in abs and "\n" not in abs and "\t" not in abs:
                    abstracts.append(abs)
            return abstracts[0] + "\n\n" + abstracts[1]

        item = article_item()
        item['journal_name'] = "Chinese_Space_Science_and_Technology"
        item['html_to_ingest'] = response.body.decode('utf-8')
        item['pdf_to_download'] = response.css("meta[name='citation_pdf_url']::attr('content')").get()
        item['original_link'] = response.url
        item['issue_number'] = response.meta["issue_number"]
        dates = response.css('ul.list-unstyled.code-style li span').getall()
        item['year_number'] = parse_date(dates).split("-")[0]
        item['publish_date'] = datetime.strptime(parse_date(dates), '%Y-%m-%d').date()
        item['title'] = response.css('h3.abs-tit::text').extract_first()
        item['article_number'] = response.meta["article_number"]
        item['authors'] = response.css("meta[name='citation_authors']::attr('content')").get().split(",")
        abstract_tag = response.css('div.panel-body.line-height.text-justify p::text').getall()
        item['abstract'] = parse_abstract(abstract_tag)
        yield item