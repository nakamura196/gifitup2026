# PROVENANCE ONLY (not run by build.zsh): how work/masks_traced/*.png was made from user_masks/.
# The committed masks_traced/*.png are its result; it also needs intermediate files not kept here.
# Snap the user's painted masks onto Kuniyoshi's ink lines (full resolution).
# user masks = rough guide; final edges come from a marker watershed on the ink-darkness ridge.
import numpy as np, cv2
from PIL import Image
import os
D=os.path.dirname(os.path.abspath(__file__))+'/'
src=np.asarray(Image.open(D+'dl/tfam.png').convert('RGB'))
H,W=src.shape[:2]
f=src.astype(np.float32); R,G,B=f[...,0],f[...,1],f[...,2]
a=np.asarray(Image.open(D+'user_masks/kuniyoshi_labels.png').convert('RGBA'))
ids=(a[...,0]*(a[...,3]>0)).astype(np.int32)
# stray id4 -> nearest of 2/3
d2=cv2.distanceTransform((ids!=2).astype(np.uint8),cv2.DIST_L2,3); d3=cv2.distanceTransform((ids!=3).astype(np.uint8),cv2.DIST_L2,3)
ids[(ids==4)&(d3<=d2)]=3; ids[ids==4]=2
P={1:'jaw',3:'hand_upper',2:'hand_lower'}
# ---- ink ridge
dark=255-f.mean(-1)
dog=dark-cv2.GaussianBlur(dark,(0,0),3)          # local contrast: faint strokes stand out
elev=0.5*dark+2.0*np.clip(dog,0,None)
rb=cv2.GaussianBlur(R-B,(0,0),1.0)               # skin (R>B) vs paper (B>=R): colour edge where ink is faint
gx=cv2.Sobel(rb,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(rb,cv2.CV_32F,0,1,ksize=3)
elev=elev+0.35*np.sqrt(gx*gx+gy*gy)
elev=cv2.GaussianBlur(elev,(0,0),0.7)
elev8=np.clip(elev,0,255).astype(np.uint8)
inkish=(dog>12)|(dark>110)
bluish=(B>R+3)&(dark<135)
paperish=(f.min(-1)>195)&(B>=R-6)
bgpix=bluish&~inkish&(B>R+8)   # only true blue paper seeds the background; pale highlights inside a body are not paper
# ---- markers
BAND=6
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*BAND+1,2*BAND+1))
markers=np.zeros((H,W),np.int32)
anyp=np.zeros((H,W),np.uint8)
for i in P: anyp|=(ids==i).astype(np.uint8)
for i in P:
    core=cv2.erode((ids==i).astype(np.uint8),k).astype(bool)
    markers[core&~bgpix]=i
STATIC=10; BG=11
far=~cv2.dilate(anyp,k).astype(bool)
markers[far&~bgpix]=STATIC
markers[bgpix&(markers==0)]=BG           # blue paper / pale fringe, also overspill inside a mask
# keep markers only inside a working window around the people
win=cv2.dilate(anyp,np.ones((41,41),np.uint8)).astype(bool)
markers[~win]=STATIC
ws=cv2.watershed(cv2.cvtColor(elev8,cv2.COLOR_GRAY2BGR),markers)
lab=ws.copy()
# watershed ridge pixels (-1): give to the darker-side neighbour majority
r=lab<0
nb=cv2.dilate(np.where(lab>0,lab,0).astype(np.float32),np.ones((3,3))).astype(np.int32)
lab[r]=nb[r]
# ---- the ink stroke itself: a person takes the whole stroke on its OUTER side (toward paper/static),
# and on the hand dividing line the upper man (3) takes it.
def own_stroke(lab,i,others):
    m=(lab==i)
    for _ in range(4):
        ring=cv2.dilate(m.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)&~m
        take=ring&inkish&np.isin(lab,others)&(dark>70)
        if not take.any(): break
        m=m|take
    return m
# snap outward toward the paper: grow (max 6 px, geodesic) into ink or skin-coloured pixels only,
# never into paper (blue or the pale bluish fringe). This fills gaps where the brush stopped short.
growable=(dark>95)|(R>B+6)
for _ in range(6):
    for i in P:
        m=(lab==i).astype(np.uint8)
        ring=cv2.dilate(m,np.ones((3,3),np.uint8)).astype(bool)&(lab==BG)&growable
        lab[ring]=i
