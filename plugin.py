"""
<plugin key="FliprLite" name="ZZ - Flipr Basic Analyzer" author="Erwanweb" version="1.0" externallink="https://my.goflipr.com">
    <description>
        <h2>Flipr Analyzer</h2>
        <p>Récupère en RAW pH, ORP, Température via l'API interne Flipr </p>
    </description>
    <params>
        <param field="Username" label="Flipr Email" width="300px" required="true"/>
        <param field="Password" label="Flipr Password" width="300px" required="true"/>
        <param field="Mode1" label="Flipr Serial Number" width="200px" required="true" default=""/>
        <param field="Mode2" label="PH 7 calibration (ex:7.34)" width="50px" required="true" default="7"/>
        <param field="Mode3" label="Redox offset (ex -50)" width="50px" required="true" default="0"/>
        <param field="Mode6" label="Log Level" width="200px">
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
from datetime import datetime, timedelta, time
import time
import math

class BasePlugin:
    def __init__(self):
        self.session = requests.Session()
        self.email = ""
        self.password = ""
        self.serial = ""
        self.PhLastCalib = 0
        self.PhCalib = 0
        self.RedoxOffset = 0
        self.nexscrape = datetime.now() - timedelta(hours=2)
        self.PreviousMesureId = ""
        self.MesureId = ""
        DataTimedOut = False

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
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
        if 4 not in Devices:
            Domoticz.Device(Name="Batt", Unit=4, Type=243, Subtype=31, Options={"Custom": "1;mV"},Used=1).Create()
            devicecreated.append(deviceparam(4, 0, "0"))  # default is 0

        self.email = Parameters["Username"]
        self.password = Parameters["Password"]
        self.serial = Parameters["Mode1"]
        self.PhLastCalib = Parameters["Mode2"]
        self.RedoxOffset = Parameters["Mode3"]

        Domoticz.Heartbeat(20)

    def onHeartbeat(self):
        now = datetime.now()
        if self.nexscrape + timedelta(minutes=1) <= now:
            Domoticz.Log("Logging in & fetching Flipr datas...")
            self.login()
            self.scrape_data_raw()
            self.nexscrape = datetime.now()

    def login(self):
        Domoticz.Debug("Logging in to Flipr web...")
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

    def scrape_data_raw(self):
        try:
            url = f"https://my.goflipr.com/getAllData.php?serial={self.serial}"
            headers = {
                "User-Agent": "Mozilla/5.0"
            }
            response = self.session.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                Domoticz.Error(f"Failed to load Flipr JSON data: HTTP {response.status_code}")
                return

            data_list = response.json()
            if not data_list or not isinstance(data_list, list):
                Domoticz.Error("Flipr JSON response is not a valid list.")
                return

            # ✅ Toujours prendre la première mesure (la plus récente)
            data = data_list[0]

            # Vérification de l’ancienneté de la donnée du flipr
            try:
                timestamp_str = data.get("DateTime")
                if timestamp_str:
                    # Retirer les fractions de secondes et le 'Z' si présent
                    if "." in timestamp_str:
                        timestamp_str = timestamp_str.split(".")[0]
                    timestamp_str = timestamp_str.rstrip("Z")
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

                    now_utc = datetime.utcnow()
                    age = now_utc - timestamp
                    if age > timedelta(hours=6):
                        Domoticz.Error(f"La donnée est trop ancienne : ({age}) h")
                        Devices[1].Update(nValue=Devices[1].nValue, sValue=Devices[1].sValue, TimedOut=True)
                        Devices[2].Update(nValue=Devices[2].nValue, sValue=Devices[2].sValue, TimedOut=True)
                        Devices[3].Update(nValue=Devices[3].nValue, sValue=Devices[3].sValue, TimedOut=True)
                        Devices[4].Update(nValue=Devices[4].nValue, sValue=Devices[4].sValue, TimedOut=True)
                        DataTimedOut = True
                        return
                    else :
                        DataTimedOut = False
                else:
                    Domoticz.Error("Pas de champ DateTime dans la donnée.")
                    return
            except Exception as e:
                Domoticz.Error(f"Erreur lors de la vérification de l'âge de la donnée : {str(e)}")
                return

            if not DataTimedOut :
                self.MesureId = data.get("MesureId", 0)
                if not self.MesureId ==self.PreviousMesureId :
                    Domoticz.Log(f"Received fresh Flipr's datas with ID : {self.MesureId}")
                    self.PreviousMesureId = self.MesureId
                    temp_raw = data.get("Temperature", 0)
                    ph_raw = data.get("RawPH", 0)
                    redox_raw = data.get("OxydoReducPotentiel", 0)
                    batt_raw = data.get("RawBatteryLevel", 0)

                    # ✅ Formattage correct :
                    temp = round(float(temp_raw), 1)
                    ph = round(float(ph_raw), 2)
                    redox = int(round(float(redox_raw), 0))  # Sans virgule
                    batt = int(round(float(batt_raw), 0))  # Sans virgule
                    Domoticz.Log(f"Scraped RAW JSON: Temp={temp}°C, pH={ph}, Redox={redox} mV, Batt={batt} mV")

                    # ✅ calibration correct :
                    self.PhCalib = round(float(self.PhLastCalib) - 7, 2)
                    Domoticz.Debug(f"Flipr Calibration Ph7 is : {self.PhCalib}")
                    ph = ph - self.PhCalib
                    redox = redox + float(self.RedoxOffset)
                    Domoticz.Debug(f"Flipr Redox offset is {self.RedoxOffset}")
                    Domoticz.Log(f"Flipr Calibrated values: pH= {ph}, Redox= {redox} mV")

                    Devices[1].Update(nValue=0, sValue=str(ph), TimedOut=False)
                    Devices[2].Update(nValue=0, sValue=str(redox), TimedOut=False)
                    Devices[3].Update(nValue=0, sValue=str(temp), TimedOut=False)
                    Devices[4].Update(nValue=0, sValue=str(batt), TimedOut=False)
                else :
                    Domoticz.Log(f"Flipr's datas with ID : {self.MesureId} are not news, no update")

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

