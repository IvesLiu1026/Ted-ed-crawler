import os
import time
import concurrent.futures
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import csv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

GECKODRIVER_PATH = os.getenv("GECKODRIVER_PATH")
TED_ED_EMAIL = os.getenv("TED_ED_EMAIL")
TED_ED_PASSWORD = os.getenv("TED_ED_PASSWORD")
SIGN_IN = 1
MAX_PAGES = 1

def initialize_browser():
    options = Options()
    options.binary_location = os.getenv("FIREFOX_BINARY_PATH")
    service = Service(executable_path=GECKODRIVER_PATH)
    return webdriver.Firefox(service=service, options=options)

def login(firefox):
    handle_cookie_consent(firefox)
    click_sign_in_button(firefox)
    handle_cookie_consent(firefox)
    enter_email(firefox)
    click_continue_button(firefox)
    enter_password(firefox)
    click_continue_button(firefox)

def handle_cookie_consent(firefox):
    try:
        WebDriverWait(firefox, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-pc-sdk"]/div/div[3]/div[1]/button[1]'))
        ).click()
        time.sleep(0.5)
    except:
        pass

def click_sign_in_button(firefox):
    sign_in_button = WebDriverWait(firefox, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/header/div/div/div/div/div/a"))
    )
    sign_in_button.click()

def click_continue_button(firefox):
    continue_button = WebDriverWait(firefox, 15).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div/div[2]/form/div/span/span/button"))
    )
    continue_button.click()

def enter_email(firefox):
    email_input = WebDriverWait(firefox, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/form/label/input"))
    )
    email_input.send_keys(TED_ED_EMAIL)
    time.sleep(0.5)

def enter_password(firefox):
    password_input = WebDriverWait(firefox, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/form/label[2]/div[2]/input"))
    )
    password_input.send_keys(TED_ED_PASSWORD)

def get_youtube_subtitle(youtube_link):
    youtube_id = youtube_link.split('v=')[-1]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(youtube_id, languages=['en'])
        subtitle = ' '.join([entry['text'] for entry in transcript])
        return subtitle
    except:
        return "Transcript not available"

def get_correct_option(firefox, options_elements, think_url):
    question_number = 0
    for i in range(len(options_elements)):
        try:
            # Re-fetch the options elements to avoid StaleElementReferenceError
            options_elements = WebDriverWait(firefox, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//label[contains(@class, 'cursor-pointer')]"))
            )
            option = options_elements[i]
            option_text = option.find_element(By.XPATH, ".//div[contains(@class, 'leading-6')]").text
            print(f"Trying option {i + 1}/{len(options_elements)}: {option_text}")
            option.click()
            print("option clicked")
            submit_button = WebDriverWait(firefox, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"/html/body/main/article/div[2]/turbo-frame/div[2]/div[1]/turbo-frame/div/turbo-frame/div/div/form/fieldset/label[{i + 1}]/button"))
            )
            submit_button.click()
            print("submit button clicked")
            # time.sleep(0.5)  # Wait for the result to be processed


            try:
                correct_message = WebDriverWait(firefox, 2).until(
                    EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'text-correct-green')]"))
                )
                if correct_message:
                    
                    print("Correct answer found")
                    firefox.get(f"{think_url}?question_number={question_number + 1}")
                    time.sleep(0.5)  # Ensure the page has fully loaded
                    option.addClass('correct')
                    # return option
            except:
                try:
                    incorrect_message = WebDriverWait(firefox, 2).until(
                        EC.visibility_of_element_located((By.XPATH, "//p[contains(text(), 'That wasn’t it!')]"))
                    )
                    if incorrect_message:
                        print("Incorrect answer, trying again")
                        firefox.get(f"{think_url}?question_number={question_number}")
                        time.sleep(0.5)  # Ensure the page has fully loaded
                except Exception as e:
                    print(f"Error while handling incorrect answer: {e}")
        except Exception as e:
            print(f"Error while trying option {i + 1}/{len(options_elements)}: {e}")
    return option



