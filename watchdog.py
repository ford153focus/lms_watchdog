#!/usr/bin/python3

import json
import os
import platform
import psutil
import requests
import socket
from dotenv import load_dotenv

_dir = os.path.dirname(os.path.abspath(__file__))

load_dotenv()

class Slack:
    @staticmethod
    def send_message(message_text):
        url = "https://slack.com/api/chat.postMessage"
        token = os.environ["SLACK_TOKEN"]
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(token)
        }
        message = {
            "channel": "#buspay_zabbix",
            "text": message_text
        }
        requests.post(url, headers=headers, data=json.dumps(message))


class WatchDog:
    config = {}
    counters = {}

    host = platform.node()

    def cpu_usage(self):
        for check in self.config["cpu_watcher"]:
            if psutil.cpu_percent() > check['critical_value']:
                self.counters["counters"]["cpu"][str(check['critical_value'])] = int(
                    self.counters["counters"]["cpu"].get(str(check['critical_value'])) or 0) + 1
                if self.counters["counters"]["cpu"][str(check['critical_value'])] >= check['attempts_before_fail']:
                    Slack.send_message(
                        "{0} :: CPU usage is over than {1}% for more than {2} minutes!".format(
                            self.host,
                            check['critical_value'],
                            self.counters["counters"]["cpu"][str(
                                check['critical_value'])]
                        )
                    )
            else:
                self.counters["counters"]["cpu"][str(
                    check['critical_value'])] = 0

    def ram_usage(self):
        mem_usage = dict(psutil.virtual_memory()._asdict())

        for check in self.config["ram_watcher"]:
            if (mem_usage['total']-mem_usage['used'])/1024/1024 < check['critical_value']:
                self.counters["counters"]["ram"][str(check['critical_value'])] = int(
                    self.counters["counters"]["ram"].get(str(check['critical_value'])) or 0) + 1
                if self.counters["counters"]["ram"][str(check['critical_value'])] >= check['attempts_before_fail']:
                    Slack.send_message(
                        "{0} :: Free RAM is less than {1} mb for more than {2} minutes!".format(
                            self.host,
                            check['critical_value'],
                            self.counters["counters"]["ram"][str(
                                check['critical_value'])]
                        )
                    )
            else:
                self.counters["counters"]["ram"][str(
                    check['critical_value'])] = 0

    def disk_capacity_usage(self):
        st = os.statvfs("/")

        free = (st.f_bavail * st.f_frsize)
        # total = (st.f_blocks * st.f_frsize)
        # used = (st.f_blocks - st.f_bfree) * st.f_frsize

        free_gb = free/1024/1024/1024

        for check in self.config["disk_watcher"]:
            if free_gb < check['critical_value']:
                self.counters["counters"]["disk"][str(check['critical_value'])] = int(
                    self.counters["counters"]["disk"].get(str(check['critical_value'])) or 0) + 1
                if self.counters["counters"]["disk"][str(check['critical_value'])] >= check['attempts_before_fail']:
                    Slack.send_message(
                        "{0} :: Free disk space is less than {1} gb for more than {2} minutes!".format(
                            self.host,
                            check['critical_value'],
                            self.counters["counters"]["disk"][str(
                                check['critical_value'])]
                        )
                    )
            else:
                self.counters["counters"]["disk"][str(
                    check['critical_value'])] = 0

    def host_availability(self):
        if self.host == "zabbix":
            for check in self.config["host_availability"]:
                for port in check["ports"]:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        result = sock.connect_ex((check['host'], port))
                        if result != 0:
                            Slack.send_message("{0} :: port {1} on server is not answering! (reported by {2})".format(check["host"], port, self.host))
                    except Exception as e:
                        Slack.send_message("Failed to scan port {0} on server {1}: {2})".format(port, check["host"], str(e)))

    def __init__(self):
        # read config from json-file
        self.config = json.load(open(_dir+"/config.json", "r"))
        # read counters from json-file
        self.counters = json.load(open(_dir+"/counters.json", "r"))

        self.cpu_usage()
        self.ram_usage()
        self.disk_capacity_usage()
        self.host_availability()

        # write counters to json-file
        json.dump(self.counters, open(_dir+"/counters.json", "w"))


_ = WatchDog()
