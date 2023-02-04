"""Connect to sickw and return a SickwResults object with data from serial_number and service """
import os
import json
from typing import List
from bs4 import BeautifulSoup
import requests
from modules import load_config as config

print(f"Importing {os.path.basename(__file__)}...")

APPLE_SERIAL_INFO = 26


class SickwResults:
    """Object built from sickw API results"""

    result_id: int = 0
    status: str
    serial_number: str
    description: str = ""
    name: str = ""
    a_number: str = ""
    model_id: str = ""
    capacity: str = ""
    color: str = ""
    type: str = ""
    year: int = 0

    def __init__(self, serial_number: str, service: int) -> None:
        self.serial_number = serial_number
        sickw_return = json.loads(self.get_json(serial_number, service))
        if sickw_return["status"].lower() == "success":
            sickw_return_dict = self.html_to_dict(sickw_return["result"])
            if len(sickw_return_dict) > 0:
                self.result_id = sickw_return["id"]
                self.status = sickw_return["status"]
                self.description = sickw_return_dict["Model Desc"]
                self.name = sickw_return_dict["Model Name"]
                self.a_number = sickw_return_dict["Model Number"]
                self.model_id = sickw_return_dict["Model iD"]
                self.capacity = sickw_return_dict["Capacity"]
                self.color = sickw_return_dict["Color"]
                self.type = sickw_return_dict["Type"]
                self.year = sickw_return_dict["Year"]
                return
        self.status = "failed"

    def get_json(self, serial_number: str, service: int):
        """Get requested data from Sickw API"""
        current_params = {"imei": serial_number, "service": service, "key": config.SICKW_API_KEY, "format": "JSON"}
        headers = {"User-Agent": "My User Agent 1.0"}
        response = requests.get("https://sickw.com/api.php", params=current_params, headers=headers, timeout=60)
        # response_text = BeautifulSoup(response.text).get_text()
        return response.text

    def html_to_dict(self, html: str):
        """generate dict from html returned in result"""
        soup = BeautifulSoup(html, "html.parser")
        return_dict = {}
        for line in soup.findAll("br"):
            br_next = line.nextSibling
            if br_next != line and br_next is not None:
                data = br_next.split(":")
                return_dict[data[0]] = data[1].strip()
                # return_list.append(br_next)

        return return_dict

    @staticmethod
    def search_list_for_serial(serial: str, sickw_history: "List[SickwResults]") -> str:
        for result in sickw_history:
            if result.serial_number == serial:
                return result.name, result.status

    @staticmethod
    def success_count(sickw_history: "List[SickwResults]") -> int:
        return_count = 0
        for result in sickw_history:
            if result.name:
                return_count += 1

        return return_count