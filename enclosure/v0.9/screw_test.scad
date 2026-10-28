// Screw fit test, mm. part: base or cap. Flat seating for external socket heads, no countersink.
part="cap";
module base(){difference(){
translate([0, 0, 0]) cube([14, 14, 12]);
translate([7, 7, 2]) cylinder(h=10.2,r=0.85,$fn=48);
}}
module cap(){difference(){
translate([0, 0, 0]) cube([14, 14, 2]);
translate([7, 7, -0.1]) cylinder(h=2.2,r=1.2,$fn=48);
}}
if(part=="base") base(); else cap();
