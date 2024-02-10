# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class article_item(scrapy.Item):
    
    html_to_ingest = scrapy.Field()
    pdf_to_download = scrapy.Field()
    original_link = scrapy.Field()
    issue_number = scrapy.Field()
    year_number = scrapy.Field()
    title = scrapy.Field()
    article_number = scrapy.Field()
    publish_date = scrapy.Field()
    authors = scrapy.Field()
    abstract = scrapy.Field()
