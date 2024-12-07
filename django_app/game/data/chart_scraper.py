from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import pandas as pd
from selenium.webdriver.support.ui import Select
from tqdm import tqdm
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm
# Set up WebDriver
def save_find_element(parent, by_type, location):
    try:
        # Wait for the table to load
        element = WebDriverWait(parent, 10).until(
            EC.presence_of_element_located((by_type,location))
        )
        return element
    except TimeoutException:
        print(f"Failed")

def save_find_elements(parent, by_type, location):
    try:
        elements = WebDriverWait(parent, 10).until(
            lambda d: parent.find_elements(by_type, location)
        )
        return elements
    except TimeoutException:
        print(f"Failed")

def get_chart_data(start_year=1960, end_year=2024, us=False):
    driver = webdriver.Chrome()
    all_song_data = []

    driver.get(f"http://www.charts-surfer.de/musikcharts.php")

    submit_button = save_find_element(driver,By.XPATH, '//*[@id="musik"]/form/table/tbody/tr[7]/td/input')
    submit_button.click()

    for year in tqdm(range(start_year, end_year + 1)):
        selector_top_count = save_find_element(driver, By.XPATH, '//*[@id="musik"]/form/table/tbody/tr[2]/td[4]/select')
        selector_top_count = Select(selector_top_count)
        selector_top_count.select_by_visible_text("Top 100")

        selector_year = save_find_element(driver, By.XPATH, '//*[@id="musik"]/form/table/tbody/tr[2]/td[5]/select')
        selector_year = Select(selector_year)
        selector_year.select_by_visible_text(str(year))
        
        if us:
            selector_year = save_find_element(driver, By.XPATH, '//*[@id="musik"]/form/table/tbody/tr[2]/td[1]/select')
            selector_year = Select(selector_year)
            selector_year.select_by_value("uss")

        submit_button = save_find_element(driver,By.XPATH, '//*[@id="musik"]/form/table/tbody/tr[3]/td/input')
        submit_button.click()

        table = save_find_element(driver, By.XPATH, '//*[@id="musik"]/table[2]/tbody')

        # Find all song rows
        song_list = save_find_elements(table, By.TAG_NAME, 'tr')

        # Iterate through the table rows and print the content
        for song_row in song_list[2:]:
            try:
                # Wait for each element in the row
                song_elements = save_find_elements(song_row, By.TAG_NAME, "td") + save_find_elements(song_row, By.TAG_NAME, "th")
                song = {
                    "title": song_elements[1].text, 
                    "artists": song_elements[3].text,  
                    "points": song_elements[6].text, 
                    "pos": song_elements[5].text, 
                    "max_pos": song_elements[7].text, 
                    "year_released": song_elements[8].text, 
                    "year_charts": year, 
                    "weeks_top10": song_elements[9].text, 
                }
                all_song_data.append(song)
                # Extract data
            except NoSuchElementException as e:
                print(f"Missing elements in a row: {e}")
    df = pd.DataFrame(all_song_data)
    return df
