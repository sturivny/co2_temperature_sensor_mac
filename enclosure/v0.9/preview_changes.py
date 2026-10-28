from pathlib import Path
import numpy as np
import trimesh
P=Path(__file__).resolve().parent
source=(P/'build_enclosure.py').read_text();ns={'__file__':str(P/'build_enclosure.py')}
exec(source.split('bs,ls=base().solid(),lid().solid()')[0],ns)
exec(source[source.index('# Deterministic opaque z-buffer preview'):source.index('board_objects=')],ns)
Image,ImageDraw,ImageFont=ns['Image'],ns['ImageDraw'],ns['ImageFont'];render=ns['render'];mesh=ns['mesh'];B=ns['B'];m=ns['m']
def solid(p):
 t=trimesh.load(p,force='mesh');return m.Manifold(m.Mesh(np.asarray(t.vertices,dtype=np.float32),np.asarray(t.faces,dtype=np.uint32)))
old=solid(P.parent/'v0.8/base.stl');new=solid(P/'base.stl');lid=solid(P/'lid.stl').rotate((180,0,0)).translate((0,40,17))
region=B(39.8,12.3,0,14.5,14,8).solid()
frames=[(mesh(old^region),'#b58b88'),(mesh(new^region),'#8e74b5'),(mesh(new^B(31,10,0,6,22,15.5).solid()),'#8e74b5'),(mesh(lid^B(0,0,14.5,11,11,2.5).solid()),'#a9b9c5')]
im=Image.new('RGB',(1600,1120),'#f5f6f8');d=ImageDraw.Draw(im)
font='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x,y,s,n=27,b=False):d.text((x,y),s,font=ImageFont.truetype(bold if b else font,n),fill='#233545')
labels=['v0.8 · узкий задний упор','v0.9 · широкий упор и два ребра','Провода опускаются сверху · паз 8 мм','Крышка · плоская посадка винта M2']
for i,(tm,col) in enumerate(frames):
 x=(i%2)*800;y=(i//2)*550
 camera=(-85,-110,105) if i<2 else (100,-125,150)
 im.paste(render([(tm,col)],camera,(740,425)),(x+30,y+75));text(x+35,y+25,labels[i],28,True)
text(35,1060,'Геометрия по новым STL. Прочность и фактическую посадку проверить пробной печатью.',25)
im.save(P/'preview_changes.png')
