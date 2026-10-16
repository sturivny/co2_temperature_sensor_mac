"""Measured-board enclosure v0.8. Requires numpy, manifold3d, trimesh, matplotlib.
All dimensions mm. Geometry is generated once, exported to SCAD and STL.
"""
from pathlib import Path
import json, struct, os
os.environ.setdefault('MPLCONFIGDIR','/tmp/co2-mpl')
import numpy as np
import manifold3d as m
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
OUT=Path(__file__).resolve().parent
L,W,H=78.,40.,17.
CORNER_R,EDGE_R=3.,.6
WALL,FLOOR,ROOF=2.,2.,2.
PCB_Z,PCB_T=5.,1.5
SIDE_GAP,TOP_GAP=.3,.4
BOARDS={'sensor':(8.,18.,22.2,13.),'esp32':(51.2,9.,24.8,20.6)}
ESP=BOARDS['esp32']
USB_FRONT=ESP[0]+ESP[2]+2.
USB_CENTRE_Y=ESP[1]+ESP[3]/2
USB_WIDTH,USB_HEIGHT=9.,3.
USB_BOTTOM=PCB_Z+1.1
USB_GAP=.3
USB_WINDOW_W=USB_WIDTH+2*USB_GAP
USB_WINDOW_H=USB_HEIGHT+2*USB_GAP
USB_WINDOW_BOTTOM=USB_BOTTOM-USB_GAP
SCREWS=[(5.,5.),(L-5,5.),(5.,W-5),(L-5,W-5)]
class N:
 def __init__(self,op,*args): self.op,self.a=op,args
 def solid(self):
  a=self.a
  if self.op=='box': return m.Manifold.cube(a[3:]).translate(a[:3])
  if self.op=='roundbox':
   tm=rounded_box_mesh(a)
   return m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))
  if self.op=='cyl': return m.Manifold.cylinder(a[3],a[4],a[4],48).translate(a[:3])
  if self.op=='cone': return m.Manifold.cylinder(a[3],a[4],a[5],96).translate(a[:3])
  if self.op=='cylx': return m.Manifold.cylinder(a[3],a[4],a[4],128).rotate((0,90,0)).translate(a[:3])
  if self.op=='union':
   r=a[0].solid()
   for n in a[1:]:r=r+n.solid()
   return r
  if self.op=='diff':
   r=a[0].solid()
   for n in a[1:]:r=r-n.solid()
   return r
 def scad(self):
  a=self.a
  if self.op=='box':return f'translate({list(a[:3])}) cube({list(a[3:])});'
  if self.op=='roundbox':
   tm=rounded_box_mesh(a)
   return 'polyhedron(points='+repr(tm.vertices.tolist())+',faces='+repr(tm.faces.tolist())+');'
  if self.op=='cyl':return f'translate({list(a[:3])}) cylinder(h={a[3]},r={a[4]},$fn=48);'
  if self.op=='cone':return f'translate({list(a[:3])}) cylinder(h={a[3]},r1={a[4]},r2={a[5]},$fn=96);'
  if self.op=='cylx':return f'translate({list(a[:3])}) rotate([0,90,0]) cylinder(h={a[3]},r={a[4]},$fn=128);'
  return ('union' if self.op=='union' else 'difference')+'(){\n'+'\n'.join(n.scad() for n in a)+'\n}'
def B(x,y,z,l,w,h):return N('box',x,y,z,l,w,h)
def C(x,y,z,h,r):return N('cyl',x,y,z,h,r)
def F(x,y,z,h,r1,r2):return N('cone',x,y,z,h,r1,r2)
def U(*a):return N('union',*a)
def D(a,*b):return N('diff',a,*b)
def capsule_x(x,y,z,depth,width,height):
 assert width>height>0
 r=height/2
 return U(B(x,y+r,z,depth,width-height,height),N('cylx',x,y+r,z+r,depth,r),N('cylx',x,y+width-r,z+r,depth,r))


