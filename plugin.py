"""
<plugin key="FliprLite" name="ZZ - Flipr Basic Analyzer" author="Erwanweb" version="1.0" externallink="https://www.goflipr.com">
    <description>
        <h2>Flipr Basic Pool Data</h2>
        <p>Fetch PH, Redox and Water Temperature from your Flipr Analyzer.</p>
    </description>
    <params>
        <param field="Address" label="Flipr Module ID" width="300px" required="true" default="" />
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
from datetime import datetime

class BasePlugin:
    def __init__(self):
        self.token = None
        self.module_id = ""
        self.email = ""
        self.password = ""

    def onStart(self):
        if Parameters["Mode1"] == "Debug":
            Domoticz.Debugging(1)
        else:
            Domoticz.Debugging(0)

        Domoticz.Log("Flipr Simple Plugin starting...")

        # Create devices
        if 1 not in Devices:
            Domoticz.Device(Name="pH Value", Unit=1, Type=243, Subtype=31, Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Redox Value", Unit=2, Type=243, Subtype=31, Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name="Water Temperature", Unit=3, TypeName="Temperature", Used=1).Create()

        self.module_id = Parameters["Address"]
        self.email = Parameters["Username"]
        self.password = Parameters["Password"]

        self.loginFlipr()

        Domoticz.Heartbeat(300)  # every 5 minutes

    def onHeartbeat(self):
        if not self.token:
            Domoticz.Log("No Flipr token found — retrying login.")
            self.loginFlipr()
            return
        self.readFliprData()

    def loginFlipr(self):
        Domoticz.Log("Authenticating with Flipr API...")
        url = "https://apis.goflipr.com/users/sign_in"
        payload = {"user": {"email": self.email, "password": self.password}}
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                self.token = response.json().get("authentication_token")
                Domoticz.Log(f"Flipr token obtained: {self.token}")
            else:
                Domoticz.Error(f"Flipr login failed: HTTP {response.status_code} - {response.text}")
                self.token = None
        except Exception as e:
            Domoticz.Error(f"Flipr login error: {str(e)}")
            self.token = None

    def readFliprData(self):
        Domoticz.Log("Fetching Flipr measurement data...")
        url = f"https://apis.goflipr.com/modules/{self.module_id}/last_measurement"
        headers = {"Authorization": f"Token {self.token}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                ph = round(float(data["ph"]), 2)
                redox = round(float(data["orp"]), 0)
                temp = round(float(data["temperature"]), 1)

                Domoticz.Log(f"Flipr data: pH={ph}, Redox={redox}, Temp={temp}°C")

                Devices[1].Update(nValue=0, sValue=str(ph))
                Devices[2].Update(nValue=0, sValue=str(redox))
                Devices[3].Update(nValue=0, sValue=str(temp))

            elif response.status_code == 401:
                Domoticz.Error("Flipr token expired or invalid — re-authenticating.")
                self.token = None
            else:
                Domoticz.Error(f"Flipr API error: HTTP {response.status_code} - {response.text}")

        except Exception as e:
            Domoticz.Error(f"Flipr data fetch error: {str(e)}")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()
