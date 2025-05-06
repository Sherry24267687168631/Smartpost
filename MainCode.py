# Wir holen alle Sachen, die wir brauchen (Bibliotheken)
from machine import Pin, I2C, SPI
import time
import aht10
from bh1750 import BH1750
import network
from umqtt.simple import MQTTClient
import ujson
import ntptime
import machine
import st7789

# --- Display vorbereiten ---
# Das ist der kleine Bildschirm. Damit man sieht, was los ist.
spi = SPI(1, baudrate=40000000, sck=Pin(40), mosi=Pin(41)) # SPI-Verbindung für Display
display = st7789.ST7789(spi=spi, width=240, height=280, dc=Pin(42), cs=Pin(1), rst=Pin(2)) # Display starten
display.framebuf.fill(0x0000)  # Alles schwarz machen
display.show() # Anzeige aktualisieren

# --- WLAN verbinden ---
# Damit der ESP32 ins Internet kann (z. B. Uhrzeit holen und mit Node-RED sprechen)
wlan = network.WLAN(network.STA_IF)  # WLAN-Modul aktivieren
wlan.active(True) # WLAN einschalten
if not wlan.isconnected(): 
    wlan.connect('BZTG-IoT', 'WerderBremen24')  # WLAN-Name und Passwort
    while not wlan.isconnected(): # Warten bis verbunden
        pass
print("Mit WLAN verbunden!") # Erfolgsmeldung

# --- Uhrzeit synchronisieren ---
try:
    ntptime.host = "pool.ntp.org" # Zeitserver einstellen 
    ntptime.settime() # Zeit vom Internet holen
    print("Uhrzeit geholt")
    offset = 2 * 60 * 60  # Sommerzeit
    jetzt = time.localtime(time.time() + offset) # Aktuelle Uhrzeit
    rtc = machine.RTC() # Uhr im ESP32 setzen
    rtc.datetime((jetzt[0], jetzt[1], jetzt[2], jetzt[6], jetzt[3], jetzt[4], jetzt[5], 0))
except Exception as e:
    print("Uhrzeit ging nicht:", e) # Fehler beim Zeit holen

# --- MQTT vorbereiten ---
# Damit Node-RED Nachrichten empfangen kann
def mqtt_callback(topic, msg):
    global pieper_status_mqtt
    if topic == b"briefkasten/pieper":
        if msg == b'on':
            pieper_status_mqtt = True  # Pieper einschalten
        elif msg == b'off':
            pieper_status_mqtt = False  # Pieper ausschalten

client = MQTTClient("BriefkastenESP", "192.168.1.173")  # IP vom MQTT-Broker (Node-RED)
client.connect() # Verbinden
client.set_callback(mqtt_callback) # Callback-Funktion setzen
client.subscribe(b"briefkasten/pieper") # Kanal abonnieren
pieper_status_mqtt = None  # Startzustand
print("Mit MQTT verbunden")

# --- Sensoren anschließen ---
magnet = Pin(19, Pin.IN, Pin.PULL_UP)  # erkennt, ob Klappe offen ist
vibration = Pin(4, Pin.IN)             # erkennt Erschütterung
i2c_temp = I2C(1, scl=Pin(36), sda=Pin(35))  # Temperatur und Feuchtigkeit
i2c_licht = I2C(0, scl=Pin(17), sda=Pin(18)) # Helligkeitssensor
temp_sensor = aht10.AHT10(i2c_temp)
licht_sensor = BH1750(i2c_licht)

# --- Pieper und LED anschließen ---
pieper = Pin(21, Pin.OUT)  # Macht Geräusch bei Alarm
led = Pin(8, Pin.OUT)      # Rote LED bei Alarm

# --- Merken, ob gerade Alarm war ---
magnet_alarm_active = False # Anfangszustand Magnet-Alarm
magnet_alarm_time = 0 # Zeit vom Magnet-Alarm
erschuett_alarm_active = False # Anfangszustand Erschütterungs-Alarm
erschuett_alarm_time = 0 # Zeit vom Erschütterungs-Alarm

# --- Letzte gesendete Werte speichern ---
letzter_status = letzte_temp = letzte_feucht = letzte_licht = letzte_ersch = None

