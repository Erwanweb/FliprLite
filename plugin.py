"""
<plugin key="FliprLite" name="ZZ - Flipr Basic Analyzer" author="Erwanweb" version="1.0" externallink="https://my.goflipr.com">
    <description>
        <h2>Flipr HTML Scraper</h2>
        <p>Scrapes pH, Redox and Water Temperature directly from my.goflipr.com using session cookies.</p>
    </description>
    <params>
        <param field="Username" label="Flipr Email" width="300px" required="true" default="" />
        <param field="Password" label="Flipr Password" width="300px" required="true" default="" />
        <param field="Mode1" label="Log Level" width="200px">
            <options>
                <option label="Normal" value="Normal" default="true"/>
                <option label="Debug" value="Debug"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import requests
from bs4 import BeautifulSoup

class BasePlugin:
    def __init__(self):
        self.session = requests.Session()
        self.email = ""
        self.password = ""

    def onStart(self):
        if Parameters["Mode1"] == "Debug":
            Domoticz.Debugging(1)
        else:
            Domoticz.Debugging(0)

        Domoticz.Log("FliprScraper starting...")

        if 1 not in Devices:
            Domoticz.Device(Name="pH Value", Unit=1, Type=243, Subtype=31, Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Redox Value", Unit=2, Type=243, Subtype=31, Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name="Water Temperature", Unit=3, TypeName="Temperature", Used=1).Create()

        self.email = Parameters["Username"]
        self.password = Parameters["Password"]

        self.login()
        Domoticz.Heartbeat(20)

    def onHeartbeat(self):
        Domoticz.Log("Heartbeat: fetching Flipr HTML...")
        self.scrape_data()

    def login(self):
        Domoticz.Log("Logging in to Flipr (index.php)...")
        url = "https://my.goflipr.com/index.php"
        payload = {
            "email": self.email,
            "password": self.password
        }
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        try:
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            if "logout.php" in response.text:
                Domoticz.Log("Flipr login successful.")
            else:
                Domoticz.Error("Flipr login failed — check credentials or CSRF protection.")
        except Exception as e:
            Domoticz.Error(f"Flipr login error: {str(e)}")

    def scrape_data(self):
        try:
            url = "https://my.goflipr.com"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            response = self.session.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                Domoticz.Error(f"Failed to load Flipr dashboard: HTTP {response.status_code}")
                self.login()
                return

            soup = BeautifulSoup(response.text, "html.parser")
            # Grab the first pool card
            pool = soup.find("article", class_="table-item")
            if pool:
                divs = pool.find_all("div", class_="text-2")
                if len(divs) >= 3:
                    temp_raw = divs[0].text.strip().replace("°C", "").replace(",", ".")
                    ph_raw = divs[1].text.strip().replace(",", ".")
                    redox_raw = divs[2].text.strip().replace("mv", "").replace(",", ".")
                    temp = round(float(temp_raw), 1)
                    ph = round(float(ph_raw), 2)
                    redox = round(float(redox_raw), 0)

                    Domoticz.Log(f"Scraped: Temp={temp}°C, pH={ph}, Redox={redox} mV")

                    Devices[1].Update(nValue=0, sValue=str(ph))
                    Devices[2].Update(nValue=0, sValue=str(redox))
                    Devices[3].Update(nValue=0, sValue=str(temp))
                else:
                    Domoticz.Error("Could not find enough data points in HTML.")
            else:
                Domoticz.Error("Could not find pool data in HTML — session might have expired.")
                self.login()

        except Exception as e:
            Domoticz.Error(f"Scraping error: {str(e)}")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