def rounded_box_mesh(a):
 x,y,z,length,width,height,radius,edge=a
 assert 0<radius<min(length,width)/2 and 0<=edge<min(radius,height/2)
 if edge:
  levels=[(edge*(1-np.cos(t)),edge*(1-np.sin(t))) for t in np.linspace(0,np.pi/2,7)]
  levels += [(height-edge+edge*np.sin(t),edge*(1-np.cos(t))) for t in np.linspace(0,np.pi/2,7)]
 else:levels=[(0.,0.),(height,0.)]
 rings=[]
 for zz,inset in levels:
  rr=radius-inset;ring=[]
  for cx,cy,start in [(length-radius,width-radius,0),(radius,width-radius,90),(radius,radius,180),(length-radius,radius,270)]:
   for angle in np.linspace(start,start+90,17):
    theta=np.deg2rad(angle);ring.append([x+cx+rr*np.cos(theta),y+cy+rr*np.sin(theta),z+zz])
  rings.append(ring)
 count=len(rings[0]);verts=[v for ring in rings for v in ring];faces=[]
 for k in range(len(rings)-1):
  for j in range(count):
   a0=k*count+j;b0=k*count+(j+1)%count;c0=(k+1)*count+(j+1)%count;d0=(k+1)*count+j
   faces += [[a0,b0,c0],[a0,c0,d0]]
 bottom=len(verts);verts.append([x+length/2,y+width/2,z])
 top=len(verts);verts.append([x+length/2,y+width/2,z+height])
 for j in range(count):
  faces.append([bottom,(j+1)%count,j])
  faces.append([top,(len(rings)-1)*count+j,(len(rings)-1)*count+(j+1)%count])
 tm=trimesh.Trimesh(verts,faces,process=True)
 assert tm.is_watertight and tm.is_winding_consistent
 if tm.volume<0:tm.invert()
 return tm

def RB(x,y,z,length,width,height,radius,edge=0):return N('roundbox',x,y,z,length,width,height,radius,edge)

def corner_positions(board):
 x,y,l,w=board
 for cx,sx in [(x,-1),(x+l,1)]:
  for cy,sy in [(y,-1),(y+w,1)]:yield cx,cy,sx,sy


def clipped_pcb(board,z=PCB_Z,thickness=PCB_T,cut=1.):
 x,y,length,width=board
 # Approximate user-described 1 x 1 mm corner cuts; exact radius not assumed.
 shape=B(x,y,z,length,width,thickness).solid()
 # A chamfered 2D outline extruded as a closed, consistently oriented mesh.
 points=[(cut,0),(length-cut,0),(length,cut),(length,width-cut),(length-cut,width),(cut,width),(0,width-cut),(0,cut)]
 v=[[x+xx,y+yy,zz] for zz in [z,z+thickness] for xx,yy in points]
 faces=[]
 for j in range(8):
  k=(j+1)%8;faces.extend([[j,k,8+k],[j,8+k,8+j]])
 for j in range(1,7):faces.extend([[0,j+1,j],[8,8+j,8+j+1]])
 tm=trimesh.Trimesh(v,faces,process=True)
 assert tm.is_watertight and tm.is_winding_consistent
 if tm.volume<0:tm.invert()
 return m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))

def pcb_solid(board,z=PCB_Z,thickness=PCB_T):
 return clipped_pcb(board,z,thickness) if board==BOARDS['esp32'] else B(board[0],board[1],z,board[2],board[3],thickness).solid()

def esp_cradle(board):
 x,y,length,width=board;a=[]
 # Bear on straight long edges at least 2 mm from both ends, not PCB corners.
 for xx in [x+2.,x+length-4.]:
  for side in [-1,1]:
   yy=y-1.8 if side<0 else y+width-.8
   a.append(B(xx,yy,FLOOR,2.,2.6,PCB_Z-FLOOR))
   guide_y=y-1.8 if side<0 else y+width+SIDE_GAP
   a.append(B(xx,guide_y,FLOOR,2.,1.8-SIDE_GAP,PCB_Z+PCB_T+.3-FLOOR))
 # Rear stop only, in the centre of the non-USB edge. Front datum is the wall.
 a.append(B(x-1.8,y+width/2-2,FLOOR,1.65,4.,PCB_Z+PCB_T+.3-FLOOR))
 return U(*a)

