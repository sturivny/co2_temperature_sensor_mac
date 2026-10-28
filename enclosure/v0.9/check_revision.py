"""Check v0.9 reinforcement, top-open wiring slot, flat M2 lid and delivered STL."""
from pathlib import Path
import hashlib
import json
import numpy as np
import manifold3d as m
import trimesh

P=Path(__file__).resolve().parent
ns={'__file__':str(P/'build_enclosure.py')}
exec((P/'build_enclosure.py').read_text().split('bs,ls=base().solid(),lid().solid()')[0],ns)
B=ns['B'];ESP=ns['ESP']
def load(path):
 tm=trimesh.load(path,force='mesh',process=True)
 assert tm.is_watertight and tm.is_winding_consistent,path.name
 solid=m.Manifold(m.Mesh(np.asarray(tm.vertices,dtype=np.float32),np.asarray(tm.faces,dtype=np.uint32)))
 assert solid.status()==m.Error.NoError and len(solid.decompose())==1,path.name
 return solid,tm
base,_=load(P/'base.stl');old,_=load(P.parent/'v0.8/base.stl')
lid_print,_=load(P/'lid.stl')
lid=lid_print.rotate((180,0,0)).translate((0,ns['W'],ns['H']))
report={'version':'0.9','parts':[],'checks':{},'strength':'Not load-tested or FEA-validated; physical test print required.'}
for p in sorted(P.glob('*.stl')):
 s,tm=load(p);report['parts'].append({'file':p.name,'bounds_mm':tm.extents.round(3).tolist(),'watertight':True,'consistent_winding':True,'connected_solids':1})
assert len(report['parts'])==8
assert abs((base^lid).volume())<1e-5
# Check the contact face without extending into the fitted board or its clearance.
contact_x=ESP[0]-.15;cy=ESP[1]+ESP[3]/2
face=B(contact_x-.1,cy-3.9,5.,.09,7.8,1.5).solid()
assert abs((base^face).volume()-face.volume())<1e-5
clear=B(contact_x+.01,cy-3.9,5.,.13,7.8,1.5).solid()
assert abs((base^clear).volume())<1e-5
section=B(40.,14.,2.01,11.1,10.5,.02).solid()
old_area=(old^section).volume()/.02;new_area=(base^section).volume()/.02
assert abs(old_area-6.6)<.01 and abs(new_area-100.)<.01
report['checks']['root_cross_section_mm2']={'v08':round(old_area,3),'v09':round(new_area,3),'not_a_strength_multiplier':True}
report['checks']['rear_stop_contact_clearance_mm']=.15
# A wire bundle can be lowered vertically through the central divider opening.
# This checks a 7.8 x 2.18 mm envelope, not wire flex or actual solder joints.
slot=B(32.91,17.1,2.01,2.18,7.8,18.).solid()
assert abs((base^slot).volume())<1e-5
report['checks']['wiring_slot']={'width_mm':8.,'open_from_top':True,'geometric_drop_envelope_clear':True}
for x,y in ns['SCREWS']:
 hole=ns['C'](x,y,14.95,2.1,1.19).solid()
 assert abs((lid^hole).volume())<1e-5
 annulus=ns['D'](ns['C'](x,y,16.9,.08,2.7),ns['C'](x,y,16.89,.1,1.3)).solid()
 assert abs((lid^annulus).volume()-annulus.volume())<1e-5
report['checks']['lid_fasteners']={'clearance_diameter_mm':2.4,'countersink':False,'flat_external_seat_diameter_checked_mm':5.4,'m2x10_tip_clearance_mm':2.}
# The only material removed from the old base is inside the new wire opening.
removed=old-base
allowed=B(32.89,16.99,1.89,2.22,8.02,17.02).solid()
assert (removed-allowed).volume()<1e-4
report['checks']['removed_base_material_confined_to_wire_slot']=True
for name in ['fit_sensor.stl','fit_sensor_snaps.stl']:
 assert (P/name).read_bytes()==(P.parent/'v0.8'/name).read_bytes()
report['checks']['sensor_samples_byte_identical_to_v08']=True
(P/'validation_revision.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
