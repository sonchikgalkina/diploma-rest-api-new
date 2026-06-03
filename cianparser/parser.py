import itertools
import time
from bs4 import BeautifulSoup
import re
import cloudscraper
import math
import psycopg2
import cianparser.coefficient_dictionaries as dicts
from cianparser.constants import *
from cianparser.helpers import *



class ParserOffers:
    def __init__(self, rooms):
        self.session = cloudscraper.create_scraper()
        self.session.headers = {'Accept-Language': 'en'}
        self.is_saving_csv = True
        self.is_latin = False
        self.result_parsed = set()
        self.result = []
        self.rooms = rooms
        self.start_page = 1
        self.end_page = 15
        self.average_price = 0
        self.parsed_announcements_count = 0
        self.url = None
    def build_url(self):
        rooms_path = ""
        if type(self.rooms) is tuple:
            for count_of_room in self.rooms:
                if type(count_of_room) is int:
                    if count_of_room > 0 and count_of_room < 6:
                        rooms_path += ROOM.format(count_of_room)
                elif type(count_of_room) is str:
                    if count_of_room == "studio":
                        rooms_path += "&room9=1"
                        self.rooms = 0
        elif type(self.rooms) is int:
            if self.rooms > 0 and self.rooms < 6:
                rooms_path += ROOM.format(self.rooms)
        elif type(self.rooms) is str:
            if self.rooms == "studio":
                rooms_path += "&room9=1"
                self.rooms = 0
            elif self.rooms == "all":
                rooms_path = ""
        url = "https://cian.ru/cat.php?engine_version=2&p={}&region={}" + "&offer_type=flat&deal_type=rent&with_neighbors=0" + rooms_path
        url += "&type=4"
        return url

    def load_page(self, number_page=1):
        self.url = self.build_url().format(number_page, 1)
        res = self.session.get(url=self.url)
        res.raise_for_status()
        return res.text

    def parse_page(self, html: str, number_page: int, count_of_pages: int, attempt_number: int):
        try:
            soup = BeautifulSoup(html, 'lxml')
        except:
            soup = BeautifulSoup(html, 'html.parser')

        header = soup.select("div[data-name='HeaderDefault']")
        if len(header) == 0:
            return False, attempt_number + 1, True

        offers = soup.select("article[data-name='CardComponent']")
        page_number_html = soup.select("button[data-name='PaginationButton']")
        if len(page_number_html) == 0:
            return False, attempt_number + 1, True

        if page_number_html[0].text == "Назад" and (number_page != 1 and number_page != 0):
            return True, 0, True

        if number_page == self.start_page:
            print(f"The page from which the collection of information begins: \n {self.url} \n")
            print(f"Collecting information from pages with list of announcements", end="")

        print("")
        print(f"\r {number_page} page: {len(offers)} offers", end="\r", flush=True)

        for ind, block in enumerate(offers):
            self.parse_block(block=block)
            total_planed_announcements = len(offers)*count_of_pages

            print(f"\r {number_page - self.start_page + 1} | {number_page} page with list: [" + "=>" * (
                        ind + 1) + "  " * (
                          len(offers) - ind - 1) + "]" + f" {math.ceil((ind + 1) * 100 / len(offers))}" + "%" +
                  f" | Count of all parsed: {self.parsed_announcements_count}."
                  f" Progress ratio: {math.ceil(self.parsed_announcements_count * 100 / total_planed_announcements)} %."
                  f" Average price: {'{:,}'.format(int(self.average_price)).replace(',', ' ')} rub", end="\r",
                  flush=True)

        time.sleep(5)

        return True, 0, True

    def define_location_data(self, block):
        elements = block.select("div[data-name='LinkArea']")[0]. \
            select("div[data-name='GeneralInfoSectionRowComponent']")

        location_data = dict()
        location_data["region"] = ""
        location_data["district"] = ""
        location_data["street"] = ""
        location_data["underground"] = ""
        location_data["house"] = ""

        for index, element in enumerate(elements):
            if "р-н" in element.text:
                address_elements = element.text.split(",")
                if len(address_elements) < 2:
                    continue
                location_data["time_to_underground"] = int((''.join(re.findall('(\d+)', address_elements[0].strip()))).replace("1905",''))
                location_data["region"] = address_elements[1].strip()
                location_data["district"] = address_elements[2].strip()
                location_data["underground"] = address_elements[3].strip()
                location_data["street"] = address_elements[-2].strip()
                location_data["house"] = address_elements[-1].strip()
        return location_data

    def define_price_data(self, block):
        elements = block.select("div[data-name='LinkArea']")[0]. \
            select("div[data-name='GeneralInfoSectionRowComponent']")

        price_data = {
            "price_per_month": -1,
            "commissions": 0,
        }

        for element in elements:
            if "₽/мес" in element.text:
                price_description = element.text
                price_data["price_per_month"] = int("".join(price_description[:price_description.find("₽/мес") - 1].split()))

                if "%" in price_description:
                    price_data["commissions"] = int(price_description[price_description.find("%") - 2:price_description.find("%")].replace(" ", ""))

                return price_data

            if "₽" in element.text:
                price_description = element.text
                price_data["price"] = int("".join(price_description[:price_description.find("₽") - 1].split()))

                return price_data

        return price_data

    def define_specification_data(self, block):
        title = block.select("div[data-name='LinkArea']")[0].select("div[data-name='GeneralInfoSectionRowComponent']")[
            0].text

        common_properties = block.select("div[data-name='LinkArea']")[0]. \
            select("div[data-name='GeneralInfoSectionRowComponent']")[0].text

        total_meters = None
        if common_properties.find("м²") is not None:
            total_meters = title[: common_properties.find("м²")].replace(",", ".")
            if len(re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", total_meters)) != 0:
                total_meters = float(re.findall(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", total_meters)[-1].replace(" ", "").replace("-", ""))
            else:
                total_meters = -1

        if "этаж" in common_properties:
            floor_per = common_properties[common_properties.rfind("этаж") - 7: common_properties.rfind("этаж")]

            floor_per = floor_per.split("/")

            if len(floor_per) == 0:
                floor, floors_count = -1, -1
            else:
                floor, floors_count = floor_per[0], floor_per[1]

            ints = re.findall(r'\d+', floor)
            if len(ints) == 0:
                floor = -1
            else:
                floor = int(ints[-1])

            ints = re.findall(r'\d+', floors_count)
            if len(ints) == 0:
                floors_count = -1
            else:
                floors_count = int(ints[-1])
        else:
            floors_count = -1
            floor = -1

        return {
            "floor": floor,
            "floors_count": floors_count,
            "rooms_count": define_rooms_count(common_properties),
            "total_meters": total_meters,
        }

    def parse_block(self, block):
        common_data = dict()
        common_data["link"] = block.select("div[data-name='LinkArea']")[0].select("a")[0].get('href')
        location_data = self.define_location_data(block=block)
        price_data = self.define_price_data(block=block)
        specification_data = self.define_specification_data(block=block)
        page_data = dict()

        specification_data["price_per_m2"] = float(0)
        if "price" in price_data:
            self.average_price = (self.average_price*self.parsed_announcements_count + price_data["price"])/(self.parsed_announcements_count+1)
            price_data["price_per_m2"] = int(float(price_data["price"])/specification_data["total_meters"])
        elif "price_per_month" in price_data:
            self.average_price = (self.average_price*self.parsed_announcements_count + price_data["price_per_month"])/(self.parsed_announcements_count+1)
            price_data["price_per_m2"] = int(float(price_data["price_per_month"])/specification_data["total_meters"])

        self.parsed_announcements_count += 1

        if define_id_url(common_data["link"]) in self.result_parsed:
            return
        self.result_parsed.add(define_id_url(common_data["link"]))
        self.result.append(self.union(common_data, specification_data, price_data, page_data, location_data))

        if self.is_saving_csv:
            self.save_result()

    def union(self, *dicts):
        return dict(itertools.chain.from_iterable(dct.items() for dct in dicts))

    def save_result(self):
        self.result
        conn = psycopg2.connect(dbname='diplomaBackend', user='postgres', host='db', password='123456')
        cursor = conn.cursor()

        for val in self.result[len(self.result)-1].values():
            if val == '' or val == None:
                self.result.pop(0)
                return
            if (isinstance(val, int) and val < 0):
                self.result.pop(0)
                return

        if (self.result[len(self.result)-1]["district"] not in dicts.common_ecology_dict.keys() or self.result[len(self.result)-1]["region"] not in dicts.criminality_dict.keys()):
                self.result.pop(0)
                return
        self.result[0]["rooms"] = self.rooms
        self.result[0]["common_ecology_coeff"] = dicts.common_ecology_dict[self.result[0]["district"]]
        self.result[0]["population_density_coeff"] = dicts.population_density_dict[self.result[0]["district"]]
        self.result[0]["green_spaces_coeff"] = dicts.green_spaces_dict[self.result[0]["district"]]
        self.result[0]["negative_impact_coeff"] = dicts.negative_impact_dict[self.result[0]["district"]]
        self.result[0]["phone_nets_coeff"] = dicts.phone_nets_dict[self.result[0]["district"]]
        self.result[0]["crime_coeff"] = dicts.criminality_dict[self.result[0]["region"]]

        cursor.execute("INSERT INTO rest_api_flat(link, floor, floors_count, total_meters, price_per_m2, price_per_month, commissions, region, district, street, underground, house, rooms, time_to_underground ,common_ecology_coeff, population_density_coeff, green_spaces_coeff, negative_impact_coeff, phone_nets_coeff, crime_coeff) VALUES (\'{}\', {}, {}, {}, {}, {}, {}, \'{}\', \'{}\', \'{}\', \'{}\', \'{}\', {}, {}, {}, {}, {}, {}, {}, {}) on conflict do nothing;".format(
            self.result[0]["link"],
                  self.result[0]["floor"],
                  self.result[0]["floors_count"],
                  self.result[0]["total_meters"],
                  self.result[0]["price_per_m2"],
                  self.result[0]["price_per_month"],
                  self.result[0]["commissions"],
                  self.result[0]["region"],
                  self.result[0]["district"],
                  self.result[0]["street"],
                  self.result[0]["underground"],
                  self.result[0]["house"],
                  self.result[0]["rooms"],
                  self.result[0]["time_to_underground"],
                  self.result[0]["common_ecology_coeff"],
                  self.result[0]["population_density_coeff"],
                  self.result[0]["green_spaces_coeff"],
                  self.result[0]["negative_impact_coeff"],
                  self.result[0]["phone_nets_coeff"],
                  self.result[0]["crime_coeff"]))
        conn.commit()
        conn.close()
        self.result.pop(0)

    def run(self):
        print(f"\n{' ' * 30}Preparing to collect information from pages..")
        attempt_number_exception = 0
        for number_page in range(self.start_page, self.end_page + 1):
            try:
                parsed, attempt_number = False, 0
                while not parsed and attempt_number < 3:
                    parsed, attempt_number, end = self.parse_page(html=self.load_page(number_page=number_page), number_page=number_page, count_of_pages=self.end_page + 1 - self.start_page, attempt_number=attempt_number)
                    attempt_number_exception = 0
                    if end:
                        break

            except Exception as e:
                attempt_number_exception += 1
                if attempt_number_exception < 3:
                    continue
                print(f"\n\nException: {e}")
                print(f"The collection of information from the pages with ending parse on {number_page} page...\n")
                print(f"Average price per day: {'{:,}'.format(int(self.average_price)).replace(',', ' ')} rub")
                break

        print(f"\n\nThe collection of information from the pages with list of announcements is completed")
        print(f"Total number of parced announcements: {self.parsed_announcements_count}. ", end="")
        print(f"Average price per month: {'{:,}'.format(int(self.average_price)).replace(',', ' ')} rub")
