from ast import Raise
from playwright.sync_api import sync_playwright, Page
import pandas as pd
from datetime import datetime 
import traceback

class Scraper:
    def __init__(self):
        self.data = {}
        self.article_count = 0
        self.page_count = 1
        self.df = None
        
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        self.page = context.new_page()

    def set_items_to_20(self):
        self.page.wait_for_selector('xpath=/html/body/main/div/div[3]/div[1]/form/div[1]/span/button[3]')
        self.page.locator('xpath=/html/body/main/div/div[3]/div[1]/form/div[1]/span/button[3]').click()
        self.page.wait_for_timeout(3000)

    def scrape_page(self):
        try:
            article_elements = self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/a').all()
            
            for article_element in article_elements:
                link = article_element.get_attribute('href')

                article_element = article_element.locator('xpath=/article/div').all()[-1]
                article_element.locator('xpath=/div[2]/h6').wait_for()
                               
                date_author_issues_element = article_element.locator('xpath=/div[1]/*').all()
                date = datetime.strptime(date_author_issues_element[0].inner_text(), '%B %d, %Y')

                authors = []
                while len(date_author_issues_element[2+len(authors)].locator('xpath=/span').all()) > 1:
                    authors.append(date_author_issues_element[2+len(authors)].locator('xpath=/span').all()[0].inner_text())
                authors.append(date_author_issues_element[2+len(authors)].inner_text())

                issues = []
                if len(date_author_issues_element) > 2+len(authors):
                    while len(date_author_issues_element[3+len(authors)+len(issues)].locator('xpath=/span').all()) > 1:
                        issues.append(date_author_issues_element[3+len(authors)+len(issues)].locator('xpath=/span').all()[0].inner_text())
                    issues.append(date_author_issues_element[3+len(authors)+len(issues)].inner_text())

                title = article_element.locator('xpath=/h4').inner_text()
                organization = article_element.locator('xpath=/div[2]').inner_text()

                self.data[self.article_count] = [date, authors, issues, title, organization, link]
                self.article_count += 1
        except Exception as e:
            raise e

    def has_next_page(self) -> bool:
        self.page.wait_for_selector('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[3]')

        if self.page_count <= 3:
            return True
        elif self.page_count >= 3 and self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[4]').count() > 0:
            return True
        else:
            return False

    def next_page(self):
        try:
            self.page.wait_for_selector('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[3]')
            
            # Get the first article's link to detect when content changes
            first_article = self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/a').first
            old_link = first_article.get_attribute('href')

            if self.page_count == 1:
                self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[2]').click()
                self.page_count += 1
            elif self.page_count == 2:
                self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[3]').click()
                self.page_count += 1
            elif self.page_count >= 3 and self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[4]').count() > 0:
                self.page.locator('xpath=/html/body/main/div/div[3]/div[2]/div/ul/li[4]').click()
                self.page_count += 1
            else:
                raise Exception("No next page found")
            
            # Wait for the first article link to change (indicating new content loaded)
            # This waits until the href attribute is different from the old value
            self.page.wait_for_function(
                f"""
                () => {{
                    const xpath = '/html/body/main/div/div[3]/div[2]/a';
                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                    const element = result.singleNodeValue;
                    if (!element) return false;
                    const currentLink = element.getAttribute('href');
                    return currentLink && currentLink !== '{old_link}';
                }}
                """,
                timeout=10000
            )
        except Exception as e:
            raise e
        
    def dump(self):
        self.df.to_csv('./output.csv')

    def run(self):
        try:
            self.page.goto('https://www.fdd.org/category/in_the_news/')
            # self.set_items_to_20

            self.scrape_page
            # i = 0
            while(self.has_next_page()):
                # i += 1
                self.next_page()
                self.scrape_page()
        except Exception as e:
            print(traceback.format_exc())
        finally:
            self.df = pd.DataFrame.from_dict(self.data, orient='index', columns=['date', 'author', 'issues', 'title', 'organization', 'link'])
        
        
s = Scraper()
s.run()
s.dump()



