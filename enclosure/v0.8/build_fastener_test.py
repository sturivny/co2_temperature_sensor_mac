from pathlib import Path
import json
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'build_enclosure.py')}
exec((P/'build_enclosure.py').read_text().split('bs,ls=base().solid(),lid().solid()')[0],ns)
B,C,F,D=ns['B'],ns['C'],ns['F'],ns['D'];export=ns['checked_export']
base=D(B(0,0,0,14,14,12),C(7,7,2,10.2,.85))
cap=D(B(0,0,0,14,14,2),C(7,7,-.1,2.2,1.2),F(7,7,.8,1.3,1.2,2.5))
report={'parts':[export('screw_test_base.stl',base.solid()),export('screw_test_cap.stl',cap.solid())],
 'screw':{'diameter_mm':2,'overall_length_mm':10,'head_diameter_mm':4.6,'assumed_angle_degrees':90},
 'holes':{'countersink_diameter_mm':4.8,'through_diameter_mm':2.4,'pilot_diameter_mm':1.7,'pilot_depth_mm':10},
 'full_case':{'outside_height_mm':17,'head_face_height_if_90_deg_mm':16.9,'screw_tip_mm':6.9,'pilot_bottom_mm':5,'tip_clearance_mm':1.9},
 'notes':'Assumes 10 mm measured including countersunk head. Thread engagement and actual angle require test.'}
(P/'validation_fasteners.json').write_text(json.dumps(report,indent=2)+'\n')
(P/'screw_test.scad').write_text('// Screw fit test, mm. part: base or cap. Cone assumes 90 degrees.\npart="cap";\nmodule base(){'+base.scad()+'}\nmodule cap(){'+cap.scad()+'}\nif(part=="base") base(); else cap();\n')
print(json.dumps(report,indent=2))
