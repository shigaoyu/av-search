import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PROXY = os.getenv('PROXY', 'http://127.0.0.1:7890')
    ARIA2_RPC_URL = os.getenv('ARIA2_RPC_URL', 'http://localhost:6800/rpc')
    ARIA2_SECRET = os.getenv('ARIA2_SECRET', '')
    
    # 爬虫请求头
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    }
