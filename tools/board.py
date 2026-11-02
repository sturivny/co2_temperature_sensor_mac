#!/usr/bin/env python3
"""USB diagnostic, local Wi-Fi provisioning, and lossless CSV export."""
import argparse,csv,getpass,json,os,secrets,sys,time
from pathlib import Path
import serial
from serial.tools import list_ports

def port_name(explicit=None):
    if explicit:return explicit
    ports=[p.device for p in list_ports.comports() if p.vid==0x303A]
    if len(ports)!=1:raise RuntimeError('Connect one ESP32, or select a device with --port.')
    return ports[0]

def connect(port):
    s=serial.Serial();s.port=port;s.baudrate=115200;s.timeout=.15;s.write_timeout=2;s.dtr=True;s.rts=False;s.open();return s

def request(s,command,kind,timeout=8):
    s.reset_input_buffer();payload=(json.dumps(command,ensure_ascii=False)+'\n').encode();s.write(payload);s.flush();deadline=time.monotonic()+timeout;retry=time.monotonic()+1.5
    while time.monotonic()<deadline:
        if time.monotonic()>=retry:s.write(payload);s.flush();retry=time.monotonic()+1.5
        line=s.readline()
        try:d=json.loads(line)
        except (ValueError,UnicodeError):continue
        if d.get('type')=='ack' and d.get('error'):raise RuntimeError(d['error'])
        if kind=='history' and d.get('requested_after')!=command.get('after',0):continue
        if d.get('type')==kind or (kind=='ack' and 'ok' in d):return d
    raise TimeoutError(f'No {kind} response from the device')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','scan','configure','export','monitor']);p.add_argument('--port');p.add_argument('--output',type=Path);args=p.parse_args()
    with connect(port_name(args.port)) as s:
        if args.action=='monitor':
            while True:
                line=s.readline()
                if line:print(line.decode(errors='replace').rstrip(),flush=True)
        elif args.action in ['scan','status']:
            d=request(s,{'cmd':args.action},args.action);print(json.dumps(d,indent=2,ensure_ascii=False))
        elif args.action=='configure':
            ssid=input('2.4 GHz Wi-Fi network name: ').strip();password=getpass.getpass('Wi-Fi password (input hidden): ');token=secrets.token_hex(24)
            d=request(s,{'cmd':'configure','ssid':ssid,'password':password,'token':token},'configured')
            if not d.get('ok'):raise RuntimeError('Configuration was not accepted')
            request(s,{'cmd':'set_time','unix_s':int(time.time())},'ack')
            root=Path.home()/'Library/Application Support/CO2Monitor';root.mkdir(parents=True,exist_ok=True)
            config={'host':d['host'],'token':token}
            dest=root/'config.json';fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as f:json.dump(config,f)
            print('Configuration saved locally. The Wi-Fi password was not saved to a file on the Mac.')
            print('Device:',d['host']);print('Restart CO2 Monitor if it is already open.')
        else:
            dest=args.output or Path('co2-history.csv');cursor=0
            with dest.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['device_id','seq','unix_s','boot','uptime_s','co2','temperature','humidity']);w.writeheader()
                while True:
                    d=request(s,{'cmd':'history','after':cursor,'limit':64},'history')
                    if not d.get('read_ok'):raise RuntimeError('Could not read device flash')
                    for r in d['records']:w.writerow({'device_id':d['device_id'],**r})
                    nxt=d['next_after']
                    if not d['more']:break
                    if nxt<=cursor:raise RuntimeError('History cursor did not advance')
                    cursor=nxt
            print('CSV:',dest.resolve())
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
