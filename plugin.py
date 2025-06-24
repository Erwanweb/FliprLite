"""
<plugin key="FliprLite" name="ZZ - Flipr Basic Analyzer" author="Erwanweb" version="1.0" externallink="https://my.goflipr.com">
    <description>
        <h2>Flipr JSON Analyzer</h2>
        <p>Récupère pH, ORP, Température via l'API interne Flipr `getAllData.php`</p>
    </description>
    <params>
        <param field="Username" label="Flipr Email" width="300px" required="true"/>
        <param field="Password" label="Flipr Password" width="300px" required="true"/>
        <param field="Mode1" label="Flipr Serial Number" width="200px" required="true" default=""/>
        <param field="Mode2" label="Log Level" width="200px">
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

class BasePlugin:
    def __init__(self):
        self.session = requests.Session()
        self.email = ""
        self.password = ""
        self.serial = ""

    def onStart(self):
        if Parameters["Mode2"] == "Debug":
            Domoticz.Debugging(1)
        else:
            Domoticz.Debugging(0)

        Domoticz.Log("FliprJSON starting...")

        if 1 not in Devices:
            Domoticz.Device(Name="pH", Unit=1, Type=243, Subtype=31, Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Redox", Unit=2, Type=243, Subtype=31, Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name="Water Temp", Unit=3, TypeName="Temperature", Used=1).Create()

        self.email = Parameters["Username"]
        self.password = Parameters["Password"]
        self.serial = Parameters["Mode1"]

        Domoticz.Heartbeat(20)

    def onHeartbeat(self):
        Domoticz.Log("Heartbeat: logging in & fetching Flipr JSON...")
        self.login()
        self.scrape_data()

    def login(self):
        Domoticz.Log("Logging in to Flipr (index.php)...")
        url = "https://my.goflipr.com/index.php"
        payload = {
            "email": self.email,
            "password": self.password,
            "accept": "on"
        }
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        try:
            self.session.cookies.set("cookieconsent_status", "allow")
            response = self.session.post(url, data=payload, headers=headers, timeout=30)
            if "logout.php" in response.text:
                Domoticz.Log("Flipr login successful.")
            else:
                Domoticz.Error("Flipr login failed — check credentials or accept field.")
        except Exception as e:
            Domoticz.Error(f"Flipr login error: {str(e)}")

    def scrape_data(self):
        try:
            url = f"https://my.goflipr.com/getAllData.php?serial={self.serial}"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            response = self.session.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                Domoticz.Error(f"Failed to load Flipr JSON data: HTTP {response.status_code}")
                return

            data = response.json()
            Domoticz.Debug(f"Flipr JSON response: {data}")

            temp_raw = data.get("Temperature", 0)
            ph_raw = data.get("RawPH", 0)
            redox_raw = data.get("OxydoReducPotentiel", 0)

            # ✅ Formattage :
            temp = round(float(temp_raw), 1)
            ph = round(float(ph_raw), 2)
            redox = int(round(float(redox_raw), 0))  # Redox sans virgule

            Domoticz.Log(f"Scraped JSON: Temp={temp}°C, pH={ph}, Redox={redox} mV")

            Devices[1].Update(nValue=0, sValue=str(ph))
            Devices[2].Update(nValue=0, sValue=str(redox))
            Devices[3].Update(nValue=0, sValue=str(temp))

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

