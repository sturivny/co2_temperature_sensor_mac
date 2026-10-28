from pathlib import Path
import json
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'build_enclosure.py')}
exec((P/'build_enclosure.py').read_text().split('bs,ls=base().solid(),lid().solid()')[0],ns)
B,C,F,D=ns['B'],ns['C'],ns['F'],ns['D'];export=ns['checked_export']
base=D(B(0,0,0,14,14,12),C(7,7,2,10.2,.85))
cap=D(B(0,0,0,14,14,2),C(7,7,-.1,2.2,1.2))
report={'parts':[export('screw_test_base.stl',base.solid()),export('screw_test_cap.stl',cap.solid())],
 'screw':{'diameter_mm':2,'length_under_head_mm':10,'head_seating':'flat_outside_cap'},
 'holes':{'countersink':False,'through_diameter_mm':2.4,'pilot_diameter_mm':1.7,'pilot_depth_mm':10},
 'full_case':{'outside_height_mm':17,'head_seating_height_mm':17.,'screw_tip_mm':7.,'pilot_bottom_mm':5,'tip_clearance_mm':2.},
 'notes':'Assumes M2 x 10 mm measured under the head. Socket head seats flat outside; thread engagement requires a physical test.'}
(P/'validation_fasteners.json').write_text(json.dumps(report,indent=2)+'\n')
(P/'screw_test.scad').write_text('// Screw fit test, mm. part: base or cap. Flat seating for external socket heads, no countersink.\npart="cap";\nmodule base(){'+base.scad()+'}\nmodule cap(){'+cap.scad()+'}\nif(part=="base") base(); else cap();\n')
print(json.dumps(report,indent=2))
