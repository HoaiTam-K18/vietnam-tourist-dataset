import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class AttractionsSpider(scrapy.Spider):
    name = "attractions"
    start_urls = [
        "https://www.trip.com/travel-guide/attraction/ho-chi-minh-city-434/tourist-attractions/"
    ]

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # bỏ nếu muốn thấy trình duyệt chạy
        service = Service("/opt/homebrew/bin/chromedriver")  # đường dẫn ChromeDriver
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def parse(self, response):
        self.driver.get(response.url)
        wait = WebDriverWait(self.driver, 10)

        while True:
            html = self.driver.page_source
            resp = HtmlResponse(url=self.driver.current_url, body=html, encoding="utf-8")

            for item in resp.css(".OnlinePoiList_listBox__XDyli a"):
                url = item.css("::attr(href)").get()

                rating = item.css(".Reviews_tripScoreValue__BaSt9::text").get()
                review_count = item.css(".Reviews_tripScoreViews__pJXRN::text").get()
                meta = {
                    "rating":rating,
                    "review_count":review_count,
                }

                yield resp.follow(url, callback=self.parse_item, meta=meta)

            try:
                next_btn = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#__next > div.PoiListStyle-sc-tfa2r6-0 > div.trip-poi-list > div > div.xtaro-xview.OnlinePoiList_right__zhxWh > div.xtaro-xview.OnlinePoiList_listBox__XDyli > div > div:nth-child(3)"))
                )

                # kiểm tra nếu bị disable thì thoát vòng lặp
                if "Pagination_disabled__sp5HS" in next_btn.get_attribute("class"):
                    break

                # nếu không thì click
                self.driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)

            except Exception as e:
                self.logger.info(f"Stop because no Next: {e}")
                break

    def parse_item(self, response):
        rating = response.meta.get("rating")
        review_count = response.meta.get("review_count")


        name = response.css(".basicName::text").get()
        open_address = response.css(".one-line .field::text").getall()

        opening_hours = open_address[0].strip() if len(open_address) > 0 else None
        address = open_address[2].strip() if len(open_address) > 2 else None

        img = response.css(".img-bg::attr(src)").get()

        long_desc = response.css(".asctivity_details p::text").get()

        price = response.css(".tour-price span::text").getall()[1]

        text = response.css("#__NEXT_DATA__").get()
        for item in text.split("{"):
            if "coordinateType" in item:
                coord_raw = item
                break

        latitude = coord_raw.split(",")[1]
        longitude = coord_raw.split(",")[2]

        latitude = latitude.split(":")[1]
        longitude = longitude.split(":")[1][:-1]

        coordinate = latitude + ", " + longitude


        yield {
            "name": name,
            "address": address,
            "opening_hours": opening_hours,
            "img": img,
            "rating": rating,
            "review_count": review_count,
            "long_desc": long_desc,
            "price": price,
            "coordinate": coordinate,
            "url": response.url,
        }
