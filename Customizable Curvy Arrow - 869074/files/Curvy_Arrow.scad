//Name: Curvy Arrow
//Created by Ari M. Diacou, April-June 2015
//Shared under Creative Commons License: Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0) 
//see http://creativecommons.org/licenses/by-sa/3.0/

//INSTRUCTIONS:
/* The code below produces an arrow with curvy edges. It does this by intersecting and taking the difference of 4 pairs of circles. 2 circles form the tip of the arrow (set1), and 2 form the back of the tip of the arrow(set2). The sides of the shaft are formed by set3, and the tail of the arrow is formed by set 4. 

The circles are specified by a modified polar coordinate system called "easy_form" which is ={distance from origin to circle edge, radius of circle, angle between +x-axis and cicle center in degrees}. This coordinate system is SLIGHTLY easier to get a grasp of entering values. Changing the first value will push a curve farther from the origin (the center of the arrow). Lowering the 2nd number will make a line more curvy (by lowering the radius of the circle it creates). Raising the 2nd number will make a line more flat (by increasing the radius of the circle it creates). Changing the 3rd number is how you get position control. The 3rd number is the angle that the angle that the line connecting the origin and the center of the circle will make with the x-axis.Both the first and the third parameters can be negative. Negative radii will fail silently.

It is highly reccommended that this program be used in OpenSCAD and not customizer. There is no input checking, and a lot of edge cases where circles will not intersect. If instead of an arrow looking thing, cutomizer or OpenSCAD show you two circles floating in space, it means that the circles are not intersecting, and the program is failing silently. If you wish to make a 2D file, use 0 for the height (I dont think this works in customizer).

The last 4 functions in this program are used to calculate the points where the circles intersect, which is used to calculate the length and width of the arrow. This information is available through the echo function, and not visible in customizer. So if you want to know the dimensions of your arrow, use OpenSCAD.*/

//The tip of the arrow [origin to edge, radius, polar position angle] e.g. [1,5,35]
set1=[1,5,35];      
//The back of the arrow tip [origin to edge, radius, polar position angle] e.g. [0,10,75]
set2=[0,10,75];     
//The sides of the shaft [origin to edge, radius, polar position angle] e.g. [.5,10,0]
set3=[.5,10,0];      
//The back of the shaft [origin to edge, radius, polar position angle] e.g. [-1.5,10,60]
set4=[-3,10,60];
//Height of your arrow, use 0 offline to output a DXF file
height=1;

/* HIDDEN */
///// Derived Parameters /////
ep=0.05; //epsilon, a small number
tip= intersection(set1,[set1[0],set1[1],180-set1[2]]); echo(str("tip=",tip));
back=intersection(set3,set4); echo(str("back = ",back));
side=intersection(set1,set2); echo(str("side = ",side));
length=tip[1]-back[1]; echo(str("length = ",length));
width=2*max(side[0],back[0]); echo(str("width = ", width));
//real_height = height < ep ? ep : height; //input handl
/////////// MAIN() //////////
//if the height is less than epsilon, output a 2D file, else: output a 3D file with the specified height. I dont know if customizer can output DXF files, so I think this will only work in OpenSCAD.
if(height < ep)
    arrow();
else
    linear_extrude(height) arrow();
echo(str(
    "A suggested name for your arrow is: curvy_arrow-sets=[",set1,set2,set3,set4,"],h=",height
    ));
///////// FUNCTIONS /////////
function intersection(circle1,circle2)=(norm(intersections(circle1,circle2)[0])<=norm(intersections(circle1,circle2)[1]))?intersections(circle1,circle2)[0]:intersections(circle1,circle2)[1];
function xyr_form(easy_form)=[
    //easy_form={distance from origin to circle edge, radius of circle,angle between +x-axis and cicle center}
    //xyr_form={x-cooridante of center,y-coordinate of center,radius of circle}
    (easy_form[0]+easy_form[1])*cos(easy_form[2]), //x=(diff+r)*cos(theta)
    (easy_form[0]+easy_form[1])*sin(easy_form[2]), //y=(diff+r)*sin(theta)
    easy_form[1] //r
    ];
module arrow(){
    top();
    bottom();
    }
