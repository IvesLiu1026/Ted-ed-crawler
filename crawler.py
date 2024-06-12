import concurrent.futures
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import csv
from youtube_transcript_api import YouTubeTranscriptApi
import logging

GECKODRIVER_PATH = r"D:/NYCU1122courses/Project/crawler/geckodriver.exe"
MAX_PAGES = 1
# Disable logging
logging.basicConfig(level=logging.CRITICAL)

def get_youtube_subtitle(youtube_link):
    youtube_id = youtube_link.split('v=')[-1]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(youtube_id, languages=['en'])
        subtitle = ' '.join([entry['text'] for entry in transcript])
        return subtitle
    except:
        return "Transcript not available"

def handle_cookie_consent(chrome):
    try:
        WebDriverWait(chrome, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-pc-sdk"]/div/div[3]/div[1]/button[1]'))
        ).click()
    except:
        print("No cookie consent popup found")

def scrape_page(page_number, results, no_transcript_list, log_file):
    options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    service = Service(executable_path=GECKODRIVER_PATH)
    firefox = webdriver.Firefox(service=service)
    
    page_url = f"https://ed.ted.com/lessons.html?direction=desc&page={page_number}&sort=featured-position"
    firefox.get(page_url)
    
    # Handle cookie consent popup
    handle_cookie_consent(firefox)
    
    # Wait for the lessons grid to load
    WebDriverWait(firefox, 10).until(EC.presence_of_element_located((By.ID, "lessons-grid")))
    lessons_grid_html = firefox.find_element(By.ID, 'lessons-grid').get_attribute('innerHTML')
    soup = BeautifulSoup(lessons_grid_html, 'html.parser')
    video_links = soup.select('a.text-gray-700.hover\\:text-gray-700')
    categories = soup.select('a.text-secondary-700.hover\\:text-secondary-700')
    
    if not video_links:  # If no video links are found, break the loop
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

        # Extract the category
        category = category_tag.text.strip()

        # Check if the "Think" section exists by directly trying to access the URL
        firefox.get(think_url)
        if "Sorry, we couldn't find that page" in firefox.page_source:
            continue

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
            no_transcript_list.append({
                "Title": title,
                "URL": lesson_url,
                "Remark": "Transcript not available"
            })
            # Write no transcript lesson to a CSV file
            with open('exception.csv', 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['Title', 'URL', 'Remark'])
                writer.writerow({"Title": title, "URL": lesson_url, "Remark": "Transcript not available"})
        
        question_number = 1
        while True:
            try:
                question_url = f"{think_url}?question_number={question_number}"
                firefox.get(question_url)

                # Check if the question page exists
                if "Question not found" in firefox.page_source:
                    raise Exception("No more questions")

                # Determine question type by checking for multiple-choice or open-answer
                if firefox.find_elements(By.XPATH, "//label[contains(@class, 'cursor-pointer')]"):
                    # Multiple-choice question
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
                    lesson_data["multiple-choice"].append(question_data)
                elif firefox.find_elements(By.XPATH, "//div[@class='w-full max-w-lg']"):
                    question_element = firefox.find_element(By.XPATH, "//div[@class='w-full max-w-lg']/h2")
                    question_text = question_element.text
                    lesson_data["open-answer"].append({"question": question_text})
                else:
                    break
                
                question_number += 1

            except Exception as e:
                break
            
        # results.append(lesson_data)
        # Write result to JSON file
        with open('dataset.json', 'r+', encoding='utf-8') as f:
            try:
                data = json.load(f)
                data.append(lesson_data)
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4)
            except json.JSONDecodeError:
                # If there is a JSON decode error, handle it (e.g., log the error)
                with open('scrape_log.txt', 'a', encoding='utf-8') as log:
                    log.write("@" * 30 + "\n")
                    log.write("Page: " + str(page_number) + ", Video: " + str(video_number) + "\n")
                    log.write("JSON decode error in dataset.json\n")
                    log.write("@" * 30 + "\n")
                
        # Write result to CSV file
        # fieldnames = ["page", "lesson", "title", "category", "url", "transcript"]
        # with open('dataset.csv', 'a', newline='', encoding='utf-8') as csvfile:
        #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #     if csvfile.tell() == 0:  # Write header only if the file is empty
        #         writer.writeheader()
        #     writer.writerow({
        #         "page": page_number,
        #         "lesson": video_number,
        #         "title": title,
        #         "category": category,
        #         "url": lesson_url,
        #         "transcript": lesson_data["transcript"]
        #     })
                
        # Write log to file
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"[Page: {page_number}, Video: {video_number}] is completed\n")
        
    firefox.quit()
    print("=" * 20)
    print(f"Page {page_number} completed")
    print("=" * 20)
    
def scrape_ted_ed():
    results = []
    no_transcript_list = []
    log_file = "scrape.log"

    # Create a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        future_to_page = {executor.submit(scrape_page, page_number, results, no_transcript_list, log_file): page_number for page_number in range(1, MAX_PAGES + 1)}

        for future in concurrent.futures.as_completed(future_to_page):
            page_number = future_to_page[future]
            try:
                future.result()
            except Exception as e:
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"Error processing page {page_number}: {e}\n")
    
    # Save results to a JSON file
    # with open('results.json', 'w', encoding='utf-8') as f:
    #     json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    scrape_ted_ed()
    print("---Scraping completed---")
