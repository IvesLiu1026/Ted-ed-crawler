
# TED Ed Crawler Script

## Description

This script is designed to crawl TED Ed lessons pages and extract video transcripts using Selenium and BeautifulSoup. It automates the process of browsing web pages, handling pop-ups, and collecting specific information for further analysis or processing.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/IvesLiu1026/Ted-ed-crawler.git
   ```

2. **Navigate to the project directory:**
   ```bash
   cd repository-name
   ```

3. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

4. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Make sure you have `chromedriver` installed and available in your PATH. You can download it from [here](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json).

## Usage

To run the script, use the following command:
```bash
python crawler.py
```

You can customize the script's behavior by modifying the configuration variables at the beginning of the `crawler.py` file.

## Features

- Automated web page browsing using Selenium.
- Data extraction using BeautifulSoup.
- Handles cookie consent pop-ups.
- Fetches YouTube video transcripts.
- Configurable crawling and extraction settings.

## Configuration

The script allows customization through several configuration variables defined in the `crawler.py` file. Here are some key configurations you can modify:

- `CHROMEDRIVER_PATH`: Path to the chromedriver executable.
- `START_URL`: The initial URL to start crawling from.
- `MAX_PAGES`: The maximum number of pages to crawl.
- `OUTPUT_FILE`: The file where the extracted data will be saved.
- `HEADLESS_MODE`: Boolean to run the browser in headless mode.

```python
# Example configuration in crawler.py
CHROMEDRIVER_PATH = r"path/to/your/chromedriver"
MAX_PAGES = 123
```
Notice that adjust the max_worker variable based on your PC configuration.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
