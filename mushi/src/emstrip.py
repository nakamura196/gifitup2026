import sys
from PIL import Image
D=sys.argv[1]; idx=[int(x) for x in sys.argv[2].split(',')]; out=sys.argv[3]
box=(40,400,360,700)
ims=[Image.open(f'{D}/frames/f{i:03d}.png').crop(box).resize((480,450),Image.LANCZOS) for i in idx]
cols=4; rows=(len(ims)+cols-1)//cols
s=Image.new('RGB',(480*cols,450*rows))
for k,im in enumerate(ims): s.paste(im,((k%cols)*480,(k//cols)*450))
s.save(out,quality=88)
