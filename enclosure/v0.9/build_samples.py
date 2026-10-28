"""Measured-board enclosure v0.9. Requires numpy, manifold3d, trimesh, matplotlib.
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
  if self.op=='wedge':
   tm=wedge_mesh(a)
   return m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))
  if self.op=='brace':
   tm=brace_mesh(a)
   return m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))
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
  if self.op=='wedge':
   tm=wedge_mesh(a)
   return 'polyhedron(points='+repr(tm.vertices.tolist())+',faces='+repr(tm.faces.tolist())+');'
  if self.op=='brace':
   tm=brace_mesh(a)
   return 'polyhedron(points='+repr(tm.vertices.tolist())+',faces='+repr(tm.faces.tolist())+');'
  return ('union' if self.op=='union' else 'difference')+'(){\n'+'\n'.join(n.scad() for n in a)+'\n}'

def brace_mesh(a):
 x,y,z,length,width,height=a
 verts=[[x,y,z],[x+length,y,z],[x+length,y,z+height],
        [x,y+width,z],[x+length,y+width,z],[x+length,y+width,z+height]]
 faces=[[0,2,1],[3,4,5],[0,1,4],[0,4,3],[1,2,5],[1,5,4],[2,0,3],[2,3,5]]
 tm=trimesh.Trimesh(verts,faces,process=True)
 assert tm.is_watertight and tm.is_winding_consistent
 if tm.volume<0:tm.invert()
 return tm

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
 # Preserve the fitted contact datum x-0.15 and z=6.8, but spread the load.
 face=x-.15;back=face-3.2;centre=y+width/2;height=PCB_Z+PCB_T+.3-FLOOR
 # Wide wall, floor-overlapping foot, and two rear-facing triangular gussets.
 a.append(B(back,centre-4,FLOOR,3.2,8.,height))
 a.append(B(back-6.8,centre-5,FLOOR-.5,10.,10.,1.1))
 for yy in [centre-3.8,centre+2]:
  a.append(N('brace',back-6,yy,FLOOR,6.3,1.8,height))
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
 baffle=D(B(33,2,2,2,W-4,H-ROOF-FLOOR-.3),B(32.9,17,1.9,2.2,8,H),B(32.9,2,H-ROOF-2.3,2.2,2,3),B(32.9,W-4,H-ROOF-2.3,2.2,2,3))
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
 # M2 socket heads sit outside on the flat lid: no countersink or head recess.
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


def wedge_mesh(a):
 x,y,z,length,dy,height=a
 verts=[[x,y,z],[x+length,y,z],[x,y+dy,z],[x+length,y+dy,z],[x,y+dy,z+height],[x+length,y+dy,z+height]]
 faces=[[0,2,4],[1,5,3],[0,1,3],[0,3,2],[2,3,5],[2,5,4],[4,5,1],[4,1,0]]
 tm=trimesh.Trimesh(verts,faces,process=True)
 assert tm.is_watertight and tm.is_winding_consistent
 if tm.volume<0:tm.invert()
 return tm

CLIP_GAP=.3
CLIP_THICK=.8
HOOK_OVERLAP=.35
HOOK_Z=PCB_Z+PCB_T+.25
CLIP_TOP=8.

def snap_parts(board):
 x,y,l,w=board;clips=[];slots=[]
 anchor=x+3.;root_end=anchor+2.;free_end=root_end+10.
 for side in [-1,1]:
  edge=y if side<0 else y+w
  inner=edge+side*CLIP_GAP
  yy=inner-CLIP_THICK if side<0 else inner
  # Vertical wall starts on the bed, but a base slot frees the 10 mm beam.
  beam=B(anchor,yy,0,free_end-anchor,CLIP_THICK,CLIP_TOP)
  tip=edge-side*HOOK_OVERLAP
  ramp=N('wedge',free_end-2.4,tip,HOOK_Z,2.4,inner+side*.05-tip,CLIP_TOP-HOOK_Z)
  tab_y=yy-.6 if side<0 else yy+CLIP_THICK-.05
  release=B(free_end-2.4,tab_y,7.2,2.4,.65,.8)
  clips.append(U(beam,ramp,release))
  # The clearance slot opens to the outside edge of the sample.
  slot_y=y-2.1 if side<0 else y+w-.2
  slots.append(B(root_end,slot_y,-.1,free_end-root_end+.6,2.3,FLOOR+.2))
 return clips,slots

samples={};report={'version':'0.9-snaps','scope':'controller 24.8 mm, straight-edge supports, PCB flush against USB wall; sensor unchanged','parts':[],'checks':{},
 'snap_dimensions_mm':{'beam_free_length':10,'beam_thickness':CLIP_THICK,'hook_overlap':HOOK_OVERLAP,'vertical_gap_above_pcb':.25,'nominal_insertion_deflection':CLIP_GAP+HOOK_OVERLAP}}
for name,b in BOARDS.items():
 x,y,l,w=b
 extension=9. if name=='esp32' else 0.
 floor=B(x-2-extension,y-2,0,l+4+extension,w+4,FLOOR)
 clips,slots=snap_parts(b)
 # Cut base BEFORE adding the flexible clip, preserving only its root attachment.
 floor=D(floor,*slots)
 a=[floor,cradle(b)]+clips
 if name=='esp32':
  a.append(D(B(x+l,y-2,0,2,w+4,H-ROOF),capsule_x(x+l-.1,y+w/2-USB_WINDOW_W/2,USB_WINDOW_BOTTOM,2.2,USB_WINDOW_W,USB_WINDOW_H)))
 node=U(*a);world=node.solid()
 pcb=pcb_solid(b)
 intersection=(world^pcb).volume()
 assert abs(intersection)<1e-6,(name,intersection)
 report['checks'][name+'_pcb_at_rest_intersection_mm3']=round(intersection,8)
 # Verify an open undercut exists between beam and plate along its free span.
 samples[name]=world.translate((-x+2+extension,-y+2,0))
 filename='fit_'+name+'_snaps.stl'
 report['parts'].append(checked_export(filename,samples[name]))
 (OUT/('fit_'+name+'_snaps.scad')).write_text('// Sample with flexible side latches, v0.9. Millimetres.\n'+f'translate({[-x+2+extension,-y+2,0]}) '+node.scad()+'\n')
report['checks']['flexural_strength']='not simulated; physical fit and fatigue unverified'
report['checks']['insertion']='requires elastic latch deflection; rigid straight-in collision check intentionally not used'
(OUT/'validation_samples.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
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

im=Image.new('RGB',(1700,850),'#f5f6f8');d=ImageDraw.Draw(im)
font='/System/Library/Fonts/Supplemental/Arial.ttf';bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def text(x,y,t,n=28,b=False):d.text((x,y),t,fill='#233545',font=ImageFont.truetype(bold if b else font,n))
for name,colour,offset in [('sensor','#81a59d',0),('esp32','#9c88b5',850)]:
 tm=trimesh.load(OUT/('fit_'+name+'_snaps.stl'),force='mesh')
 pic=render([(tm,colour)],(75,-100,110),(800,580));im.paste(pic,(offset+25,115))
text(45,30,'Датчик: две боковые защёлки',31,True)
text(885,30,'ESP32: защёлки и окно USB-C',31,True)
text(45,715,'Гибкие стенки отделены прорезями от основания. Удержание за край текстолита.',28)
text(45,770,'Для снятия развести обе защёлки наружу. Усилие и прочность проверяются печатью.',27)
im.save(OUT/'preview_samples.png')
print(json.dumps(report,indent=2,ensure_ascii=False))
