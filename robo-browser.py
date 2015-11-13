#!/usr/bin/env python3
#
# robo-browser.py gets the next website from the robotask API and browses to it using
# a selenium webdriver with the scriptobservatory chrome extension installed. It repeats 
# this forever, using a "fake" Xvfb display to run headlessly.
#

import json
import logging
import multiprocessing
import os
import random
import requests
import subprocess
import sys
import time

import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from xvfbwrapper import Xvfb


API_BASE_URL = "https://scriptobservatory.org/api/robotask"
LOG_FILE = os.environ['LOG_FILEPATH']

MAX_RANDOM_CHOICE_TASKS = 25

N_SECS_TO_WAIT_FOR_CHROME_EXT = 5
N_SECS_ON_DELETE_FAIL = 5
N_SECS_TO_WAIT_AFTER_ONLOAD = 10
N_SECS_TO_WAIT_AFTER_ERR = 20
N_SECS_WHEN_NO_TASKS_FOUND = 30
N_SECS_REQ_TIMEOUT = 70
N_SECS_HARD_REQ_TIMEOUT = 90

USER_AGENT_STR = "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)"

OPTIONS = Options()
OPTIONS.add_argument("--user-agent={0}".format(USER_AGENT_STR))
OPTIONS.add_argument("--load-extension={0}".format(os.environ['PATH_TO_EXTENSION']))
OPTIONS.add_argument("--disable-application-cache")

# there are issues with using Chrome's sandbox in Travis-CI's environment
if 'TRAVIS' in os.environ:
    OPTIONS.add_argument("--no-sandbox")


def get_next_robotask():
    """ gets the (url, priority, task_id) of next task """
    response = requests.get(API_BASE_URL, 
                            params=dict(q=json.dumps(dict(order_by=[dict(field='priority', direction='asc')],
                                                          results_per_page=MAX_RANDOM_CHOICE_TASKS))),
                            headers={'Content-Type': 'application/json'},
                            verify=False)

    if response.status_code != 200:
        return (None, None, None)

    task_data = response.json()
    tasks = task_data["objects"]
    n_tasks = len(tasks)
    
    if n_tasks == 0:
        return (None, None, None)

    # we choose randomly from up to the first *max_tasks* tasks that all have the same priority
    # level as the first task (which has the highest priority because of sort order).
    max_tasks = MAX_RANDOM_CHOICE_TASKS if n_tasks > MAX_RANDOM_CHOICE_TASKS else n_tasks  # probably unnecessary
    task_choices = [t for t in tasks[:max_tasks] if t["priority"] == tasks[0]["priority"]]
    current_task = random.choice(task_choices)
    
    # TODO: may need to catch requests.exceptions.ConnectionError
    return (current_task["url"], current_task["priority"], current_task["id"])


def delete_robotask(task_id):
    """ deletes the task with id *task_id* from the robotask API or return -1 on error """
    response = requests.delete("{0}/{1}".format(API_BASE_URL, task_id), verify=False)
    
    if response.status_code != 204:
        # a non-204 status is most often returned if someone else has already deleted the task. We return
        # -1 so we can go and get the next task instead of running this one 
        return -1


def fetch_webpage(url):
    """ fetch_webpage creates a chrome webdriver and navigates to *url* """
    try:
        logging.warn("in fetch_webpage()")
        driver = webdriver.Chrome(chrome_options=OPTIONS) 
        logging.warn("finished creating webdriver")
        driver.set_page_load_timeout(N_SECS_REQ_TIMEOUT)
        time.sleep(N_SECS_TO_WAIT_FOR_CHROME_EXT)
        driver.get(url)
        time.sleep(N_SECS_TO_WAIT_AFTER_ONLOAD)
        logging.warn("done!")
    
    except selenium.common.exceptions.WebDriverException as e:
        logging.error("tab crashed! err: {0}".format(e))

    except selenium.common.exceptions.TimeoutException as e:
        logging.error("the page load timed out! err: {0}".format(e))

    finally:
        driver.quit()


if __name__ == "__main__":
    if 'TRAVIS' in os.environ:
        logging.basicConfig(level=logging.WARN)
    else:
        logging.basicConfig(filename=LOG_FILE, level=logging.WARN)
        
    logging.warn("number of chrome / python processes: {0}".format(subprocess.check_output("ps aux | grep -i \"chrome\|python\" | wc -l", shell=True)))

    url, priority, task_id = get_next_robotask()
    
    if url is None:
        logging.warn("no tasks found! sleeping for {0} seconds then continuing...".format(N_SECS_WHEN_NO_TASKS_FOUND))
        time.sleep(N_SECS_WHEN_NO_TASKS_FOUND)
        exit()

    logging.warn("got task for url: {0}".format(url))
    
    if delete_robotask(task_id) is not None:
        logging.warn("error when calling delete_robotask()! (someone else probably got this task)")
        time.sleep(N_SECS_ON_DELETE_FAIL)
        exit()

    vdisplay = Xvfb()
    vdisplay.start()
    p = multiprocessing.Process(target=fetch_webpage, args=(url,))
    
    try:
        p.start()
        p.join(N_SECS_HARD_REQ_TIMEOUT)
    
    except subprocess.CalledProcessError as e:
        logging.error("ERROR: CalledProcessError {0} -- continuing on...".format(e))
        time.sleep(N_SECS_TO_WAIT_AFTER_ERR)

    finally:
        if p.is_alive():
            p.terminate()
    
    vdisplay.stop()
