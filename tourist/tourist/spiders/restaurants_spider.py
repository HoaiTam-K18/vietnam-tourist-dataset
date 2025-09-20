import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import json, re


class RestaurantSpider(scrapy.Spider):
    name = "restaurants"
    start_urls = [
        "https://www.trip.com/restaurant/city-434.html"
    ]

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # bỏ nếu muốn thấy trình duyệt chạy
        service = Service("/opt/homebrew/bin/chromedriver")  # đường dẫn ChromeDriver
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.seen = set()  # dùng để lọc trùng theo url

    def parse(self, response):
        self.driver.get(response.url)
        wait = WebDriverWait(self.driver, 10)

        while True:
            html = self.driver.page_source
            resp = HtmlResponse(url=self.driver.current_url, body=html, encoding="utf-8")

            data = resp.css("#__NEXT_DATA__::text").get()
            json_data = json.loads(data)

            restaurants = json_data["props"]["pageProps"]["initialState"]["resultList"]

            for r in restaurants:
                url = "https://us.trip.com" + r.get("jumpUrl", "")
                if not url or url in self.seen:  # bỏ qua trùng
                    continue
                self.seen.add(url)

                img = r.get("imgeUrls")
                name = r.get("englishName", "")
                rating = r.get("rating", None)
                review_count = r.get("reviewCount", 0)
                gglat = r.get("gglat", None)
                gglon = r.get("gglon", None)
                coordinate = str(gglat) + ", " + str(gglon)
                price = r.get("price", 0)
                short_desc = r["rankings"][0].get("recommendReason") if r.get("rankings") else None

                long_desc = ""
                if r.get("commentInfo") and isinstance(r["commentInfo"], list):
                    long_desc = r["commentInfo"][0].get("content", "")
                    long_desc = re.sub(r"\s+", " ", long_desc).strip()

                # gửi sang parse_item để lấy thêm chi tiết (ví dụ address)
                yield resp.follow(
                    url,
                    callback=self.parse_item,
                    meta={
                        "name": name,
                        "img": img,
                        "rating": rating,
                        "review_count": review_count,
                        "short_desc": short_desc,
                        "long_desc": long_desc,
                        "price": price,
                        "coordinate": coordinate,
                        "url": url,
                    }
                )

            try:
                next_btn = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-next"))
                )
                if "disabled" in next_btn.get_attribute("class"):
                    break

                old_data = data
                self.driver.execute_script("arguments[0].click();", next_btn)

                # chờ đến khi dữ liệu JSON thay đổi
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.find_element(By.CSS_SELECTOR, "#__NEXT_DATA__").get_attribute("innerHTML") != old_data
                )

            except Exception as e:
                self.logger.info(f"Stop because no Next: {e}")
                break

    def parse_item(self, response):
        item = {
            "name": response.meta.get("name"),
            "img": response.meta.get("img"),
            "rating": response.meta.get("rating"),
            "review_count": response.meta.get("review_count"),
            "short_desc": response.meta.get("short_desc"),
            "long_desc": response.meta.get("long_desc"),
            "price": response.meta.get("price"),
            "coordinate": response.meta.get("coordinate"),
            "url": response.meta.get("url"),
        }

        # địa chỉ nằm trong detail page
        address_list = response.css(".gl-poi-detail_info div div::text").getall()
        address = address_list[1] if len(address_list) > 1 else None
        item["address"] = address

        yield item
