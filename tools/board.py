#!/usr/bin/env python3
"""USB diagnostic, local Wi-Fi provisioning, and lossless CSV export."""
import argparse,csv,getpass,json,os,secrets,sys,time
from pathlib import Path
import serial
from serial.tools import list_ports

def port_name(explicit=None):
    if explicit:return explicit
    ports=[p.device for p in list_ports.comports() if p.vid==0x303A]
    if len(ports)!=1:raise RuntimeError('Нужна одна подключённая ESP32; укажите --port при нескольких платах.')
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
    raise TimeoutError(f'Нет ответа {kind} от платы')

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
            ssid=input('Имя сети Wi-Fi 2,4 ГГц: ').strip();password=getpass.getpass('Пароль Wi-Fi (ввод скрыт): ');token=secrets.token_hex(24)
            d=request(s,{'cmd':'configure','ssid':ssid,'password':password,'token':token},'configured')
            if not d.get('ok'):raise RuntimeError('Настройки не приняты')
            request(s,{'cmd':'set_time','unix_s':int(time.time())},'ack')
            root=Path.home()/'Library/Application Support/CO2Monitor';root.mkdir(parents=True,exist_ok=True)
            config={'host':d['host'],'token':token}
            dest=root/'config.json';fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as f:json.dump(config,f)
            print('Настройки сохранены локально. Пароль Wi-Fi не записан в файл на Mac.')
            print('Устройство:',d['host']);print('Перезапустите CO2 Monitor, если он уже открыт.')
        else:
            dest=args.output or Path('co2-history.csv');cursor=0
            with dest.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['device_id','seq','unix_s','boot','uptime_s','co2','temperature','humidity']);w.writeheader()
                while True:
                    d=request(s,{'cmd':'history','after':cursor,'limit':64},'history')
                    if not d.get('read_ok'):raise RuntimeError('Ошибка чтения flash')
                    for r in d['records']:w.writerow({'device_id':d['device_id'],**r})
                    nxt=d['next_after']
                    if not d['more']:break
                    if nxt<=cursor:raise RuntimeError('Журнал не продвигается')
                    cursor=nxt
            print('CSV:',dest.resolve())
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