def esp_keepers(board):
 x,y,length,width=board;a=[]
 for xx in [x+3.,x+length-3.]:
  for side in [-1,1]:
   yy=y if side<0 else y+width-.85
   body_y=y if side<0 else y+width-1.6
   a.append(B(xx-.5,yy,PCB_Z+PCB_T+TOP_GAP,1.,.85,1.2))
   a.append(B(xx-.8,body_y,8.,1.6,1.6,H-ROOF-8.+.05))
 return U(*a)

def cradle(board):
 if board==BOARDS['esp32']:return esp_cradle(board)
 a=[]
 for x,y,sx,sy in corner_positions(board):
  # Each support contacts at most an 0.8 x 0.8 mm PCB corner.
  xx=x-1.8 if sx<0 else x-.8
  yy=y-1.8 if sy<0 else y-.8
  a.append(B(xx,yy,FLOOR,2.6,2.6,PCB_Z-FLOOR))
  # L-shaped lateral stops, 0.3 mm outside the PCB outline.
  xs=x-1.8 if sx<0 else x+SIDE_GAP
  ys=y-1.8 if sy<0 else y+SIDE_GAP
  a.append(B(xs,yy,FLOOR,1.8-SIDE_GAP,2.6,PCB_Z+PCB_T+.3-FLOOR))
  a.append(B(xx,ys,FLOOR,2.6,1.8-SIDE_GAP,PCB_Z+PCB_T+.3-FLOOR))
 return U(*a)

def keepers(board):
 if board==BOARDS['esp32']:return esp_keepers(board)
 a=[]
 # Retaining pillars stop 0.4 mm ABOVE the PCB: they do not preload it.
 # Tips stay inside the lateral L stops, avoiding base/lid interference.
 for x,y,sx,sy in corner_positions(board):
  xx=x if sx<0 else x-.85
  yy=y if sy<0 else y-.85
  a.append(B(xx,yy,PCB_Z+PCB_T+TOP_GAP,.85,.85,1.2))
  body_x=x if sx<0 else x-1.6
  body_y=y if sy<0 else y-1.6
  a.append(B(body_x,body_y,8.,1.6,1.6,H-ROOF-8.+.05))
 return U(*a)

def base():
 shell=D(RB(0,0,0,L,W,H-ROOF,CORNER_R,EDGE_R),RB(WALL,WALL,FLOOR,L-2*WALL,W-2*WALL,H,CORNER_R-WALL))
 baffle=D(B(33,2,2,2,W-4,H-ROOF-FLOOR-.3),B(32.9,17,2,2.2,7,5),B(32.9,2,H-ROOF-2.3,2.2,2,3),B(32.9,W-4,H-ROOF-2.3,2.2,2,3))
 a=[shell,baffle]+[C(x,y,FLOOR,H-ROOF-FLOOR,4) for x,y in SCREWS]
 a += [cradle(b) for b in BOARDS.values()]
 cuts=[C(x,y,H-ROOF-10,11,.85) for x,y in SCREWS]
 # Side vents on the sensor side; no fan or filter required by the geometry.
 cuts += [B(-.1,y,6,2.2,2,7) for y in range(14,30,4)]
 # Measured USB-C: 9 x 3 mm; bottom 1.1 mm above PCB underside.
 # Window has 0.3 mm clearance per edge; check actual cable on sample.
 cuts += [capsule_x(L-2.1,USB_CENTRE_Y-USB_WINDOW_W/2,USB_WINDOW_BOTTOM,2.2,USB_WINDOW_W,USB_WINDOW_H)]
 return D(U(*a),*cuts)

