from .base import BaseCrawler
from .javbus import JavBusCrawler
from .javdb import JavDbCrawler
from .sukebei import SukebeiCrawler

def get_crawlers(config):
    return [
        SukebeiCrawler(config),
        JavBusCrawler(config),
        JavDbCrawler(config),
    ]
