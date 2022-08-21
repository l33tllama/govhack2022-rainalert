import configparser
from flask import Flask, render_template, make_response
import csv
from tinydb import TinyDB, Query
import json
import tweepy

# This is the program that runs on my local machine but does not run on PythonAnywhere

app = Flask(__name__, static_folder="./static", template_folder="./html")
app.config['TEMPLATES_AUTO_RELOAD'] = True

all_years_data = []
last_decade_data = []
warnings = []


# Class for parsing rainfall data and saving to local db for querying
class RainData:
    rainfall_data = []
    db = None

    def __init__(self):
        self.db = TinyDB("rainfall.db")

    def load_rain_data(self, filename):
        with open(filename, 'r') as data_csv_file:
            reader = csv.reader(data_csv_file)
            for row in reader:
                year = row[2]
                month = row[3]
                precip = row[4]
                dt = {"year": year, "month": month, "precip": precip}
                #print(str(dt))
                self.db.insert(dt)

    def get_month(self, year, month):
        m_str = str(month).zfill(2)
        y_str = str(year)
        data = self.db.search(Query().fragment({'year': y_str, 'month': m_str}))

        if data:
            #print(m_str + " " + y_str + " " + str(data[0]['precip']))
            return data[0]['precip']

        else:
            return -1

@app.route('/')
def index():
    template = render_template("index.html", warnings=warnings)
    #response = make_response(template)
    #response.headers.set('Content-Type', 'application/rss+xml')
    return template


@app.route('/get_all_years_data')
def get_all_years_data():
    return json.dumps(all_years_data)


@app.route('/get_last_decade_data')
def get_last_decade_data():
    return json.dumps(last_decade_data)


# Get 1882-2022!
def get_all_months(rd:RainData):
    all_months = []
    for i in range(1882, 2022):
        for j in range(1, 12):
            if i == 2022 and j > 7:
                pass
            else:
                month_p = rd.get_month(i, j)
                #date = str(i) + "-" + str(j).zfill(1)
                all_months.append(month_p)
    return all_months


# Get 2012-2022
def get_last_decade(rd:RainData):
    last_decade = []
    for i in range(2012, 2022):
        for j in range(1, 12):
            if i == 2022 and j > 7:
                pass
            else:
                month_p = rd.get_month(i, j)
                last_decade.append(month_p)
    return last_decade


# Add </a href>..</a> tages to links automatically?
def linkify(text:str):
    sub_text = text
    found_index = 1
    final_text = ""
    loop_count = 0
    while found_index > 0:
        link_loc_u = sub_text.find("http://")
        link_loc_s = sub_text.find("https://")
        if link_loc_s:
            found_index = link_loc_s
            # Text before https
            new_text = sub_text[:link_loc_s]
            # Text after https index
            ahref = sub_text[link_loc_s:]
            # location of link end
            ahref_end = ahref.find(" ")
            if ahref_end < 0:
                found_index = -1
            #print("End of link index: " + str(ahref_end))
            # hopefully just the link
            ahref = ahref[:ahref_end]
            # The link!
            ahref = "<a href=\"" + ahref + "\">" + ahref + "</a>"
            # Before link plus link
            new_text = new_text + ahref
            # Substring from https:// to end of link
            new_text_end = sub_text[link_loc_s + ahref_end:]
            final_text = final_text + new_text
            sub_text = new_text_end
            loop_count += 1
            #print("Sub text: " + sub_text)
        else:
            found_index = -1
    if len(final_text) == 0:
        final_text = text
    if loop_count == 1:
        final_text += sub_text
    return final_text


# Add Twitter handle links to text eg @username with <a href=..>
def userify(text):
    print("Userifying..")
    sub_text = text
    found_index = 1
    final_text = ""
    loop_count = 0
    new_text_end = ""
    while found_index > 0:
        at_loc = sub_text.find("@")
        found_index = at_loc
        if at_loc >= 0:
            # Text before @
            new_text = sub_text[:at_loc]
            # Text including and after @
            handle = sub_text[at_loc:]
            print(handle)
            # Location of handle end
            handle_end = handle.find(" ")
            if handle_end < 0:
                found_index = -1
            # Hopefully just the handle
            handle = handle[:handle_end]
            print("Handle: " + handle)
            # The link!
            handle_href = "<a href=\"https://www.twitter.com/" + handle + "\">" + handle + "</a>"
            # Before link plus text
            new_text = new_text + handle_href
            # Substring from @ to end of link
            new_text_end = sub_text[at_loc + handle_end:]
            final_text = final_text + new_text
            sub_text = new_text_end
            print("Handle Sub text: " + sub_text)
            loop_count += 1
        else:
            found_index = -1
    if len(final_text) == 0:
        final_text = text
    if loop_count == 1:
        final_text += sub_text
    return final_text


# http://www.bom.gov.au/fwo/IDZ00058.warnings_tas.xml
class WeatherWarnings:
    # Can't use this - blocked to scrapers
    # warnings_url = "http://www.bom.gov.au/fwo/IDZ00058.warnings_tas.xml"
    api_key = ''
    api_secret = ''
    bearer_token = ''
    tc = None
    taid = 0

    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        self.api_key = config["Twitter"]['api_key']
        self.api_secret = config['Twitter']['api_secret']
        self.bearer_token = config['Twitter']['bearer_token']
        self.taid = config['Twitter']['tas_alert_id']
        self.tc = tweepy.Client(self.bearer_token)

    def read_warnings(self, limit:int):
        response = self.tc.get_users_tweets(self.taid, max_results=max(5, limit), tweet_fields=['context_annotations', 'created_at'])
        warnings = []
        tweet_index = 0
        for tweet in response.data:
            if tweet:
                if str(tweet).lower().find("flood"):
                    print("Tweet " + str(tweet_index) + ": " + tweet.text)
                    date = tweet.created_at.strftime("%d %b %Y %I:%M %p") if tweet.created_at else "No date"
                    tweet_text = userify(linkify(tweet.text))
                    warnings.append(str(date) + " : " + tweet_text)
                    tweet_index += 1
        return warnings[:limit]


# http://www.bom.gov.au/climate/data/index.shtml?zoom=1&lat=-26.9635&lon=133.4635&dp=IDC10002&p_nccObsCode=139&p_display_type=dataFile
# http://www.bom.gov.au/jsp/ncc/cdio/weatherData/av?p_nccObsCode=139&p_display_type=dataFile&p_startYear=&p_c=&p_stn_num=094029
if __name__ == "__main__":
    rd = RainData()
    ww = WeatherWarnings()
    warnings = ww.read_warnings(3)
    #rd.load_rain_data("IDCJAC0001_094029/IDCJAC0001_094029_Data1.csv")
    all_years_data = get_all_months(rd)
    last_decade_data = get_last_decade(rd)
    #print(all_years_data)
    app.run(host="0.0.0.0", port=5001)