def lid():
 a=[RB(0,0,H-ROOF,L,W,ROOF,CORNER_R,EDGE_R)]
 # Alignment ribs; gaps avoid bosses and baffle. 0.3 mm lateral allowance.
 a += [B(11,2.3,H-ROOF-2,56,1.2,2.1), B(11,W-3.5,H-ROOF-2,56,1.2,2.1),
       B(2.3,12,H-ROOF-2,1.2,W-24,2.1),B(L-3.5,12,H-ROOF-2,1.2,W-24,2.1)]
 a += [keepers(b) for b in BOARDS.values()]
 cuts=[C(x,y,H-ROOF-.1,2.2,1.2) for x,y in SCREWS]
 # 90 degree countersink, 4.8 mm at outer surface, for measured 4.6 mm head.
 cuts += [F(x,y,H-1.2,1.3,1.2,2.5) for x,y in SCREWS]
 # 12 mm glass measured 5 mm from non-USB end and one long edge.
 # 0.6 mm aperture allowance per side; physical test confirms orientation.
 cuts += [B(ESP[0]+4.4,ESP[1]+4.4,H-ROOF-.1,13.2,13.2,2.2)]
 cuts += [B(x,14,H-ROOF-.1,1.8,20,2.2) for x in [10,14,18,22,26]]
 # Tiny access holes over the two provisional BOOT/RST positions.
 # These positions are deliberately NOT drilled: exact button centres unknown.
 return D(U(*a),*cuts)

def mesh(s):
 a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True)
def checked_export(name,s):
 assert s.status()==m.Error.NoError,(name,s.status())
 tm=mesh(s)
 assert tm.is_watertight and tm.is_winding_consistent
 assert len(s.decompose())==1,(name,len(s.decompose()))
 tm.export(OUT/name)
 # Verify the serialized STL, not just the source solid.
 rt=trimesh.load(OUT/name,force='mesh',process=True)
 assert rt.is_watertight and rt.is_winding_consistent
 return {'file':name,'dimensions_mm':rt.extents.round(3).tolist(),'volume_mm3':round(float(rt.volume),2),
         'watertight':bool(rt.is_watertight),'consistent_winding':bool(rt.is_winding_consistent),
         'connected_solids':len(s.decompose()),'triangles':len(rt.faces)}

bs,ls=base().solid(),lid().solid()
# Keep lid in assembly coordinates for collision checks; invert for printing.
lprint=ls.rotate((180,0,0)).translate((0,W,H))
checks={'version':'0.8','board_dimensions_mm':{name:[b[2],b[3],PCB_T] for name,b in BOARDS.items()},'parts':[checked_export('base.stl',bs),checked_export('lid.stl',lprint)],'checks':{}}
checks['usb_window_mm']={'width':USB_WINDOW_W,'height':USB_WINDOW_H,'bottom_above_case_bottom':USB_WINDOW_BOTTOM,'connector_bottom_above_pcb_underside':1.1,'clearance_each_side':USB_GAP,'end_radius':USB_WINDOW_H/2,'profile':'capsule_full_radius','centre_y':USB_CENTRE_Y}
checks['enclosure_mm']={'length':L,'width':W,'height':H,'corner_radius':CORNER_R,'edge_radius':EDGE_R,'sensor_top_to_lid_clearance':H-ROOF-13.}
checks['fastener_mm']={'nominal_shank_diameter':2.,'overall_length_including_head':10.,'measured_head_diameter':4.6,'countersink_diameter':4.8,'assumed_head_angle_deg':90,'clearance_hole_diameter':2.4,'pilot_diameter':1.7,'pilot_depth':10.,'nominal_tip_to_pilot_bottom':1.9}
checks['controller_mount_mm']={'pcb_length':ESP[2],'pcb_width':ESP[3],'pcb_edge_x':ESP[0]+ESP[2],'inner_usb_wall_x':L-WALL,'usb_front_x':USB_FRONT,'outer_wall_x':L,'usb_recess':L-USB_FRONT,'corner_cut_assumption':1.,'support_inset_from_ends':2.,'rear_stop_clearance':.15}
checks['checks']['base_lid_intersection_mm3']=round((bs^ls).volume(),8)
assert abs((bs^ls).volume())<1e-6
for name,b in BOARDS.items():
 x,y,l,w=b;pcb=pcb_solid(b)
 v=(pcb^bs).volume()+(pcb^ls).volume()
 checks['checks'][name+'_pcb_intersection_mm3']=round(v,8)
 assert abs(v)<1e-6