module top(){ //The tip of the arrow
    difference(){
        intersection(){
            square(2*tip[1],center=true);
            pair(set2,$fn=200); //The back of the arrow
            }
        pair(set1,$fn=100); //The tip of the arrow
        }
    }
module bottom(){ //The shaft of the arrow
    difference(){
        intersection(){
            translate([0,-2.5,0])
                square(5,center=true);
            pair(set4,$fn=200); //The sides of the shaft
            }
        pair(set3,$fn=100); //The backof the shaft
        }
    }
function chord_of_circle_intersection(d,r,R)=(1/d)*sqrt(4*d*d*R*R-pow(d*d-r*r+R*R,2)); //from: http://mathworld.wolfram.com/Circle-CircleIntersection.html, Equation 8
module pair(triplet){
    /* Makes a pair of circles on the x-y plane for making the 8 arcs of the arrow. An array "triplet" is passed into the function which specifies the position and size of the circles. The 2nd parameter is the radius of the circles, the third is the angle that the line connecting the origin and the center of the circle will make with the x-axis, and the first parameter of the array is the distance between the origin and the nearest edge of the circle. Both the first and the third parameters can be negative. Negative radii will fail silently.*/
    radius=triplet[1]; 
    x=xyr_form(triplet)[0];
    y=xyr_form(triplet)[1];
    translate([x,y,0])
        circle(radius);
    translate([-x,y,0])
        circle(radius);
}
function intersections(circle1,circle2)=[
    [x1sol(xyr_form(circle1)[0],xyr_form(circle1)[1],xyr_form(circle1)[2],xyr_form(circle2)[0],xyr_form(circle2)[1],xyr_form(circle2)[2]),
    y1sol(xyr_form(circle1)[0],xyr_form(circle1)[1],xyr_form(circle1)[2],xyr_form(circle2)[0],xyr_form(circle2)[1],xyr_form(circle2)[2])],
    [x2sol(xyr_form(circle1)[0],xyr_form(circle1)[1],xyr_form(circle1)[2],xyr_form(circle2)[0],xyr_form(circle2)[1],xyr_form(circle2)[2]),
    y2sol(xyr_form(circle1)[0],xyr_form(circle1)[1],xyr_form(circle1)[2],xyr_form(circle2)[0],xyr_form(circle2)[1],xyr_form(circle2)[2])]
    ];
//The following are the solutions to the intersection of two circles with arbitrary radius and coordinates. Solved with Mathematica (9 Student/Home) on a Raspberry Pi using the algorithm discussed here: http://mathematica.stackexchange.com/questions/80695/formatting-an-equation-xy-to-powx-y, with many thanks to all the respondants. A circle intersects another at 0, 1 or 2 points. If circles do not intersect, then the following solutions would ideally be complex numbers. If they intersect at 1 point then (x1sol,x2sol)=(x2sol,y2sol). In the case of sensible inputs which create an arrow like we have in this program, there will be 2 solutions. In our case we will take the one that is closer to the origin. This will allow us to calculate the length and width of the arrow, so it can be scaled later.
function x1sol(x1,y1,r1,x2,y2,r2)=x1 + (r1*(((-x1 + x2)*(-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))))/(2.*r1) + ((-y1 + y2)*sqrt((1 + ((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)) - sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)*(1 + (-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)))/r1))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2));
function y1sol(x1,y1,r1,x2,y2,r2)=y1 + (r1*(((-y1 + y2)*(-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))))/(2.*r1) - ((-x1 + x2)*sqrt((1 + ((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)) - sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)*(1 + (-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)))/r1))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2));
function x2sol(x1,y1,r1,x2,y2,r2)=x1 + (r1*(((-x1 + x2)*(-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))))/(2.*r1) - ((-y1 + y2)*sqrt((1 + ((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)) - sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)*(1 + (-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)))/r1))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2));
function y2sol(x1,y1,r1,x2,y2,r2)=y1 + (r1*(((-y1 + y2)*(-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))))/(2.*r1) + ((-x1 + x2)*sqrt((1 + ((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)) - sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)*(1 + (-((-1 + pow(r2,2)/pow(r1,2))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2))) + sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2)))/2.)))/r1))/sqrt(pow(-x1 + x2,2)/pow(r1,2) + pow(-y1 + y2,2)/pow(r1,2));