# --- Hauptprogramm läuft jetzt in einer Schleife ---
while True:
    client.check_msg()  # Prüft, ob MQTT-Nachricht angekommen ist

    daten = {}  # Hier kommen alle aktuellen Sensorwerte rein

    magnet_auf = magnet.value() == 1
    erschuettung = vibration.value() == 1

    try:
        temperatur, feuchtigkeit = temp_sensor.read()
    except:
        temperatur, feuchtigkeit = None, None

    try:
        lux = licht_sensor.luminance()
    except:
        lux = None

    # Zeit als Text, z. B. "2025-05-04 12:34:56"
    t = time.localtime()
    zeit_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*t[:6])

    # Werte speichern
    daten["magnet"] = magnet_auf
    daten["erschuetterung"] = erschuettung
    daten["temperatur"] = round(temperatur, 2) if temperatur else None
    daten["feuchtigkeit"] = round(feuchtigkeit, 2) if feuchtigkeit else None
    daten["helligkeit"] = round(lux, 2) if lux else None
    daten["zeit"] = zeit_str

    # Nur senden, wenn sich etwas verändert hat
    if daten != {
        "magnet": letzter_status,
        "erschuetterung": letzte_ersch,
        "temperatur": letzte_temp,
        "feuchtigkeit": letzte_feucht,
        "helligkeit": letzte_licht,
        "zeit": None
    }:
        client.publish("briefkasten/status", ujson.dumps(daten))  # Werte senden
        print("MQTT gesendet:", daten) # Anzeige im Terminal
        letzter_status = daten["magnet"]
        letzte_ersch = daten["erschuetterung"]
        letzte_temp = daten["temperatur"]
        letzte_feucht = daten["feuchtigkeit"]
        letzte_licht = daten["helligkeit"]

    # Pieper/LED bei Alarm aktivieren
    pieper_an = False
    led_an = False

    # Magnetkontakt → 2 Sekunden Alarm
    if magnet_auf and not magnet_alarm_active:
        magnet_alarm_active = True
        magnet_alarm_time = time.ticks_ms()
        pieper_an = True
        led_an = True
    elif magnet_alarm_active:
        if time.ticks_diff(time.ticks_ms(), magnet_alarm_time) <= 2000:
            pieper_an = True
            led_an = True
        else:
            magnet_alarm_active = False

    # Erschütterung → 10 Sekunden Alarm
    if erschuettung:
        erschuett_alarm_active = True
        erschuett_alarm_time = time.ticks_ms()
    if erschuett_alarm_active:
        if time.ticks_diff(time.ticks_ms(), erschuett_alarm_time) <= 10000:
            pieper_an = True
            led_an = True
        else:
            erschuett_alarm_active = False

    # Temperatur > 30 °C
    if temperatur is not None and temperatur > 30:
        pieper_an = True
        led_an = True

    # Feuchtigkeit > 60 %
    if feuchtigkeit is not None and feuchtigkeit > 60:
        pieper_an = True
        led_an = True

    # Licht > 3000 Lux
    if lux is not None and lux > 200:
        pieper_an = True
        led_an = True

    # LED ein/aus
    led.value(1 if led_an else 0)

    # Pieper über MQTT oder bei Alarm ein
    if pieper_status_mqtt is True or pieper_an:
        pieper.value(1)
    elif pieper_status_mqtt is False:
        pieper.value(0)
    else:
        pieper.value(0)

    # --- Anzeige auf dem Display ---
    display.framebuf.fill(0x0000)
    display.framebuf.text("Briefkasten Status", 30, 40, 0x07E0)
    display.framebuf.text("Zeit: {}".format(zeit_str[11:]), 10, 60, 0xFFFF)
    display.framebuf.text("Magnetkontakt: {}".format("Offen" if magnet_auf else "Zu"), 10, 85, 0xFFFF)

    if temperatur is not None:
        display.framebuf.text("Temperatur: {:.1f} C".format(temperatur), 10, 110, 0xFFFF)
    if feuchtigkeit is not None:
        display.framebuf.text("Feuchtigkeit: {:.0f} %".format(feuchtigkeit), 10, 135, 0xFFFF)
    if lux is not None:
        display.framebuf.text("Licht: {:.0f} LUX".format(lux), 10, 160, 0xFFFF)

    display.framebuf.text("Erschuetterung: {}".format("JA" if erschuettung else "NEIN"), 10, 185, 0xFFFF)

    # Alarme anzeigen
    y = 210
    alarmtexte = []
    if magnet_auf or magnet_alarm_active:
        alarmtexte.append("- Post ist da")
    if temperatur is not None and temperatur > 30:
        alarmtexte.append("- Briefkasten ueberhitzt")
    if feuchtigkeit is not None and feuchtigkeit > 60:
        alarmtexte.append("- Feuchtigkeit zu hoch")
    if lux is not None and lux > 3000:
        alarmtexte.append("- Taschenlampe erkannt")
    if erschuett_alarm_active:
        alarmtexte.append("- Erschuetterungb erkannt!")

    if alarmtexte:
        display.framebuf.text("ALARM:", 10, y, 0xF800)
        y += 20
        for alarm in alarmtexte[:4]:
            display.framebuf.text(alarm, 10, y, 0xF800)
            y += 20

    display.show() # 