# Conservative component envelopes, avoiding the small corner support zones.
envelopes={
 'esp32_back':B(ESP[0]+2,ESP[1]+2,2.5,ESP[2]-4,ESP[3]-4,2.5),
 'esp32_front':B(ESP[0]+2,ESP[1]+2,6.5,ESP[2]-4,ESP[3]-4,2.5),
 'sensor_metal':B(12,21,6.5,8,8,6.5),
 'usb':capsule_x(USB_FRONT-8,USB_CENTRE_Y-USB_WIDTH/2,USB_BOTTOM,8,USB_WIDTH,USB_HEIGHT)}
for name,n in envelopes.items():
 s=n.solid();v=(s^bs).volume()+(s^ls).volume()
 checks['checks'][name+'_envelope_intersection_mm3']=round(v,8)
 assert abs(v)<1e-6,(name,v)
# Board insertion checked at several heights, separately from lid installation.
for name,(x,y,l,w) in BOARDS.items():
 for z in np.linspace(PCB_Z,24,20):
  v=(pcb_solid((x,y,l,w),float(z))^bs).volume()
  assert abs(v)<1e-6,(name,z,v)
checks['checks']['pcb_vertical_insertion']='20 positions per board, ideal outline only'
# Lid removal vertical; catches rib and retaining-pillar interferences.
for dz in np.linspace(0,20,41):assert abs((bs^ls.translate((0,0,float(dz)))).volume())<1e-6
checks['checks']['lid_vertical_removal']='41 positions, 0..20 mm'
# Small cradle-only samples, one board per sample; no upper retaining pillars.
for name,b in BOARDS.items():
 x,y,l,w=b
 sample_node=U(B(x-2,y-2,0,l+4,w+4,FLOOR),cradle(b))
 if name=='esp32':
  usb_wall=D(B(x+l,y-2,0,2,w+4,H-ROOF),capsule_x(x+l-.1,y+w/2-USB_WINDOW_W/2,USB_WINDOW_BOTTOM,2.2,USB_WINDOW_W,USB_WINDOW_H))
  sample_node=U(sample_node,usb_wall)
 sample=sample_node.solid().translate((-x+2,-y+2,0))
 checks['parts'].append(checked_export('fit_'+name+'.stl',sample))
