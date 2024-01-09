import time
from queue import Queue
from threading import Event, Thread

import requests
from bs4 import BeautifulSoup


class Site:

  def __init__(self, url, parser):
    self.url = url
    self.parser = parser


class NewsItem:

  def __init__(self, source, title, author, date, summary):
    self.source = source
    self.title = title
    self.author = author
    self.date = date
    self.summary = summary

  def __eq__(self, other):
    return self.title == other.title


class Scrapper:

  def __init__(self, sitesToParse, interval):
    self.sitesToParse = sitesToParse
    self.interval = interval
    self.newsQueue = Queue()
    self.pastNews = []

  def run(self):
    pill2kill = Event()  # event used to stop thread on exit

    def worker(stopEvent, sites, queue, interval):
      while not stopEvent.is_set():
        for site in sites:
          response = requests.get(site.url)
          soup = BeautifulSoup(response.text, 'html.parser')
          site.parser(soup, queue)
        print('Worker: sleeping for ' + str(interval) + ' seconds')
        time.sleep(interval)
      print('Worker: thread stopped')

    workerThread = Thread(target=worker,
                          args=(pill2kill, self.sitesToParse, self.newsQueue,
                                self.interval))
    workerThread.daemon = True
    workerThread.start()

    try:
      while True:
        print('Main: waiting for news queue...')
        item = self.newsQueue.get()

        if item in self.pastNews:
          print('Main: old item, not interested')
          continue

        self.pastNews.append(item)

        print(f'Source: {item.source}\n Title: {item.title}')
        if item.summary is not None:
          print(f' Summary: {item.summary}')
        if item.author is not None:
          print(f' Author: {item.author} ')
        if item.date is not None:
          print(f' Date: {item.date}')
        print()
    except KeyboardInterrupt:
      print('Main: stopping worker thread, please wait')
      pill2kill.set()  # send stop event to worked thread
      workerThread.join()  # waiting for thread to finish (interval)
      print('Main: worker thread stopped')


def washingtonpostParser(soup, queue):
  chain = soup.find_all('div', class_='chain')[0]
  cards = chain.find_all('div', class_='card')

  for card in cards:
    headline = card.find('div', class_='headline')
    title = headline.find('span').text.strip()

    author = None
    date = None

    if card.attrs['data-feature-name'] == 'latest-1-4-everywhere':
      byline = card.find('div', class_='byline')
      if byline is not None:
        date = byline.text.strip()
    else:
      byline = card.find('div', class_='byline')
      if byline is not None:
        authors = byline.find_all('a')
        author = ''
        for auth in authors:
          author += auth.text.strip() + ' '

        timestamp = byline.find('span')
        if timestamp is not None:
          date = timestamp.text.strip()

    queue.put(NewsItem('The Washington Post', title, author, date, None))


def abcnewsParser(soup, queue):
  items = soup.find_all('section', class_='ContentRoll__Item')

  for item in items:
    headline = item.find('div', class_='ContentRoll__Headline')
    title = headline.find('a').text.strip()
    summary = headline.find('div', class_='ContentRoll__Desc').text.strip()
    date = item.find('div', class_='ContentRoll__TimeStamp').text.strip()

    queue.put(NewsItem('ABC News', title, None, date, summary))


def foxnewsParser(soup, queue):
  section = soup.find('section', class_='collection-article-list')
  items = section.find_all('article', class_='article')

  for item in items:
    title = item.find('h4', class_='title').text.strip()
    meta = item.find('div', class_='meta')
    date = meta.find('span', class_='time').text.strip()

    queue.put(NewsItem('Fox News', title, None, date, None))


sitesToParse = [
    Site('https://www.washingtonpost.com/', washingtonpostParser),
    Site('https://abcnews.go.com/International', abcnewsParser),
    Site('https://www.foxnews.com/world', foxnewsParser)
]

scrapper = Scrapper(sitesToParse, 60)
scrapper.run()
