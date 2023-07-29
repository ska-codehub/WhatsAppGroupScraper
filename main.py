import os
import sys
import signal
import argparse
from pathlib import Path
import time
import random
import pandas as pd
import json
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import traceback

BASE_DIR = Path("./")
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = BASE_DIR / "archive"
CHROME_FOLDER = BASE_DIR / "chrome"
USER_DATA_DIR = CHROME_FOLDER / "user-data"
GROUP_NAMES_PATH = BASE_DIR / "groupnames.json"

USER_DATA_DIR.mkdir(exist_ok=True)

SITE_DOMAIN = "web.whatsapp.com"
LOGIN_URL = f"https://{SITE_DOMAIN}"
LOGIN_TITLE = "WhatsApp"
LOGIN_REDIRECT_TITLE = LOGIN_TITLE

HEALTH_CHECK_URL = "https://www.google.com"
HEALTH_CHECK_TITLE = "Google"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.5735.90",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36", 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
]


def confirmation_input(ask_str, ask_type):
    if ask_type not in ['Y/n', 'y/N', 'N/y', 'n/Y']:
        ask_type = 'Y/n'
    ask_str = f"{ask_str} [{ask_type}]: "
    while True:
        ask_value = input(ask_str).lower()
        if not ask_value in ['', 'yes', 'y', 'no', 'n']:
            print("Please provide a valid confirmation!")
            continue
        if ask_type == 'Y/n':
            return ask_value in ['', 'yes', 'y']
        elif ask_type == 'y/N':
            return ask_value in ['yes', 'y']
        elif ask_type == 'N/y':
            return ask_value in ['yes', 'y']
        elif ask_type == 'n/Y':
            return ask_value in ['', 'yes', 'y']


