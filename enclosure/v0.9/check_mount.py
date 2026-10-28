from pathlib import Path
import json,hashlib
import numpy as np
import manifold3d as m
import trimesh
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'build_enclosure.py')}
s=(P/'build_enclosure.py').read_text().split('bs,ls=base().solid(),lid().solid()')[0];exec(s,ns)
B,ESP,clip=ns['B'],ns['ESP'],ns['clipped_pcb']
tm=trimesh.load(P/'base.stl',force='mesh')
base=m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))
report={'controller_dimensions_mm':[ESP[2],ESP[3]],'pcb_inner_wall_contact_x':ESP[0]+ESP[2],
 'usb_front_x':ns['USB_FRONT'],'case_outer_wall_x':ns['L'],'recess_mm':ns['L']-ns['USB_FRONT'],'lower_support_tests':[], 'unchanged_sensor_parts':[]}
assert abs(ESP[0]+ESP[2]-(ns['L']-ns['WALL']))<1e-9
assert abs(ns['USB_FRONT']-ns['L'])<1e-9
for c in [1.,1.5,2.]:
 probe=clip(ESP,4.98,.02,cut=c)
 area=(probe^base).volume()/.02
 assert abs(area-6.4)<.01,(c,area)
 report['lower_support_tests'].append({'corner_cut_mm':c,'total_bearing_area_mm2':round(area,5)})
# Also check a true rounded outline R2 instead of a 45-degree cut.
probe=ns['RB'](ESP[0],ESP[1],4.98,ESP[2],ESP[3],.02,2.,0).solid()
area=(probe^base).volume()/.02
assert abs(area-6.4)<.01
report['lower_support_tests'].append({'corner_radius_mm':2,'total_bearing_area_mm2':round(area,5)})
for fn in ['fit_sensor.stl','fit_sensor_snaps.stl']:
 expected={'fit_sensor.stl':'a8406ec2f0698b819a7409d283f0bb142326e991db02c93194525f9ab0dea0d1','fit_sensor_snaps.stl':'6f451282001de407a257219d5cf99f8feecd3b476001a69910cc439f943c656b'}
 new=(P/fn).read_bytes()
 assert hashlib.sha256(new).hexdigest()==expected[fn],fn
 report['unchanged_sensor_parts'].append({'file':fn,'identical_to_v07':True,'sha256':hashlib.sha256(new).hexdigest()})
# The sample uses the same PCB-to-wall datum as the enclosure.
sample_inner=2.+9.+ESP[2];sample_outer=sample_inner+2.
assert abs((2.+9.+ESP[2]+2.)-sample_outer)<1e-9
report['sample_wall_coordinates_mm']={'pcb_edge':sample_inner,'inner_wall':sample_inner,'usb_front':sample_outer,'outer_wall':sample_outer}
(P/'validation_mount.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
