import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


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

    def parse(self, response):
        self.driver.get(response.url)
        wait = WebDriverWait(self.driver, 10)

        while True:
            html = self.driver.page_source
            resp = HtmlResponse(url=self.driver.current_url, body=html, encoding="utf-8")

            for place in resp.css(".gl-restaurants-lists-item a::attr(href)").getall():
                yield {"link": place}

            try:
                next_btn = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".btn-next"))
                )

                # kiểm tra nếu bị disable thì thoát vòng lặp
                if "disabled" in next_btn.get_attribute("class"):
                    break

                # nếu không thì click
                self.driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(2)

            except Exception as e:
                self.logger.info(f"Stop because no Next: {e}")
                break