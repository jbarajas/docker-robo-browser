#!/usr/bin/env python3
#

import json
import logging
import psycopg2
import requests
import sys
import time


API_BASE_URL = "https://www.scriptobservatory.org/api/robotask"


def add_list_file(list_filename, priority):
    for line in open(list_filename, 'r'):
        url = line.strip()

        task = {'url': url, 'priority': priority}

        cursor.execute("INSERT INTO robotask(url, priority) VALUES(%s,%s)", (url, priority))
        
        time.sleep(0.001)


if __name__ == "__main__":
    logging.basicConfig(filename="/opt/scheduler-log.txt", level=logging.WARN)
    logging.warn("current time: {0}".format(time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())))
    logging.warn("being called with: {0}".format(sys.argv))

    priority = int(sys.argv[1])
    
    for arg in sys.argv[2:]:
        # we make sure the file is really a domain list by checking for the .list ending
        if arg.endswith(".list"):
            logging.warn("adding {0} at priority {1}".format(arg, priority))
            
            conn = psycopg2.connect("postgres://postgres@/postgres")
            cursor = conn.cursor()
    
            add_list_file(arg, priority)
    
            conn.commit()
            conn.close()
        
            logging.warn("done!")
