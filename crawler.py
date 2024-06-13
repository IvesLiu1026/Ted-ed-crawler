import os
import time
import concurrent.futures
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import csv
from youtube_transcript_api import YouTubeTranscriptApi
import logging

load_dotenv()

GECKODRIVER_PATH = os.getenv("GECKODRIVER_PATH")
TED_ED_EMAIL = os.getenv("TED_ED_EMAIL")
TED_ED_PASSWORD = os.getenv("TED_ED_PASSWORD")

MAX_PAGES = 1
LOG_FILE = "scrape.log"
NO_TRANSCRIPT_FILE = "exception.csv"
LESSON_DATA_FILE = "lesson_data.json"

def click_element(firefox, xpath, timeout=10):
    element = WebDriverWait(firefox, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    element.click()

def enter_text(firefox, xpath, text, timeout=10):
    input_field = WebDriverWait(firefox, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    input_field.send_keys(text)
    time.sleep(2)

def handle_cookie_consent(firefox, timeout=10):
    WebDriverWait(firefox, timeout).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-pc-sdk"]/div/div[3]/div[1]/button[1]'))
    ).click()
    time.sleep(1)

def get_youtube_subtitle(youtube_link):
    youtube_id = youtube_link.split('v=')[-1]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(youtube_id, languages=['en'])
        subtitle = ' '.join([entry['text'] for entry in transcript])
        return subtitle
    except:
        return "Transcript not available"

def log_message(message, log_file=LOG_FILE):
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"{message}\n")

def write_csv(data, file_name=NO_TRANSCRIPT_FILE, fieldnames=None):
    with open(file_name, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(data)

class TEDScraper:
    def __init__(self, geckodriver_path, email, password, max_pages):
        self.geckodriver_path = geckodriver_path
        self.email = email
        self.password = password
        self.max_pages = max_pages
        self.results = []
        self.no_transcript_list = []

    def scrape_page(self, page_number):
        options = webdriver.FirefoxOptions()
        options.add_argument('--disable-logging')
        service = Service(executable_path=self.geckodriver_path)
        firefox = webdriver.Firefox(service=service, options=options)

        page_url = f"https://ed.ted.com/lessons.html?direction=desc&page={page_number}&sort=featured-position"
        firefox.get(page_url)

        handle_cookie_consent(firefox)
        self.sign_in(firefox)

        WebDriverWait(firefox, 10).until(EC.presence_of_element_located((By.ID, "lessons-grid")))
        lessons_grid_html = firefox.find_element(By.ID, 'lessons-grid').get_attribute('innerHTML')
        soup = BeautifulSoup(lessons_grid_html, 'html.parser')
        video_links = soup.select('a.text-gray-700.hover\\:text-gray-700')
        categories = soup.select('a.text-secondary-700.hover\\:text-secondary-700')

        if not video_links:
            firefox.quit()
            return

        video_number = 0
        for video_link, category_tag in zip(video_links, categories):
            video_number += 1
            lesson_url = f"https://ed.ted.com{video_link['href']}"
            think_url = f"{lesson_url}/think"

            firefox.get(lesson_url)
            title = WebDriverWait(firefox, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="main-content"]/article/div[1]/h1'))
            ).text

            category = category_tag.text.strip()
            lesson_data = self.extract_lesson_data(firefox, page_number, video_number, lesson_url, think_url, title, category)

            self.results.append(lesson_data)
            log_message(f"[Page: {page_number}, Video: {video_number}] is completed")

        firefox.quit()
        print("=" * 20)
        print(f"Page {page_number} completed")
        print("=" * 20)

    def sign_in(self, firefox):
        click_element(firefox, "/html/body/header/div/div/div/div/div/a")
        handle_cookie_consent(firefox)
        enter_text(firefox, "/html/body/div[2]/div/div[2]/form/label/input", self.email)
        click_element(firefox, "/html/body/div[2]/div/div[2]/form/div/span/span/button")
        enter_text(firefox, "/html/body/div[2]/div/div[2]/form/label[2]/div[2]/input", self.password)
        click_element(firefox, "/html/body/div[2]/div/div[2]/form/div/span/span/button")

    def extract_lesson_data(self, firefox, page_number, video_number, lesson_url, think_url, title, category):
        lesson_data = {
            "page": page_number,
            "lesson": video_number,
            "title": title,
            "category": category,
            "url": lesson_url,
            "transcript": "",
            "multiple-choice": [],
            "open-answer": []
        }

        # Extract transcript from YouTube video
        try:
            youtube_iframe = WebDriverWait(firefox, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[data-ui--youtube-video-target='frame']"))
            )
            youtube_link = youtube_iframe.get_attribute("src").split("?")[0].replace("embed/", "watch?v=")
            lesson_data["transcript"] = get_youtube_subtitle(youtube_link)
        except:
            lesson_data["transcript"] = "Transcript not available"
            self.no_transcript_list.append({
                "Title": title,
                "URL": lesson_url,
                "Remark": "Transcript not available"
            })
            write_csv({"Title": title, "URL": lesson_url, "Remark": "Transcript not available"})

        question_number = 1
        while True:
            try:
                question_url = f"{think_url}?question_number={question_number}"
                firefox.get(question_url)

                if "Question not found" in firefox.page_source:
                    raise Exception("No more questions")

                if firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]"):
                    lesson_data["multiple-choice"].append(self.extract_multiple_choice_question(firefox))
                elif firefox.find_elements(By.XPATH, "//div[@class='w-full max-w-lg']"):
                    lesson_data["open-answer"].append(self.extract_open_answer_question(firefox))
                else:
                    break

                question_number += 1

            except Exception as e:
                break

        return lesson_data

    def extract_multiple_choice_question(self, firefox):
        question_element = firefox.find_element(By.TAG_NAME, "legend")
        question_text = question_element.text
        question_data = {
            "question": question_text,
            "options": []
        }
        options_elements = firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]")
        for option in options_elements:
            option_label = option.find_element(By.XPATH, ".//span[contains(@class, 'rounded-full')]").text
            option_text = option.find_element(By.XPATH, ".//div[contains(@class, 'leading-6')]").text
            question_data["options"].append({"label": option_label, "text": option_text})
        return question_data

    def extract_open_answer_question(self, firefox):
        question_element = firefox.find_element(By.XPATH, "//div[@class='w-full max-w-lg']/h2")
        question_text = question_element.text
        return {"question": question_text}

    def save_data_as_json(self, file_name=LESSON_DATA_FILE):
        with open(file_name, 'w', encoding='utf-8') as json_file:
            json.dump(self.results, json_file, ensure_ascii=False, indent=4)
        print(f"Data saved to {file_name}")

    def print_data_to_console(self):
        print(json.dumps(self.results, ensure_ascii=False, indent=4))

    def scrape(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
            future_to_page = {executor.submit(self.scrape_page, page_number): page_number for page_number in range(1, self.max_pages + 1)}

            for future in concurrent.futures.as_completed(future_to_page):
                page_number = future_to_page[future]
                try:
                    future.result()
                except Exception as e:
                    log_message(f"Error processing page {page_number}: {e}")

        self.save_data_as_json()
        self.print_data_to_console()

if __name__ == "__main__":
    scraper = TEDScraper(GECKODRIVER_PATH, TED_ED_EMAIL, TED_ED_PASSWORD, MAX_PAGES)
    scraper.scrape()
    print("---Scraping completed---")
