import numpy as np, cv2, sys, os
D=sys.argv[1]
DL=os.environ.get('DL', f'{D}/dl')
im=cv2.imread(f'{DL}/p83.jpg')
lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
def mask(box,thr,DK=18,CK=15):
    x0,y0,x1,y1=box
    sub=lab[y0:y1,x0:x1]
    paper=np.median(sub.reshape(-1,3),axis=0)
    L,a,b=sub[...,0],sub[...,1],sub[...,2]
    # ink: darker, or more chromatic (warm/green) than paper; ghost is bluish-grey (b lower)
    d=np.sqrt(((a-paper[1])*1.5)**2+((b-paper[2])*1.0)**2)
    dark=(paper[0]-L)
    warm = (b-paper[2])>-6   # not bluish
    m=(((d>thr)|(dark>DK)) & warm) | (dark>60)
    m=m.astype(np.uint8)*255
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(CK,CK)))
    n,lbl,st,_=cv2.connectedComponentsWithStats(m)
    keep=np.zeros_like(m)
    for i in range(1,n):
        if st[i,4]>1500: keep[lbl==i]=255
    cs,_=cv2.findContours(keep,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(keep,cs,-1,255,-1)
    full=np.zeros(im.shape[:2],np.uint8); full[y0:y1,x0:x1]=keep
    return full,paper
for name,box,thr,DK,CK in [('adult',(850,1240,1345,1620),9,18,31),('nymph',(455,1445,785,1680),9,18,15)]:
    m,p=mask(box,thr,DK,CK)
    cv2.imwrite(f'{D}/work/m_{name}.png',m)
    x0,y0,x1,y1=box
    vis=im.copy(); vis[m==0]=(vis[m==0]*0.3+np.array([255,0,255])*0.7).astype(np.uint8)
    cv2.imwrite(f'{D}/work/v_{name}.jpg',vis[y0:y1,x0:x1])
    print(name,p)
# post-fix nymph: drop paper-like pixels inside filled mask that are far from ink
m=cv2.imread(f'{D}/work/m_nymph.png',0)
L=lab[...,0];a=lab[...,1];b=lab[...,2]
paperlike=((np.abs(a-131)<4)&(np.abs(b-148)<6)&(L>170)).astype(np.uint8)*255
paperlike=cv2.bitwise_and(paperlike,m)
paperlike=cv2.morphologyEx(paperlike,cv2.MORPH_OPEN,np.ones((7,7),np.uint8))
n,lbl,st,_=cv2.connectedComponentsWithStats(paperlike)
for i in range(1,n):
    if st[i,4]>300: m[cv2.dilate((lbl==i).astype(np.uint8),np.ones((3,3),np.uint8))>0]=0
cv2.imwrite(f'{D}/work/m_nymph.png',m)
x0,y0,x1,y1=(455,1445,785,1680)
vis=im.copy(); vis[m==0]=(vis[m==0]*0.3+np.array([255,0,255])*0.7).astype(np.uint8)
cv2.imwrite(f'{D}/work/v_nymph.jpg',vis[y0:y1,x0:x1])
