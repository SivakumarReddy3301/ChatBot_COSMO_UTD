import scrapy
from utdcrawler.items import PageItem
import tldextract
import time

class UtdSpider(scrapy.Spider):
    name = "utd"
    allowed_domains = ["utdallas.edu"]
    start_urls = ["https://www.utdallas.edu/"]

    def __init__(self, *args, **kwargs):
        super(UtdSpider, self).__init__(*args, **kwargs)
        self.visited_links = set()

    def parse(self, response):
        self.logger.info(f"Crawling: {response.url}")

        # Mark URL as visited
        self.visited_links.add(response.url)

        # Save scraped content
        item = PageItem()
        item["url"] = response.url
        item["title"] = response.xpath("//title/text()").get(default="No Title")
        item["text"] = " ".join(response.xpath("//body//text()").getall()).strip()
        
        metadata = {}
        for meta in response.xpath("//meta[@name]"):
            name = meta.xpath("@name").get()
            content = meta.xpath("@content").get()
            metadata[name] = content
        item["metadata"] = metadata
        item["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        yield item

        # Follow links
        links = response.css("a::attr(href)").getall()
        for link in links:
            if link.startswith("//"):
                link = "https:" + link
            elif link.startswith("/"):
                link = response.urljoin(link)
            elif not link.startswith("http"):
                continue

            if self.is_valid_link(link) and (link not in self.visited_links):
                self.visited_links.add(link)
                self.logger.info(f"Following: {link}")
                yield scrapy.Request(
                    link,
                    callback=self.parse,
                    meta={"playwright": True},
                    dont_filter=True
                )

    def is_valid_link(self, link):
        if "polycraft.utdallas.edu" in link or "idp.utdallas.edu" in link or "atlas.utdallas.edu" in link or "calendar.utdallas.edu" in link or "coursebook.utdallas.edu" in link:
            return False

        domain_info = tldextract.extract(link)
        full_domain = f"{domain_info.domain}.{domain_info.suffix}"
        return "utdallas.edu" in full_domain