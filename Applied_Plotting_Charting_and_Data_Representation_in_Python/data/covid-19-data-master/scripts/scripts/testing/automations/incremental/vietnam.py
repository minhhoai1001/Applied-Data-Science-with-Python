"""Constructs daily time series of COVID-19 testing data for Vietnam."""
import os
import re
import requests
import datetime
from typing import List
from bs4 import BeautifulSoup
import pandas as pd


COUNTRY = 'Vietnam'
UNITS = 'samples tested'
TESTING_TYPE = 'PCR only'
SOURCE_LABEL = 'Vietnam General Department of Preventive Medicine'
FILEPATH = 'automated_sheets/Vietnam.csv'


def main() -> None:
    old = pd.read_csv(FILEPATH)
    new = get_recent_data()
    new['Country'] = COUNTRY
    new['Units'] = UNITS
    new['Testing type'] = TESTING_TYPE
    new['Source label'] = SOURCE_LABEL
    new['Notes'] = pd.NA
    df = merge_old_new(old, new)
    df.to_csv(FILEPATH, index=False)
    return None


def merge_old_new(old, new):
    df = pd.concat([old, new]).dropna(subset=["Cumulative total"])
    df = df.sort_values("Date").groupby("Date").head(1)
    df = df.sort_values("Cumulative total").groupby("Cumulative total").head(1)
    df["Cumulative total"] = df["Cumulative total"].astype(int)
    return df


def get_recent_data() -> pd.DataFrame:
    newsletter_urls = _get_newsletter_urls()
    data = []
    for d in newsletter_urls:
        try:
            url = d['url']
            date = d['date']
            samples_cumul = _extract_samples_tested(url)
            row = {'Date': date, 'Source URL': url, 'Cumulative total': samples_cumul}
            data.append(row)
        except Exception as e:
            print(f'Error extracting samples tested from {(date).strftime("%Y-%m-%d")} situation update ({url}): {e}')
    df = pd.DataFrame(data)
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    return df


def _get_newsletter_urls() -> List[dict]:
    """retrieves the URL and associated date for each daily COVID-19 disease
    update newsletter.
    """
    domain = 'http://vncdc.gov.vn'
    url = os.path.join(domain, 'tim-kiem.html?q=COVID-19')
    res = requests.get(url)
    soup = BeautifulSoup(res.content, 'html.parser')
    records = []
    list_h3_headings = soup.find('div', {'class': 'list_news_v2'}).find_all('h3')
    for h3 in list_h3_headings:
        regex_res = re.search(r'covid-19', h3.text, re.IGNORECASE)
        if regex_res:
            date_regex_res = re.search(r"[\d/]{8,10}", h3.text.strip())
            if date_regex_res:
                dd, mm, yyyy = re.findall(r"\d+", date_regex_res.group(0))
                date = datetime.datetime(int(yyyy), int(mm), int(dd))
                url = f"{domain}{h3.find('a').get('href')}"
                # print(date)
                records.append({'url': url, 'date': date})
    return records


def _extract_samples_tested(url: str) -> int:
    """extracts the cumulative number of samples tested to date from a single
    daily newsletter.
    """
    samples_cumul = None
    res = requests.get(url)
    soup = BeautifulSoup(res.content, 'html.parser')
    text = soup.find('div', {'class': 'content_news'}).text
    regex1 = re.compile(r"([\d,\.]+) x??t nghi???m Realtime RT-PCR", re.IGNORECASE)
    regex2 = re.compile(r"T???ng s??? m???u ???? x??t nghi???m c???ng d???n:?\s*([\d,\.]+)", re.IGNORECASE)
    regex3 = re.compile(r"T???ng s??? m???u b???nh ph???m ???? x??t nghi???m c???ng d???n:?\s*([\d,\.]+)", re.IGNORECASE)
    regex4 = re.compile(r"T???ng s??? m???u b???nh ph???m ???? x??t nghi???m ?????n nay l??:?\s*([\d,\.]+)", re.IGNORECASE)
    regexes = [regex1, regex2, regex3, regex4]
    while samples_cumul is None and len(regexes):
        regex = regexes.pop(0)
        regex_res = regex.search(text)
        if regex_res:
            samples_cumul = int(re.sub(r'[,\.\s]*', '', regex_res.groups()[0]))
    return samples_cumul


if __name__ == '__main__':
    main()