class WhatsAppScraper:
    def __init__(self,invisible=False) -> None:
        self.invisible = invisible
        self.user_agent = USER_AGENTS[random.randrange(0, len(USER_AGENTS)-1)]
        self.page_load_timeout = 60
        self.not_ok = 0
        self.retry = 0
        self.max_retries = 3

    def is_head_ready(self):
        try:
            WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "head")))
            return self.browser.find_element(By.TAG_NAME, "head") is not None 
        except Exception as e:
            print("WhatsAppScraper.is_head_ready Error: ", e, traceback.format_exc())
            return False
    
    def is_dom_ready(self):
        try:
            time.sleep(0.5)
            WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))                
            try:
                self.browser.execute_script(f'window.scrollTo(0, {random.randrange(100, 1000)})')
            except:
                pass
            return self.browser.find_element(By.TAG_NAME, "body") is not None
        except Exception as e:
            print("WhatsAppScraper.is_dom_ready Error: ", e, traceback.format_exc())
            return False        

    def is_title_valid(self, title=None):
        try:
            if title is None:return True
            return self.browser.title.strip()==title
        except Exception as e:
            print("WhatsAppScraper.is_title_valid Error: ", e, traceback.format_exc())
            return False
        
    def is_page_ready(self, title):
        ready = False
        for _ in range(0, 3):
            try:
                time.sleep(1)
                ready = self.is_head_ready() and self.is_dom_ready() and self.is_title_valid(title)
                if ready:
                    break
            except:
                ready = False
        return ready


    def get_page(self, url, title=None):
        try:
            self.browser.get(url)
            time.sleep(1)
            return self.is_page_ready(title)
        except TimeoutException as e:
            print("WhatsAppScraper.get_page Error1: ", e, traceback.format_exc())
            if self.retry<=self.max_retries:
                self.retry += 1
                # self.config_browser()
                return self.get_page(url, title)
            return False
        except Exception as e:
            print("WhatsAppScraper.get_page Error2: ", e, traceback.format_exc())
            return False

    def test_browser_ok(self):
        print("Testing browser")
        if self.get_page(HEALTH_CHECK_URL, HEALTH_CHECK_TITLE):
            self.not_ok = 0
            print("OK")
            return True
        else:
            self.not_ok += 1
            print("NOT OK")
            return False
    
    def kill_browser_process(self):
        killed = False        
        try:
            if self.browser is not None:
                print("Killing browser instances and process")
                pid = int(self.browser.service.process.id)
                try:
                    self.browser.service.process.send_signal(signal.SIGTERM)
                except:
                    pass
                try:
                    if self.browser.service is not None:
                        self.browser.close()
                except:
                    pass
                try:
                    if self.browser.service is not None:
                        self.browser.quit()
                    if self.browser.service is None:
                        killed = True
                except:
                    pass
                try:
                    if not killed and self.browser.service is not None:
                        os.kill(pid, signal.SIGTERM)
                    killed = True
                except:
                    pass
                try:
                    if not killed and self.browser.service is not None:
                        import psutil
                        from contextlib import suppress
                        for process in psutil.process_iter():
                            try:
                                if process.name() == "chrome.exe" \
                                    and "--test-type=webdriver" in process.cmdline():
                                    with suppress(psutil.NoSuchProcess):
                                        try:
                                            os.kill(process.pid, signal.SIGTERM)
                                            killed = True
                                        except:
                                            pass
                            except:
                                pass
                except:
                    pass
        except:
            pass
        if killed:
            print("Browser closed and webdriver process killed!")
        else:
            print("Browser and Webdriver process NOT killed !!!!")


    def config_browser(self, *args, **kwargs):
        print("Configuring browser...")
        chrome_driver_path = CHROME_FOLDER / 'chromedriver.exe'
        self.kill_browser_process()
        options = Options()
        options.page_load_strategy = "none"
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-gpu-blacklist")
        options.add_argument("--use-gl")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--ignore-ssl-errors=yes")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--block-insecure-private-network-requests=false")
        options.add_argument(f"--unsafely-treat-insecure-origin-as-secure={SITE_DOMAIN}")
        options.add_argument("--safebrowsing-disable-download-protection")
        options.add_argument("--disable-gpu")
        if self.invisible:
            print("Configuring browser with invisible mode!")
            options.add_argument("--headless")
        else:
            print("Configuring browser with visible mode!")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.user_agent}")
        options.add_argument("--kiosk-printing")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-notifications")
        options.add_argument(f"user-data-dir={USER_DATA_DIR.absolute()}")
        options.set_capability("acceptInsecureCerts", True)
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        prefs = {
            "profile.default_content_setting_values.notifications" : 2,
            "safebrowsing_for_trusted_sources_enabled" : False,
            "safebrowsing.enabled" : False,
            "profile.exit_type" : "Normal"
        }
        options.add_experimental_option("prefs", prefs)
        os.environ["webdriver.chrome.driver"] = str(chrome_driver_path.absolute())
        service = Service(executable_path=chrome_driver_path, service_args=["--verbose"])
        self.browser = webdriver.Chrome(service=service, options=options)
        self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.browser.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent":self.user_agent})
        self.browser.set_page_load_timeout(self.page_load_timeout)
        self.browser.maximize_window()
        print("browserVersion: ", self.browser.capabilities["browserVersion"])
        print("chromedriverVersion: ", self.browser.capabilities["chrome"]["chromedriverVersion"].split(" ")[0])
        if not self.test_browser_ok():
            self.retry += 1
            if self.retry<=self.max_retries:
                self.config_browser()
            else:
                raise Exception("Failed to configure browser. Possible reason: Blocked Proxy server")
        else:
            self.retry = 0

        
    def get_clickable_element(self, by_tuple):
        el = None
        try:
            el = WebDriverWait(self.browser, 20).until(EC.presence_of_element_located(by_tuple))
            el1 = WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(by_tuple))
            if el1 is not None:
                el = el1
        except Exception as e:
            print("WhatsAppScraper.get_clickable_element Error: ", e)
        return el


    def login(self):
        if self.get_page(LOGIN_URL, LOGIN_TITLE):
            time.sleep(3)
            qrcode_el = self.browser.find_elements(By.XPATH, "//div[@data-testid='qrcode']")
            if len(qrcode_el)==0:return True
            print("Please scan the QR Code to login!")
            while True:
                if confirmation_input("Done with scanning QR code?", 'y/N')==True:
                    qrcode_el = self.browser.find_elements(By.XPATH, "//div[@data-testid='qrcode']")
                    if len(qrcode_el)==0:
                        time.sleep(1)
                        print(f"Waiting for login redirect title {LOGIN_REDIRECT_TITLE}!")
                        if not self.is_page_ready(LOGIN_REDIRECT_TITLE):
                            if not self.is_title_valid(LOGIN_REDIRECT_TITLE):
                                print("Couldn't login!!! Re-loging....")
                                return self.login()
                        time.sleep(3)
                        return True
                    else:
                        print("Scanning not done yet! Please scan the QR code...")
        return False
        
    def get_names_mobile(self):
        names = []
        mobiles = []
        is_popup = True
        try:
            soup = BeautifulSoup(self.browser.page_source, "html.parser")
            listitem = soup.select("div[data-testid='popup-contents'] div[data-testid='contacts-modal'] div[role='listitem']")
            if listitem is None or len(listitem)==0:
                listitem = soup.select("div[data-testid='drawer-right'] div[data-testid='group-info-participants-section'] div[id='pane-side'] div[role='list'] div[role='listitem']")
                is_popup = False
            else:
                print("Fetching participants from popup")
                by_tuple = (By.XPATH, "//div[@data-testid='popup-contents']//div[@data-testid='contacts-modal']//div[@role='listitem']")
                el = self.get_clickable_element(by_tuple)
                listitem1 = []
                listitem2 = []
                listitem3 = []
                for y in range(0, 100000, 800):
                    self.browser.execute_script(f"arguments[0].parentElement.parentElement.parentElement.parentElement.scroll(0, {y})", el)
                    soup = BeautifulSoup(self.browser.page_source, "html.parser")
                    listitem1 = soup.select("div[data-testid='popup-contents'] div[data-testid='contacts-modal'] div[role='listitem']")
                    if listitem1!=listitem2:
                        listitem2 = listitem1
                        listitem3 += listitem1
                    else:
                        if len(listitem3)>0:
                            listitem += listitem3
                        break
                    time.sleep(0.1)
            for item in listitem:
                name_el = item.select("div[data-testid='cell-frame-title'] span")
                name = None
                if len(name_el)>0:
                    name = name_el[0].text
                mobile_el = item.select("div[data-testid='cell-frame-secondary'] div[role='gridcell'] span span")
                if len(mobile_el)>0:
                    mobile = mobile_el[0].text
                    if mobile is None:
                        mobile = ""
                    if mobile not in mobiles or (name is not None and name not in names):
                        names.append(name)
                        mobiles.append(mobile)
                elif name is not None and name not in names:
                    names.append(name)
                    mobiles.append("")
        except Exception as e:
            print("WhatsAppScraper.get_mobiles Error: ", e, traceback.format_exc())
        return names, mobiles, is_popup

    def check_and_click_more(self):
        done = False
        try:
            by_tuple = (By.XPATH, "//div[@data-testid='drawer-right']//div[@data-testid='group-info-participants-section']//div[@role='button' and @data-ignore-capture='any']//span[@data-testid='down' or contains(., 'View all')]")
            el = self.get_clickable_element(by_tuple)
            if el:
                el.click()
                time.sleep(0.5)
                done = True
        except:
            done = False
        return done

    def close_popup_contacts(self):
        by_tuple = (By.XPATH, "//div[@data-testid='popup-contents']//div[@data-testid='contacts-modal']//div[@role='button']//span[@data-testid='x']")
        el = self.get_clickable_element(by_tuple)
        if el:
            el.click()

    def close_group_info(self):
        by_tuple = (By.XPATH, "//div[@data-testid='drawer-right']//div[@data-testid='chat-info-drawer']//header//div[@data-testid='btn-closer-drawer']//span[@data-testid='x']")
        el = self.get_clickable_element(by_tuple)
        try:
            if el:
                el.click()
        except Exception as e:
            print("WhatsAppScraper.close_group_info Error: ", e, traceback.format_exc())
        
    def get_name_mobile_list(self, group_name):
        try:
            names = []
            mobiles = []
            
            by_tuple = (By.XPATH, f"//div[@id='main']//header[@data-testid='conversation-header']//div[@data-testid='conversation-info-header']//span[@data-testid='conversation-info-header-chat-title'][contains(text(), '{group_name}')]")
            el = self.get_clickable_element(by_tuple)
            if el:
                el.click()
            
                by_tuple = (By.XPATH, "//div[@data-testid='drawer-right']//section[@data-testid='group-info-drawer-body']")
                el = self.get_clickable_element(by_tuple)

                if el:
                    el.click()
                    el = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.XPATH, "//body")))
                    for _ in range(0, 12):
                        el.send_keys(Keys.TAB)
                        time.sleep(0.02)
                    time.sleep(0.2)
                    el.send_keys(Keys.END)
                    time.sleep(0.2)
                    self.check_and_click_more()
                    names, mobiles, is_popup = self.get_names_mobile()
                    if is_popup:
                        self.close_popup_contacts()
                    self.close_group_info()
                    self.clear_search()
        except Exception as e:
            print("WhatsAppScraper.get_name_mobile_list Error: ", e , traceback.format_exc())        
        return names, mobiles

    def remove_special_chars(self, val):
        try:
            if val is not None:
                val = str(val)
                # val1 = ' '.join(filter(None, [v.strip() if v.isalnum() else '' for v in val.split(' ')]))
                val1 = val.replace(">>", "").replace("/", "").replace("\\", "")
                val = val1
        except Exception as e:
            print("WhatsAppScraper.remove_special_chars Error: ", e, traceback.format_exc())
        return val


    def parse_and_save(self, group_name):
        try:
            saved = False
            names = []
            mobiles = []
            names, mobiles = self.get_name_mobile_list(group_name)
            if len(names)>0:
                filepath = DATA_DIR / f"{self.remove_special_chars(group_name)}.xlsx"
                df = pd.DataFrame({
                                "Name": names, 
                                "Mobile": mobiles, 
                            })
                sheet_name = "Participants"
                while True:
                    try:
                        with pd.ExcelWriter(path=str(filepath.absolute()), engine="openpyxl") as writer:
                            df.to_excel(excel_writer=writer, sheet_name=sheet_name, index=False)
                        print(f"{len(mobiles)} participants have been saved in sheet '{sheet_name}' at '{filepath}'")
                        saved = True
                        break
                    except Exception as e:
                        print("WhatsAppScraper.parse_and_save Error1: ", e, traceback.format_exc())
                        if confirmation_input("Try again?", "y/N")==False:
                            print("Data not saved. Procceeding to next!")
                            break                    
            else:
                print(f"Group {group_name} has no participants.")
        except Exception as e:
            print("WhatsAppScraper.parse_and_save Error2: ", e, traceback.format_exc())
        return saved

    def _get_group_names(self):
        chat_names = []
        group_names = []
        try:
            els = self.browser.find_elements(By.XPATH, "//div[@id='pane-side']//div[@aria-label='Chat list']//div[@role='listitem']//div[@data-testid='cell-frame-container']//div[@data-testid='cell-frame-title']//span")
            for el in els:
                try:
                    chat_names.append(el.text)
                    is_normal_chat = self.browser.execute_script("""return (arguments[0].parentElement.parentElement.parentElement.parentElement.querySelector("div[data-testid='chatlist-status-v3-ring']")!=null);""", el)
                    if not is_normal_chat:
                        group_names.append(el.text)
                except StaleElementReferenceException as e:
                    print("WhatsAppScraper._get_group_names Error1: ", e)
        except Exception as e:
            print("WhatsAppScraper._get_group_names Error2: ", e, traceback.format_exc())    
        return (list(set(chat_names)), list(set(group_names)))

    def get_group_names(self):
        chat_names = []
        group_names = []
        try:
            chat_names1, group_names1 = self._get_group_names()
            chat_names += chat_names1
            group_names += group_names1
            el = self.get_clickable_element((By.XPATH, "//div[@data-testid='chat-list']"))
            if el:
                el.click()
                el = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.XPATH, "//body")))
                el.send_keys(Keys.TAB)
                el.send_keys(Keys.TAB)
                el.send_keys(Keys.TAB)
                el.send_keys(Keys.TAB)
                el.send_keys(Keys.TAB)
                chat_names2 = []
                while True:
                    for _ in range(0, 8):
                        el.send_keys(Keys.DOWN)
                        time.sleep(0.03)
                    time.sleep(0.15)
                    chat_names1, group_names1 = self._get_group_names()
                    if chat_names1!=chat_names2:
                        chat_names2 = chat_names1
                        group_names += group_names1
                    else:
                        break
        except Exception as e:
            print("WhatsAppScraper.get_group_names Error: ", e, traceback.format_exc())
        group_names = list(filter(None, sorted(set(group_names))))
        with open(GROUP_NAMES_PATH, "w", encoding="UTF-8") as fp:
            json.dump(obj=group_names, fp=fp, indent=4)
        return group_names

    def clear_search(self):
        try:
            by_tuple = (By.XPATH, "//div[@data-testid='chat-list-search-container']//button[@aria-label='Cancel search']")
            el = self.get_clickable_element(by_tuple)
            if el:
                el.click()
        except:
            pass

    def find_and_get_group(self, group_name):
        self.clear_search()
        els = self.browser.find_elements(By.XPATH, "//div[@data-testid='chat-list-search']//p")
        if len(els)>0:
            el = els[0]
            el.send_keys(group_name)
            time.sleep(0.5)
            l = len(group_name)
            error = ""
            r = int(30*l/100)
            if r==0:
                r = 1
            for i in range(0, r):
                try:
                    truncated_group_name = group_name[:l-i]
                    print("truncated_group_name: ", truncated_group_name)
                    by_tuple = (By.XPATH, f"//div[@id='pane-side']//div[@aria-label='Search results.']//div[@role='listitem']//div[@data-testid='cell-frame-container']//div[@data-testid='cell-frame-title']//span[contains(text(), '{truncated_group_name}')]")
                    el = self.get_clickable_element(by_tuple)
                except Exception as e:
                    error = str(e)
                    el = None
            if el:
                el.click()
                time.sleep(1)
                return True
            else:
                print("WhatsAppScraper.find_and_get_group Error: ", error)
        return False

    def ask_target_group_name(self, group_names):
        print()
        for i, group_name in enumerate(sorted(group_names)):
            print(f"[{i+1}: {group_name}]")
        print()
        if len(group_names)>0:
            print("The format printed above is --> [index: group name]")
            while True:
                idx = input("Please type the group index number to be processed: ")
                if idx is not None and idx!="":
                    try:
                        idx = int(idx)
                        group_name = group_names[idx-1]
                        group_names = [group_name.strip()]
                        break
                    except:
                        if idx in group_names:
                            group_names = [idx]
                            break
                        elif confirmation_input("Invalid index passed! Try again?", "Y/n")==False:
                            break
        return group_names
            


    def start_scraping(self):
        try:
            max_retries = 3
            retry = 0
            while True:
                try:
                    self.config_browser()
                    break
                except Exception as e:
                    print("WhatsAppScraper.start_scraping Error: ", e, traceback.format_exc())
                    retry += 1
                if retry>max_retries:
                    raise Exception("Browser can't be configured at this moment!")
            time.sleep(1)
            if self.login():
                WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
                group_names = []
                while True:
                    if confirmation_input("Sync the group names?", "N/y")==True:
                        print("Fetching group names...")
                        group_names = self.get_group_names()
                    else:
                        if GROUP_NAMES_PATH.exists():
                            print("Loading group names...")
                            with open(GROUP_NAMES_PATH, "r", encoding="UTF-8") as fp:
                                group_names = json.load(fp)
                        else:
                            break
                    if len(group_names)==0:
                        print("No group name found!!!")
                    else:
                        break
                
                while len(group_names)>0:
                    target_group_names = self.ask_target_group_name(group_names)
                    for i, group_name in enumerate(target_group_names):
                        if confirmation_input(f"Process group name: {group_name}", 'y/N')==False:continue
                        try:
                            while True:
                                print(f"Processing group name: {group_name}")
                                try:
                                    found = self.find_and_get_group(group_name)
                                    if found:
                                        if self.parse_and_save(group_name)==True:break
                                    else:
                                        print(f"Couldn't find group: {group_name}")
                                        if confirmation_input(f"Retry with re-configuring and re-login...", "N/y")==True:
                                            return self.start_scraping()
                                        else:
                                            print(f"Trying to find the group {group_name} again...")
                                except Exception as e:
                                    print("WhatsAppScraper.start_scraper Error: ", e, traceback.format_exc())
                                    print(f"Skipping group: {group_name}")
                                    break
                            print("####################################################################")
                            print()
                        except Exception as e:
                            print("WhatsAppScraper.start_scraping Error1: ", e, traceback.format_exc())
                    print("######################## DONE ########################")
                    print()
                    if confirmation_input("Process again?", "Y/n")==False:
                        break
                print("######################## COMPLETED ########################")
        except Exception as e:
            print("WhatsAppScraper.start_scraping Error2: ", e, traceback.format_exc())
        self.kill_browser_process()
            
                    


if __name__ == "__main__":
    argv = sys.argv
    parser = argparse.ArgumentParser(prog=f"{argv[0].split(os.sep)[-1]}", description="WhatsApp Scraper")
    parser.version = '1.0'
    parser.add_argument("-v", "--version", action="version", version=parser.version)
    parser.add_argument(
        "-inviz",
        "--invisible",
        dest="INVISIBLE",
        action='store_true',
        default=False,
        required=False,
        help="Run script with visible mode, default: visible"
    )

    args = parser.parse_args(argv[1:])
    print(parser.description)
    INVISIBLE = args.INVISIBLE
    print("INVISIBLE: ", INVISIBLE)
    wp_scraper = WhatsAppScraper(invisible=INVISIBLE)
    wp_scraper.start_scraping()

