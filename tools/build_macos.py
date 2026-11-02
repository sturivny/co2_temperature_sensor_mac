#!/usr/bin/env python3
from pathlib import Path
import plistlib,subprocess
root=Path(__file__).resolve().parents[1];app=root/'build/CO2 Monitor.app';mac=app/'Contents/MacOS';mac.mkdir(parents=True,exist_ok=True)
subprocess.run(['swiftc','-swift-version','5','-O','-target','arm64-apple-macos13.0','-module-cache-path',str(root/'.tooling/swift-cache'),'-framework','AppKit','-lsqlite3',str(root/'macos/CO2Monitor.swift'),'-o',str(mac/'CO2Monitor')],check=True)
info={'CFBundleExecutable':'CO2Monitor','CFBundleIdentifier':'local.co2.monitor','CFBundleName':'CO2 Monitor','CFBundlePackageType':'APPL','CFBundleShortVersionString':'0.3.0','CFBundleVersion':'5','CFBundleDevelopmentRegion':'en','CFBundleLocalizations':['en'],'LSUIElement':True,'LSMinimumSystemVersion':'13.0','NSLocalNetworkUsageDescription':'Read your CO₂ sensor and its history on your local network.','NSBonjourServices':['_http._tcp'],'CO2ProjectPath':str(root)}
with (app/'Contents/Info.plist').open('wb') as f:plistlib.dump(info,f)
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
print(app)
