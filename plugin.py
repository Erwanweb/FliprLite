"""
<plugin key="FliprLite" name="ZZ - Flipr Basic Analyzer" author="Erwanweb" version="1.0" externallink="https://my.goflipr.com">
    <description>
        <h2>Flipr HTML Scraper</h2>
        <p>Scrapes pH, Redox and Water Temperature directly from my.goflipr.com using session cookies and cookie consent.</p>
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

        Domoticz.Heartbeat(20)  # Heartbeat every 20 seconds for quick updates

    def onHeartbeat(self):
        Domoticz.Log("Heartbeat: logging in & fetching Flipr HTML...")
        self.login()
        self.scrape_data()

    def login(self):
        Domoticz.Log("Logging in to Flipr (index.php)...")
        url = "https://my.goflipr.com/index.php"
        payload = {
            "email": self.email,
            "password": self.password,
            "accept": "on",
            "cookies": "on"
        }
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        try:
            # ✅ Force cookie consent
            self.session.cookies.set("cookieconsent_status", "allow")

            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            if "logout.php" in response.text:
                Domoticz.Log("Flipr login successful.")
            else:
                Domoticz.Error("Flipr login failed — check credentials or cookie consent.")
        exce
