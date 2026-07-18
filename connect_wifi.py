#!/usr/bin/env python3
"""Batch WiFi connection for all devices."""
import uiautomator2 as u2
import time
import sys

SSID = "Mitoxmar"
PASS = "Marvin123"

DEVICES = [
    "98877b475345573954", "9887a8474a41454e58", "9887bc43445057584d",
    "988820344f33594d48", "988837454249515651", "98883833445a305730",
    "988939454d3930314c", "98897a31415156545a", "98897a3359474a4744",
    "98897a47483554424c", "988995304b4f573456", "9889954538385a3345",
    "988b5a415053434638", "988b5a48314f59554a", "988b9a474c38474e56",
    "988d9131423542415a", "ce11160b19538a0205",
]

ok = []
fail = []

for i, dev_id in enumerate(DEVICES):
    print(f"[{i+1}/{len(DEVICES)}] {dev_id} ", end="", flush=True)
    try:
        d = u2.connect(dev_id)
        
        # Check if already connected
        out = d.shell("dumpsys wifi | grep 'mWifiInfo.*SSID'").output
        if SSID in out:
            print("✅ ya conectado")
            ok.append(dev_id)
            continue
        
        # Open WiFi settings
        d.shell("am start -a android.settings.WIFI_SETTINGS")
        time.sleep(2.5)
        
        # Find and click Mitoxmar
        el = d(text=SSID)
        if not el.exists:
            # Scroll to find it
            for _ in range(6):
                d.swipe(540, 1200, 540, 400)
                time.sleep(1)
                el = d(text=SSID)
                if el.exists:
                    break
        
        if not el.exists:
            print(f"❌ no encontrado en lista")
            d.press("home")
            fail.append((dev_id, "network not found"))
            continue
        
        el.click()
        time.sleep(2.5)
        
        # Enter password
        edit = d(className="android.widget.EditText")
        if edit.exists(timeout=3):
            edit.set_text(PASS)
            time.sleep(0.5)
        else:
            print(f"❌ sin campo de contraseña")
            d.press("back"); d.press("home")
            fail.append((dev_id, "no password field"))
            continue
        
        # Click Connect
        btn = d(text="Conectar")
        if btn.exists(timeout=2):
            btn.click()
        elif d(text="Connect").exists(timeout=1):
            d(text="Connect").click()
        else:
            btns = d(className="android.widget.Button")
            if btns.count > 0:
                btns[0].click()
            else:
                d.press("enter")
        
        # Verify
        time.sleep(5)
        out = d.shell("dumpsys wifi | grep 'mWifiInfo.*SSID'").output
        if SSID in out:
            print("✅ conectado")
            ok.append(dev_id)
        else:
            print(f"❌ no conectó")
            fail.append((dev_id, "connection failed"))
        
        d.press("home")
        
    except Exception as e:
        print(f"❌ error: {e}")
        fail.append((dev_id, str(e)))

print(f"\n{'='*50}")
print(f"RESULTADO: {len(ok)}/{len(DEVICES)} conectados a {SSID}")
print(f"{'='*50}")
for dev_id, reason in fail:
    print(f"  ❌ {dev_id}: {reason}")