(OUT/'validation.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
# Export the same geometry to an editable OpenSCAD source, assembly coords.
(OUT/'enclosure.scad').write_text('''// v0.8 measured boards; mm. Generated by build_enclosure.py.
// part: base / lid / assembly / exploded. STL lid is already oriented for printing.
part="exploded";
module base(){\n'''+base().scad()+'\n}\nmodule lid(){\n'+lid().scad()+'''
}
if(part=="base") base();
else if(part=="lid") translate([0,40,17]) rotate([180,0,0]) lid();
else {color("LightGray") base(); color("Gainsboro") translate([0,0,part=="exploded"?16:0]) lid();}
''')
# Deterministic opaque z-buffer preview from exported meshes.
from PIL import Image, ImageDraw, ImageFont

def render(objects, camera, size=(850,650)):
 forward=np.array(camera,dtype=float);forward/=np.linalg.norm(forward)
 right=np.cross([0.,0.,1.],forward);right/=np.linalg.norm(right)
 up=np.cross(forward,right)
 basis=np.array([right,-up,forward]).T
 data=[]
 for tm,col in objects:
  verts=np.asarray(tm.vertices)@basis
  data.append((tm,verts,np.array(matplotlib.colors.to_rgb(col))*255))
 allv=np.concatenate([v for _,v,_ in data]);low=allv[:,:2].min(0);high=allv[:,:2].max(0)
 scale=min((size[0]-60)/(high[0]-low[0]),(size[1]-50)/(high[1]-low[1]))
 centre=(low+high)/2
 rgb=np.zeros((size[1],size[0],3),dtype=np.uint8);rgb[:]=[245,246,248]
 depth=np.full((size[1],size[0]),-np.inf)
 light=np.array([-.5,-1.,2.]);light/=np.linalg.norm(light)
 for tm,verts,col in data:
  xy=(verts[:,:2]-centre)*scale+np.array(size)/2
  for face,normal in zip(tm.faces,tm.face_normals):
   tri=xy[face];z=verts[face,2]
   lo=np.maximum(np.floor(tri.min(0)).astype(int),0);hi=np.minimum(np.ceil(tri.max(0)).astype(int),np.array(size)-1)
   if np.any(lo>hi):continue
   x0,y0=tri[0];x1,y1=tri[1];x2,y2=tri[2]
   denom=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
   if abs(denom)<1e-9:continue
   xs,ys=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
   a=((y1-y2)*(xs-x2)+(x2-x1)*(ys-y2))/denom
   b=((y2-y0)*(xs-x2)+(x0-x2)*(ys-y2))/denom;c=1-a-b
   zz=a*z[0]+b*z[1]+c*z[2]
   view=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
   mask=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(zz>view)
   shade=.48+.52*max(0,float(np.dot(normal,light)))
   rgb[lo[1]:hi[1]+1,lo[0]:hi[0]+1][mask]=np.clip(col*shade,0,255).astype(np.uint8)
   view[mask]=zz[mask]
 return Image.fromarray(rgb)

def obj(s,col):return (mesh(s),col)
board_objects=[obj(pcb_solid((x,y,l,w)),'#80629f' if name=='esp32' else '#557c7b') for name,(x,y,l,w) in BOARDS.items()]
board_objects += [obj(envelopes['sensor_metal'].solid(),'#cad1d5'),obj(B(ESP[0]+5,ESP[1]+5,6.5,12,12,1).solid(),'#183d55'),obj(envelopes['usb'].solid(),'#9ea4ac')]
base_obj=(trimesh.load(OUT/'base.stl',force='mesh'),'#bcc9d3')
lid_obj=mesh(ls.translate((0,0,20)))
left=render([base_obj]+board_objects+[(lid_obj,'#d9e2e8')],(95,-130,100))
right=render([base_obj]+board_objects,(0,-15,150))
im=Image.new('RGB',(1800,1000),'#f5f6f8');im.paste(left,(25,170));im.paste(right,(925,170));d=ImageDraw.Draw(im)
font='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x,y,t,n=28,b=False):d.text((x,y),t,fill='#233545',font=ImageFont.truetype(bold if b else font,n))
text(55,32,'CO2 монитор · корпус v0.8 · 78 × 40 × 17 мм',42,True)
text(55,105,'Крышка поднята: видны направляющие и упоры',26)
text(970,105,'Датчик слева · ESP32 справа · USB справа',26)
text(55,865,'Корпус показан по STL. Цветные платы и компоненты — условные объёмы по замерам.',27)
text(55,914,'Сначала напечатать образцы креплений: посадка плат и USB ещё требуют физической проверки.',26)
im.save(OUT/'preview.png')
# Separate close-up of the quick-print fit samples.
fit_objects=[(trimesh.load(OUT/'fit_sensor.stl',force='mesh'),'#81a59d')]
a=render(fit_objects,(80,-100,90),(750,500))
b=render([(trimesh.load(OUT/'fit_esp32.stl',force='mesh'),'#9c88b5')],(85,-120,90),(750,500))
im=Image.new('RGB',(1600,690),'#f5f6f8');im.paste(a,(25,100));im.paste(b,(825,100));d=ImageDraw.Draw(im)
text(50,25,'Образец датчика · 26,2 × 17 мм',30,True)
text(850,25,'Образец ESP32 и USB · 28,8 × 24,6 мм',30,True)
text(50,620,'Эти образцы проверяют нижние опоры и направляющие. Верхние упоры проверяются с крышкой.',24)
im.save(OUT/'fit_samples.png')
print(json.dumps(checks,ensure_ascii=False,indent=2))
