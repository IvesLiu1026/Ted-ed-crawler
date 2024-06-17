
# TedEd Scraper

TedEd Scraper is a Python project designed to scrape lesson information, including titles, transcripts, and multiple-choice questions from the TED-Ed website. This script utilizes Selenium for web automation and BeautifulSoup for HTML parsing. It also integrates the YouTube Transcript API to fetch subtitles for the videos.

## Features

- Login to TED-Ed
- Fetch lesson titles
- Extract YouTube video links
- Retrieve video transcripts in multiple languages
- Extract multiple-choice questions and options
- Determine correct answers to questions
- Save results in JSONL format

## Installation

1. **Clone the repository:**

```sh
git clone https://github.com/IvesLiu1026/Ted-ed-crawler.git
cd Ted-ed-crawler
```

2. **Create and activate a virtual environment (optional but recommended):**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. **Install the required Python packages:**

```sh
pip install -r requirements.txt
```

4. **Set up environment variables:**

Create a `.env` file in the root directory of the project and add the following lines:

```sh
GECKODRIVER_PATH=/path/to/geckodriver
FIREFOX_BINARY_PATH=/path/to/firefox
TED_ED_EMAIL=your_teded_email
TED_ED_PASSWORD=your_teded_password
```

Replace `/path/to/geckodriver`, `/path/to/firefox`, `your_teded_email`, and `your_teded_password` with the appropriate values.

## Usage

Run the scraper by executing:

```sh
python crawler.py
```

The scraper will log in to TED-Ed, navigate through the lessons, and save the results in a `results.jsonl` file. It will also log any issues encountered during the scraping process in `scrape.log`.

## File Structure

- `teded_scraper.py`: Main script that performs the web scraping.
- `requirements.txt`: List of Python packages required for the project.
- `.env`: Environment variables for sensitive information (not included in the repository).
- `scrape.log`: Log file for tracking the scraping process.
- `results.jsonl`: File where the scraped data is saved in JSONL format.
- `exception.csv`: File where lessons without transcripts are logged.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.