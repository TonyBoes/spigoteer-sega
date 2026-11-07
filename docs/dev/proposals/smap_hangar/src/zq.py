import sys
import mtn_h as M
import common as C
from PIL import Image
out=[]
for plane,tone in (('A','2'),('B','2'),('A','1')):
    im=C.render(M.build('h2e',True,plane,tone),M.BIOME,M.AT,False).crop((0,40,72,72+8))
    out.append(im)
w=Image.new('RGB',(sum(i.width for i in out)+20,out[0].height),(40,40,40)); x=0
for i in out: w.paste(i,(x,0)); x+=i.width+10
w.resize((w.width*5,w.height*5),Image.NEAREST).save('/workspace/.claude/worktrees/agent-a958d884767ee8afe/out/hangar/zq.png')
