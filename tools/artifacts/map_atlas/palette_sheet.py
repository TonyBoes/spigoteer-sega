import sys; sys.path.insert(0,'tools/artifacts/map_atlas')
import numpy as np, static as S
from PIL import Image, ImageDraw, ImageFont
st=S.Static(); pal=st.pal; CW,CH=S.CW,S.CH
base=Image.open('.claude/worktrees/agent-afb6b6cfdc3b0bbb4/out/map_atlas/img/map_color.png').convert('RGB').resize((CW*4,CH*4),Image.BOX)
B=np.array(base)
F=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',n)
rows=[]
cnt=np.bincount(pal.ravel(),minlength=len(st.names))
order=sorted(range(len(st.names)),key=lambda i:-cnt[i])
for i in order:
    if cnt[i]==0: continue
    m=np.kron(pal==i,np.ones((4,4),bool))
    a=(B*0.25+40).astype(np.uint8); a[m]=B[m]
    mini=Image.fromarray(a)
    W=1000; H=mini.height+20
    im=Image.new('RGB',(W,H),(30,30,34)); d=ImageDraw.Draw(im)
    im.paste(mini,(W-mini.width-10,10))
    d.text((16,14),st.names[i],fill=(255,255,255),font=F(40))
    d.text((16,66),f"{cnt[i]} cells",fill=(255,210,90),font=F(30))
    for k,c in enumerate(st.rgb[i]):
        d.rectangle((16+k*95,120,16+k*95+85,205),fill=tuple(c),outline=(255,255,255))
        d.text((16+k*95,212),str(k),fill=(200,200,200),font=F(24))
    rows.append(im)
print(len(rows),'palettes used')
# 2 per row? keep 1 column for phone
half=(len(rows)+1)//2; cols=[rows[:half],rows[half:]]; Hs=max(sum(r.height for r in c) for c in cols)+60
out=Image.new("RGB",(2000,Hs),(30,30,34)); ImageDraw.Draw(out).text((16,10),f"Map palettes (Color): {len(rows)} used, most cells first",fill=(255,255,255),font=F(36))
for ci,c in enumerate(cols):
    y=60
    for r in c: out.paste(r,(ci*1000,y)); y+=r.height
out.save('tools/artifacts/open_questions/media/map_palettes.png'); print(out.size)
for i in order: print(st.names[i],cnt[i],[ '#%02x%02x%02x'%tuple(c) for c in st.rgb[i]])
