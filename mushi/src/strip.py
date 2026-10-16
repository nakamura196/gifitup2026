import sys,os
from PIL import Image
D=sys.argv[1]; idx=[int(x) for x in sys.argv[2].split(',')]
ims=[Image.open(f'{D}/frames/f{i:03d}.png') for i in idx]
w,h=ims[0].size; cols=4; rows=(len(ims)+cols-1)//cols
s=Image.new('RGB',(w*cols,h*rows),'white')
for k,im in enumerate(ims): s.paste(im,((k%cols)*w,(k//cols)*h))
s.save(sys.argv[3] if len(sys.argv)>3 else f'{D}/strip.jpg',quality=85)
