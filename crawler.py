import os
import re
import csv
import time
import json
import concurrent.futures
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

GECKODRIVER_PATH = os.getenv("GECKODRIVER_PATH")
TED_ED_EMAIL = os.getenv("TED_ED_EMAIL")
TED_ED_PASSWORD = os.getenv("TED_ED_PASSWORD")
SIGN_IN = 1
END_PAGE = 1
START_PAGE = 1
OUTPUT_FILE = "test.jsonl"

class TedEdScraper:
    def __init__(self):
        self.results = []
        self.no_transcript_list = []
        self.log_file = "scrape.log"

    def initialize_browser(self):
        options = Options()
        # options.add_argument("--headless")
        options.binary_location = os.getenv("FIREFOX_BINARY_PATH")
        service = Service(executable_path=GECKODRIVER_PATH)
        return webdriver.Firefox(service=service, options=options)

    def login(self, firefox):
        self.handle_cookie_consent(firefox)
        self.click_sign_in_button(firefox)
        self.handle_cookie_consent(firefox)
        self.enter_email(firefox)
        self.click_continue_button(firefox)
        self.enter_password(firefox)
        self.click_continue_button(firefox)

    def handle_cookie_consent(self, firefox):
        try:
            WebDriverWait(firefox, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-pc-sdk"]/div/div[3]/div[1]/button[1]'))
            ).click()
            time.sleep(0.5)
        except:
            pass

    def click_sign_in_button(self, firefox):
        sign_in_button = WebDriverWait(firefox, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/header/div/div/div/div/div/a"))
        )
        sign_in_button.click()

    def click_continue_button(self, firefox):
        continue_button = WebDriverWait(firefox, 15).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/form/div/span/span/button"))
        )
        continue_button.click()

    def enter_email(self, firefox):
        email_input = WebDriverWait(firefox, 15).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/form/label/input"))
        )
        email_input.send_keys(TED_ED_EMAIL)
        time.sleep(0.5)

    def enter_password(self, firefox):
        password_input = WebDriverWait(firefox, 15).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/form/label[2]/div[2]/input"))
        )
        password_input.send_keys(TED_ED_PASSWORD)

    def get_lesson_title(self, firefox):
        return WebDriverWait(firefox, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="main-content"]/article/div[1]/h1'))
        ).text

    def get_youtube_link(self, firefox):
        try:
            youtube_iframe = WebDriverWait(firefox, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[data-ui--youtube-video-target='frame']"))
            )
            return youtube_iframe.get_attribute("src").split("?")[0].replace("embed/", "watch?v=")
        except:
            return None

    def reg_ex_processing(self, text):
        return re.sub(r'[\xc2-\xf4][\x80-\xbf]+',lambda m: m.group(0).encode('latin1').decode('utf8'),text)

    def get_youtube_subtitle(self, youtube_link, languages=['en']):
        youtube_id = youtube_link.split('v=')[-1]
        transcript_data = {}
        for lang in languages:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(youtube_id, languages=[lang])
                subtitle = ' '.join([entry['text'] for entry in transcript])
                transcript_data[lang] = subtitle
            except:
                transcript_data[lang] = "Transcript not available"
        return transcript_data

    def save_transcript_exception(self, title, lesson_url):
        self.no_transcript_list.append({
            "Title": title,
            "URL": lesson_url,
            "Remark": "Transcript not available"
        })
        with open('exception.csv', 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['Title', 'URL', 'Remark'])
            writer.writerow({"Title": title, "URL": lesson_url, "Remark": "Transcript not available"})

    def extract_question_data(self, firefox):
        question_element = firefox.find_element(By.TAG_NAME, "legend")
        question_text = self.reg_ex_processing(question_element.text)
        question_data = {
            "question": question_text,
            "options": [],
            "correct_option": None
        }
        options_elements = firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]")
        for option in options_elements:
            option_label = option.find_element(By.XPATH, ".//span[contains(@class, 'rounded-full')]").text
            option_text = option.find_element(By.XPATH, ".//div[contains(@class, 'leading-6')]").text
            question_data["options"].append({"label": option_label, "text": option_text})
        return question_data

    def get_question_links(self, firefox, lesson_url):
        think_url = f"{lesson_url}/think"
        firefox.get(think_url)
        WebDriverWait(firefox, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'li')))
        soup = BeautifulSoup(firefox.page_source, 'html.parser')
        question_links = soup.select('li a[href*="question_number"]')
        return [f"https://ed.ted.com{link['href']}" for link in question_links]

    def check_for_correct_option_exists(self, firefox):
        try:            
            correct_option_element = firefox.find_element(By.XPATH, "//span[contains(@class, 'bg-correct-green')]")
            print("Correct option found")
            correct_option_text = correct_option_element.text
            return correct_option_text
        except:
            return None

    def answering_question(self, firefox, question_url):
        options_list = firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]")
        option_idx = 0
        for option in options_list:
            option_idx += 1
            option_button = WebDriverWait(firefox, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"(//label[contains(@class, 'cursor-pointer')])[{option_idx}]"))
            )
            option_button.click()
            
            submit_button = WebDriverWait(firefox, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"(//label[contains(@class, 'cursor-pointer')])[{option_idx}]//button[@type='submit']"))
            )
            submit_button.click()
            time.sleep(0.5)
            
            try:
                correct_message = WebDriverWait(firefox, 1).until(
                    EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'text-correct-green')]"))
                )
                if correct_message:
                    correct_answer = chr(ord('A') + option_idx - 1)
                    return correct_answer
            except:
                try:
                    incorrect_message = WebDriverWait(firefox, 1).until(
                        EC.visibility_of_element_located((By.XPATH, "//p[contains(text(), 'That wasn’t it!')]"))
                    )
                    if incorrect_message:
                        firefox.get(question_url)
                        continue
                except Exception as e:
                    print(f"Error while handling incorrect answer: {e}")
        return None

    def process_lesson(self, firefox, lesson_url, page_number, video_number, category_tag):
        firefox.get(lesson_url)
        title = self.reg_ex_processing(self.get_lesson_title(firefox))

        lesson_data = {
            "page": page_number,
            "lesson": video_number,
            "title": title,
            "category": category_tag,
            "url": lesson_url,
            "transcript": {},
            "multiple-choice": []
        }

        youtube_link = self.get_youtube_link(firefox)
        if youtube_link:
            transcript = self.get_youtube_subtitle(youtube_link, languages=['en'])
            print(f"Transcript: {transcript['en']}")
            lesson_data["transcript"] = transcript
        else:
            lesson_data["transcript"] = {"en": "Transcript not available"}
            self.save_transcript_exception(title, lesson_url)

        questions_list = self.get_question_links(firefox, lesson_url)

        for question_url in questions_list:
            firefox.get(question_url)
            if firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]"):
                question_data = self.extract_question_data(firefox)
                lesson_data["multiple-choice"].append(question_data)
                print(f"Question: {question_data['question']}")
                for option in question_data["options"]:
                    print(f"Option: {option['label']}) {option['text']}")
                    
                if not self.check_for_correct_option_exists(firefox):
                    print("Answering question...")
                    correct_option = self.answering_question(firefox, question_url)
                else:
                    print("Checking for correct option...")
                    correct_option = self.check_for_correct_option_exists(firefox)
                    
                print(f"Correct option: {correct_option}")
                question_data["correct_option"] = correct_option

        with open(self.log_file, 'a', encoding='utf-8') as log:
            log.write(f"[Page: {page_number}, Video: {video_number}] is completed\n")
        
        self.results.append(lesson_data)
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as jsonlfile:
            jsonlfile.write(json.dumps(lesson_data) + '\n')

    def scrape_page(self, page_number):
        firefox = self.initialize_browser()
        page_url = f"https://ed.ted.com/lessons.html?direction=desc&page={page_number}&sort=featured-position"
        firefox.get(page_url)
        self.login(firefox)
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
            self.process_lesson(firefox, lesson_url, page_number, video_number, category_tag.text)

        firefox.quit()
        print("=" * 20)
        print(f"Page {page_number} completed")
        print("=" * 20)

    def scrape_ted_ed(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_to_page = {executor.submit(self.scrape_page, page_number): page_number for page_number in range(START_PAGE, END_PAGE + 1)}

            for future in concurrent.futures.as_completed(future_to_page):
                page_number = future_to_page[future]
                try:
                    future.result()
                except Exception as e:
                    with open(self.log_file, 'a', encoding='utf-8') as log:
                        log.write(f"Error processing page {page_number}: {e}\n")

if __name__ == "__main__":
    scraper = TedEdScraper()
    scraper.scrape_ted_ed()
    print("---Scraping completed---")