L=lab.copy()
L[own_stroke(lab,1,[BG])]=1                       # jaw outline against the paper
L[own_stroke(lab,3,[BG,2])]=3                     # upper man: outline + dividing line
L[own_stroke(L,2,[BG])]=2                         # lower man: outline against paper
# clean: largest piece per person, fill holes, drop specks (no opening: keeps toes/corners)
for i in P:
    m=(L==i).astype(np.uint8)
    n,cc,st,_=cv2.connectedComponentsWithStats(m,connectivity=8)
    if n>2:
        big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); L[(m>0)&(cc!=big)]=BG
    m=(L==i).astype(np.uint8); ff=m.copy(); mm=np.zeros((H+2,W+2),np.uint8)
    cv2.floodFill(ff,mm,(0,0),1); L[(ff==0)]=i
# bridge to an outer ink stroke that is separated from the body by 1-3 px of blue over-print
for i in P:
    m=(L==i).astype(np.uint8)
    dm=cv2.distanceTransform(1-m,cv2.DIST_L2,5)
    inkc=((L==BG)&(dark>130)&(dm<=5)).astype(np.uint8)
    if inkc.sum()==0: continue
    di=cv2.distanceTransform(1-inkc,cv2.DIST_L2,5)
    add=(L==BG)&(dm<=5)&(dm+di<=5.5)
    L[add]=i
# fill small notches between the body and its own outer ink stroke (concavities <= 5 px),
# but never with blue paper, so gaps between toes stay open
for i in P:
    m=(L==i).astype(np.uint8)
    cl=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5))).astype(bool)
    add=cl&(m==0)&(L==BG)&~(B>R+8)
    L[add]=i
np.save(D+'work/traced_labels.npy',L)
# ---- antialiased alpha: 4x supersampled mask edge from the ink-weighted label boundary
for i,n in P.items():
    m=(L==i).astype(np.float32)
    up=cv2.resize(m,(W*4,H*4),interpolation=cv2.INTER_LINEAR)       # bilinear = sub-pixel edge
    up=(up>0.5).astype(np.float32)
    al=cv2.resize(up,(W,H),interpolation=cv2.INTER_AREA)
    Image.fromarray((al*255).astype(np.uint8)).save(D+'work/masks_traced/%s.png'%n)
    print(n,int(m.sum()),'user',int((ids==i).sum()))
# ---- views
COL={1:(255,0,0),3:(255,140,0),2:(0,90,255)}
def contours(i):
    cs,_=cv2.findContours((L==i).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); return cs
ov=src.copy()
for i in P: cv2.drawContours(ov,contours(i),-1,COL[i],1)
Image.fromarray(ov).save(D+'trace_overlay.png')
def cu(box,s=3):
    x0,y0,x1,y1=box
    c=cv2.resize(src[y0:y1,x0:x1],None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC).copy()
    for i in P:
        for ct in contours(i):
            p=((ct[:,0,:]-[x0,y0])*s+s//2).astype(np.int32)
            cv2.polylines(c,[p],True,COL[i],1,cv2.LINE_AA)
    return c
boxes={'jaw':(170,620,500,940),'toes':(90,950,270,1080),'thumb':(390,930,530,1180),'divide':(250,1040,560,1260)}
crops={n:cu(b) for n,b in boxes.items()}
for n,c in crops.items(): Image.fromarray(c).save(D+'work/tcu_%s.png'%n)
# assemble
from PIL import ImageDraw, ImageFont
fnt=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',24)
ims={n:Image.fromarray(c) for n,c in crops.items()}
row1=[ims['jaw'],ims['divide']]; row2=[ims['toes'],ims['thumb']]
Wt=max(sum(i.width for i in row1),sum(i.width for i in row2))+20
Ht=max(i.height for i in row1)+max(i.height for i in row2)+80
out=Image.new('RGB',(Wt,Ht),'white'); d=ImageDraw.Draw(out)
x=0
for n,im in zip(['jaw (x170-500,y620-940)','hand dividing line (x250-560,y1040-1260)'],row1):
    d.text((x+4,4),n,fill=0,font=fnt); out.paste(im,(x,34)); x+=im.width+20
y=34+max(i.height for i in row1)+10; x=0
for n,im in zip(['fingertips / toes (x90-270,y950-1080)','thumb (x390-530,y930-1180)'],row2):
    d.text((x+4,y),n,fill=0,font=fnt); out.paste(im,(x,y+30)); x+=im.width+20
out.save(D+'trace_closeups.png'); print(out.size)
