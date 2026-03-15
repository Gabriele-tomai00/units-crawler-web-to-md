# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import json
import os

ITEM_CHECK_INTERVAL = 10000        # Check file size every N items
CHUNK_MAX_BYTES = 8 * 1024**3     # 8 GB


class saveLinksPipeline:
    def __init__(self, depth_limit):
        self.file_path = f"../results_scrapy/links_list_{depth_limit}.txt"
        with open(self.file_path, "w") as f:
            pass

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            depth_limit=crawler.settings.get('DEPTH_LIMIT')
        )

    def process_item(self, item, spider):
        if 'url' in item:
            with open(self.file_path, "a") as f:
                f.write(item['url'] + "\n")
        return item




class MultiFileJsonPipeline:
    """
    This pipeline saves scraped items into JSONL files. 
    It automatically rotates the output file when it exceeds a configured size limit (CHUNK_MAX_BYTES), 
    ensuring that individual files do not become too large. 
    It also clears the output directory at the start of the spider.
    """
    def open_spider(self, spider):
        self.output_dir = getattr(spider, "output_dir", f"../results_scrapy/scraper_results")
        # Clear output folder at start
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.part = 1
        self.counter = 0
        self.global_item_count = 0
        self._open_new_file()

    def _open_new_file(self):
        if hasattr(self, "file") and self.file:
            self.file.close()

        self.current_filename = os.path.join(self.output_dir, f"part_{self.part}.jsonl")
        self.file = open(self.current_filename, "w", encoding="utf-8")
        print(f"Opened new chunk: part_{self.part}.jsonl")
        self.part += 1
        self.counter = 0

    def process_item(self, item, spider):
        line = json.dumps(item, ensure_ascii=False) + "\n"
        self.file.write(line)
        self.counter += 1
        self.global_item_count += 1

        # Check file size only every ITEM_CHECK_INTERVAL items
        if self.global_item_count % ITEM_CHECK_INTERVAL == 0:
            file_size = os.path.getsize(self.current_filename)
            if file_size >= CHUNK_MAX_BYTES:
                print(f"Chunk reached {file_size/1024**3:.2f} GB, rotating file...")
                self._open_new_file()

        return item

    def close_spider(self, spider):
        if self.file:
            self.file.close()
        print("All items written, spider closed.")
