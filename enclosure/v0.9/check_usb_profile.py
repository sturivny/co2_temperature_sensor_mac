from pathlib import Path
import json, math
import numpy as np
import manifold3d as m
import trimesh
P=Path(__file__).resolve().parent
namespace={'__file__':str(P/'build_enclosure.py')}
exec((P/'build_enclosure.py').read_text().split('bs,ls=base().solid(),lid().solid()')[0],namespace)
B=namespace['B'];capsule=namespace['capsule_x'];results=[]
for fn,x,y in [('base.stl',77.,19.3),('fit_esp32.stl',36.8,12.3),('fit_esp32_snaps.stl',36.8,12.3)]:
 tm=trimesh.load(P/fn,force='mesh',process=True)
 solid=m.Manifold(m.Mesh(np.array(tm.vertices,dtype=np.float32),np.array(tm.faces,dtype=np.uint32)))
 box=B(x-.1,y-4.8,5.8,.2,9.6,3.6).solid()
 hole=capsule(x-.1,y-4.8,5.8,.2,9.6,3.6).solid()
 blocked=(solid^hole).volume()
 assert abs(blocked)<1e-5,(fn,blocked)
 area=9.6*3.6-(solid^box).volume()/.2
 target=(9.6-3.6)*3.6+math.pi*1.8**2
 assert abs(area-target)<.012,(fn,area,target)
 # All four bounding-rectangle corners must contain plastic (not square cutout).
 corners=[]
 for yy in [y-4.8+.02,y+4.8-.10]:
  for zz in [5.82,9.30]:
   q=B(x-.04,yy,zz,.08,.08,.08).solid()
   ratio=(q^solid).volume()/q.volume()
   assert ratio>.999,(fn,ratio)
   corners.append(round(ratio,5))
 results.append({'file':fn,'open_profile_area_mm2':round(area,5),'analytic_capsule_area_mm2':round(target,5),'material_blocking_profile_mm3':round(blocked,8),'filled_corner_fraction':corners})
(P/'validation_usb_profile.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
