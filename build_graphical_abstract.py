from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

OUT=Path(__file__).resolve().parent
W=H=1500
img=Image.new('RGB',(W,H),'white')
d=ImageDraw.Draw(img)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fontb='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fonti='/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'
F=lambda n,b=False,i=False: ImageFont.truetype(fontb if b else fonti if i else font,n)
navy='#183A5B'; teal='#0C7C7C'; green='#2D8A57'; orange='#D97706'; gray='#53616D'; light='#F4F7F8'; pale='#EAF5F4'; red='#B24A4A'

def centered(text, box, f, fill=navy, spacing=6):
    x0,y0,x1,y1=box
    bb=d.multiline_textbbox((0,0),text,font=f,spacing=spacing,align='center')
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    d.multiline_text(((x0+x1-tw)/2,(y0+y1-th)/2),text,font=f,fill=fill,spacing=spacing,align='center')

def rbox(box, outline=gray, fill=light, width=3, radius=18):
    d.rounded_rectangle(box,radius=radius,fill=fill,outline=outline,width=width)

def arrow(x0,y0,x1,y1,color=teal,width=5,head=14):
    d.line((x0,y0,x1,y1),fill=color,width=width)
    ang=math.atan2(y1-y0,x1-x0)
    pts=[(x1,y1),(x1+head*math.cos(ang+2.6),y1+head*math.sin(ang+2.6)),(x1+head*math.cos(ang-2.6),y1+head*math.sin(ang-2.6))]
    d.polygon(pts,fill=color)

centered('Distributed AI as a rural heat resource',(55,35,1445,110),F(42,True))
centered('Same 63.96 MW compute service; siting changes what the heat can displace',(80,110,1420,160),F(22),gray)

rbox((90,205,560,365),gray,light)
centered('Single campus\n63.96 MW IT',(90,205,560,365),F(28,True))
rbox((910,205,1410,365),teal,pale)
centered('11 liquid-cooled nodes\n13 municipalities\ndedicated dark-fibre fabric',(910,205,1410,365),F(23,True))
arrow(580,285,890,285,navy,6,18)
centered('redistribute compute',(590,225,880,270),F(18,True),navy)
centered('heat rejected to ambient',(120,370,500,415),F(18,True),red)

centered('Recovered heat — the distribution-specific climate mechanism',(100,430,1400,490),F(25,True),navy)
heat_boxes=[
    ((80,525,455,705),'District heating\n4,934 homes',green),
    ((562,525,937,705),'Alfalfa drying\n79.6 GWh heat',orange),
    ((1045,525,1420,705),'Greenhouses +\naquaculture',green),
]
for box,txt,col in heat_boxes:
    rbox(box,col,'#F3F8F4')
    centered(txt,box,F(23,True))
arrow(1295,370,1295,485,teal,4,13)
d.line((267,505,1232,505),fill=teal,width=4)
for tx in [267,750,1232]: arrow(tx,505,tx,520,teal,4,11)
arrow(1295,485,1232,505,teal,4,11)

centered('Integrated community programme — enabled by project finance, not uniquely by distribution',(120,755,1380,815),F(23,True),navy)
prog=[
    ((90,850,470,1015),'EVs + renewable fuels',gray),
    ((560,850,940,1015),'Manure → biomethane\n30.3 GWh yr⁻¹',teal),
    ((1030,850,1410,1015),'Cooking +\nfarm machinery +\noff-network heat',gray),
]
for box,txt,col in prog:
    rbox(box,col,'#F5F7F8' if col==gray else pale)
    centered(txt,box,F(19,True))
arrow(950,930,1015,930,teal,4,12)

band=(65,1075,1435,1325)
d.rounded_rectangle(band,radius=20,fill=navy)
cols=[(85,392),(402,709),(719,1026),(1036,1415)]
kpis=[
    ('45.1 ktCO₂e yr⁻¹','fossil-heat emissions displaced'),
    ('81 kgCO₂e/MWh IT','primary siting metric'),
    ('68%','territorial emissions reduction'),
    ('69.7%','integrated programme screen'),
]
for (x0,x1),(big,small) in zip(cols,kpis):
    centered(big,(x0,1100,x1,1175),F(25,True),'white')
    centered(small,(x0,1180,x1,1285),F(15),'white')

centered('Only recovered-heat displacement is physically attributable to distributed siting.',(100,1360,1400,1405),F(17,True),navy)
centered('Programme-financed measures and food-system substitution are reported separately.',(100,1405,1400,1460),F(16,i=True),gray)

img.save(OUT/'Graphical_Abstract.png',dpi=(300,300))
img.save(OUT/'Graphical_Abstract.tiff',compression='tiff_lzw',dpi=(300,300))
img.save(OUT/'Graphical_Abstract.pdf',resolution=300.0)
print(OUT/'Graphical_Abstract.png')
