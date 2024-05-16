from datetime import datetime
import logging 
import re
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

required_fields = [
    'html_to_ingest',
    'pdf_to_download',
    'original_link',
    'issue_number',
    'year_number',
    'title',
    'article_number',
    'publish_date',
    'authors',
    ]

expected_field_types = {
    'html_to_ingest' : str,
    'pdf_to_download' : str,
    'original_link' : str,
    'issue_number' : str,
    'year_number' : str,
    'title' : str,
    'article_number' : int,
    'publish_date' : datetime,
    'authors' : list or None,
}

def log_friendly(item):
    '''
    removes fields from item that are too long for convenient logging.
    '''
    too_long_fields = ["pdf_bytes", "html_to_ingest", "additional_metadata_from_xml"]
    for field in too_long_fields:
        if item.get(field):
            item.pop(field, None)
    return(item)

def convert_date_string_to_datetime(date_str):
    '''
    attempts to convert a date string into a datetime object using multiple formats.
    returns None if conversion fails.
    '''
    parsed_date = None
    for date_format in ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            break 
        except ValueError:
            continue
    #if it's just a year (YYYY), assume January 1st of that year
    if parsed_date is None and len(date_str) == 4 and date_str.isdigit():
        try:
            parsed_date = datetime(int(date_str), 1, 1)
        except ValueError:
            pass  #in case of error, nothing changes
    return parsed_date

def is_valid_url(url: str) -> bool:
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)  # path
    # print(f"Testing URL: '{url}'")  #this helps ensure the URL is as expected
    return re.match(regex, url.strip()) is not None

def process_error(item, error_level, spider=None, message=None):
    '''
    handles error logging and actions based on error severity levels.
    can trigger spider shutdown or item drop.
    '''
    error_shutdown_threshold = 1
    error_pop_threshold = 2

    if error_level >= error_shutdown_threshold:
        logger.error(message)
        logger.error("Shutdown level error encountered, Triggering spider shutdown. Additional clean-up is expected; handling the close of the spider requires the existing item queue to be cleared out and in-flight messages handled.")        
        item = log_friendly(item)
        raise DropItem("DROPPING ITEM: ERROR_SHUTDOWN_THRESHOLD exceeded.")
    
    elif error_level >= error_pop_threshold:
        error_level_indicator = error_pop_threshold + 1
        detailed_error_message = f"DROPPING ITEM: Process Error at level {error_level_indicator}: {message}"
        logger.error(detailed_error_message)

        item = log_friendly(item)
        raise DropItem(f"DROPPING ITEM: Exceeded ERROR_POP_THRESHOLD (level {error_level_indicator})")
    
    else:
        filtered_message = f"Warning: {message}"
        logger.warning(filtered_message)
        pass

class ItemValidation:
    def open_spider(self, spider):
        '''
        initializes error flag and Redis client for the spider.
        optionally flushes Redis database.
        '''
        self.required_field_override = []
        if hasattr(spider, 'allowed_empty'):
            if isinstance(spider.allowed_empty, list):
                for field in spider.allowed_empty:
                    self.required_field_override.append(field)

    def process_item(self, item, spider):
        '''
        validates and standardizes item fields, checks for text layer presence in PDFs,
        converts dates, checks field types, and performs duplication check.
        '''
        item['title'] = re.sub(r'[\s，/、\\\d\W]', '_', item['title'].strip()) #sanitize
        date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']
        for field in required_fields:
            if not item.get(field) and field not in self.required_field_override:
                process_error(item, 2, message=str(field))

        #check if pdf_to_download is valid url:
        if is_valid_url(item['pdf_to_download']) == False:
            error_message = f"Item: {item['original_link']} Field: 'pdf_to_download': {item['pdf_to_download']}. Not a valid url."
            process_error(item, 2, message=error_message)
        # else:
            # print(is_valid_url(item['pdf_to_download']))

        #checking for correct field types
        for field, expected_type in expected_field_types.items():
            if item.get(field) is None and field not in self.required_field_override:
                process_error(item, 2, message="Required field missing: %s" % str(field))
            else:
                if expected_type is datetime:
                    #convert string to datetime object
                    if isinstance(item.get(field), str):
                        date_converted = False
                        for date_format in date_formats:
                            try:
                                item[field] = datetime.strptime(item.get(field), date_format)
                                date_converted = True
                                break  #success, exit
                            except ValueError:
                                continue  #try the next format
                        if not date_converted:
                            #if none of the formats worked, log an error
                            error_message = f"Item: {item['original_link']} Field: {field}. Expected datetime formats {date_formats}, received {str(item.get(field))}."
                            process_error(item, 1, message=error_message)
                
                else:
                    #all other field types
                    if field in item:
                        current_value = item[field]
                        current_type = type(current_value)

                    if not isinstance(current_value, expected_type):
                        try:
                            converted_value = expected_type(current_value)
                            item[field] = converted_value
                            error_message = f"Item: {item['original_link']} Field: {field}. Expected {expected_type.__name__}, Received {current_type.__name__}. Type corrected."
                            process_error(item, 0, message=error_message)
                        except ValueError:
                                error_message = f"Item: {item['original_link']} Field: {field}. Expected {expected_type.__name__}, received {current_type.__name__}. Failed to convert."
                                process_error(item, 1, message=error_message)
                    else:
                        pass #added this to attempt to clear false positive errors
                        
        #adding standardized fields
        item['journal'] = spider.name
        item['uid'] = "-".join([str(element) for element in [item['journal'], item['year_number'], item['issue_number'], item['article_number'], item['title'].replace(' ','_')]])
        log_friendly_item = log_friendly(item)
        return log_friendly_item