def process_lesson(firefox, lesson_url, page_number, video_number, results, no_transcript_list, log_file):
    firefox.get(lesson_url)
    title = WebDriverWait(firefox, 10).until(
        EC.visibility_of_element_located((By.XPATH, '//*[@id="main-content"]/article/div[1]/h1'))
    ).text

    lesson_data = {
        "page": page_number,
        "lesson": video_number,
        "title": title,
        "url": lesson_url,
        "transcript": "",
        "multiple-choice": [],
        "open-answer": []
    }

    try:
        youtube_iframe = WebDriverWait(firefox, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[data-ui--youtube-video-target='frame']"))
        )
        youtube_link = youtube_iframe.get_attribute("src").split("?")[0].replace("embed/", "watch?v=")
        lesson_data["transcript"] = get_youtube_subtitle(youtube_link)
    except:
        lesson_data["transcript"] = "Transcript not available"
        no_transcript_list.append({
            "Title": title,
            "URL": lesson_url,
            "Remark": "Transcript not available"
        })
        with open('exception.csv', 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['Title', 'URL', 'Remark'])
            writer.writerow({"Title": title, "URL": lesson_url, "Remark": "Transcript not available"})

    think_url = f"{lesson_url}/think"
    question_number = 1
    while True:
        try:
            question_url = f"{think_url}?question_number={question_number}"
            firefox.get(question_url)

            if "Question not found" in firefox.page_source:
                raise Exception("No more questions")

            if firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]"):
                question_element = firefox.find_element(By.TAG_NAME, "legend")
                question_text = question_element.text
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
                    
                correct_option = get_correct_option(firefox, options_elements, think_url, question_number)
                
                # if correct_option:
                question_data["correct_option"] = correct_option.find_element(By.XPATH, ".//div[contains(@class, 'leading-6')]").text
                print(f"Correct answer: {question_data['correct_option']}")

                lesson_data["multiple-choice"].append(question_data)
                print(f"Question: {question_text}")
                for option in question_data["options"]:
                    print(f"Option: {option['label']}) {option['text']}")
            else:
                break

            # print(f"Question {question_number} completed")
            # question_number += 1
        except Exception as e:
            break

    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"[Page: {page_number}, Video: {video_number}] is completed\n")
    
    results.append(lesson_data)

def scrape_page(page_number, results, no_transcript_list, log_file):
    firefox = initialize_browser()

    page_url = f"https://ed.ted.com/lessons.html?direction=desc&page={page_number}&sort=featured-position"
    firefox.get(page_url)

    login(firefox)

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
        process_lesson(firefox, lesson_url, page_number, video_number, results, no_transcript_list, log_file)

    firefox.quit()
    print("=" * 20)
    print(f"Page {page_number} completed")
    print("=" * 20)

def scrape_page(page_number, results, no_transcript_list, log_file):
    firefox = initialize_browser()

    page_url = f"https://ed.ted.com/lessons.html?direction=desc&page={page_number}&sort=featured-position"
    firefox.get(page_url)

    login(firefox)
    # handle_cookie_consent(firefox)

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
        process_lesson(firefox, lesson_url, page_number, video_number, results, no_transcript_list, log_file)

    firefox.quit()
    print("=" * 20)
    print(f"Page {page_number} completed")
    print("=" * 20)

def scrape_ted_ed():
    results = []
    no_transcript_list = []
    log_file = "scrape.log"

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_to_page = {executor.submit(scrape_page, page_number, results, no_transcript_list, log_file): page_number for page_number in range(1, MAX_PAGES + 1)}

        for future in concurrent.futures.as_completed(future_to_page):
            page_number = future_to_page[future]
            try:
                future.result()
            except Exception as e:
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Error processing page {page_number}: {e}\n")

if __name__ == "__main__":
    scrape_ted_ed()
    print("---Scraping completed---")
