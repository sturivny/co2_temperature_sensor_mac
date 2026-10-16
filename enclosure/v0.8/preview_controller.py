from pathlib import Path
import numpy as np
import trimesh
P=Path(__file__).resolve().parent
s=(P/'build_samples.py').read_text();ns={'__file__':str(P/'build_samples.py')}
exec(s.split('samples={};report=')[0],ns)
exec(s[s.index('# Deterministic opaque z-buffer preview'):s.index('im=Image.new')],ns)
Image,ImageDraw,ImageFont=ns['Image'],ns['ImageDraw'],ns['ImageFont'];render=ns['render'];mesh=ns['mesh'];ESP=ns['ESP']
offset=(-ESP[0]+2,-ESP[1]+2,0)
frame=trimesh.load(P/'fit_esp32_snaps.stl',force='mesh')
pcb=mesh(ns['pcb_solid'](ESP).translate(offset))
usb=mesh(ns['capsule_x'](ns['USB_FRONT']-8,ns['USB_CENTRE_Y']-4.5,ns['USB_BOTTOM'],8,9,3).solid().translate(offset))
glass=mesh(ns['B'](ESP[0]+5,ESP[1]+5,6.5,12,12,1).solid().translate(offset))
a=render([(frame,'#9c88b5')],(85,-120,100),(800,580))
b=render([(frame,'#9c88b5'),(pcb,'#553971'),(glass,'#183d55'),(usb,'#bfc8ce')],(100,-120,85),(800,580))
im=Image.new('RGB',(1700,800),'#f5f6f8');im.paste(a,(25,125));im.paste(b,(875,125));d=ImageDraw.Draw(im)
f='/System/Library/Fonts/Supplemental/Arial.ttf';fb='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def t(x,y,s,n=29,b=False):d.text((x,y),s,font=ImageFont.truetype(fb if b else f,n),fill='#233545')
t(50,30,'v0.8 · опоры на прямых краях',33,True)
t(900,30,'С платой 24,8 × 20,6 мм',33,True)
t(50,710,'Уголки PCB свободны. Край текстолита у внутренней стенки, торец USB-C — вровень снаружи.',27)
t(50,755,'Корпус и образец показаны по STL; контур платы и компоненты — условные объёмы.',26)
im.save(P/'preview_controller.png')
