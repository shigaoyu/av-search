from engine.manager import MetadataManager
from config import Config
import json

def test():
    config = {
        'PROXY': 'http://127.0.0.1:7890'
    }
    mgr = MetadataManager(config)
    code = "SSIS-123"
    print(f"Enriching code: {code}")
    meta = mgr.get_metadata(code)
    print(f"Metadata result: {json.dumps(meta, indent=2)}")

if __name__ == "__main__":
    test()
