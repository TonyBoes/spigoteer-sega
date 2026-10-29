from PIL import Image, ImageDraw, ImageFont
src=open('build.py').read().split('\n# ---- Scene pieces')[0]
g={'__file__':'/workspace/tools/artifacts/palette_plan/build.py','__name__':'x'}
exec(compile(src,'build.py','exec'),g)
V={v['key']:v for v in g['venues']}
NP={n:c for l in g['NEW_PATRONS'].values() for n,c in l}
def pal(k,o):
    v=V[k]; m=g['model'](v); return g['eff'](m[('OBJ',o)])[1:]
# venue, title, rows: (patron, [own], A (label, slot), B (label, slot))
SETS=[("divers","Igloo",[("MUSHER",("CUB","OBJ 5",5),("Full mug","OBJ 1",1)),("YETI",("Empty mug","OBJ 2",2),("CUB","OBJ 5",5))]),
      ("robots","Factory",[("CLANK",("VOLTA","OBJ 6",6),("Full mug","OBJ 1",1)),("BUBBLE",("NEKA","OBJ 4",4),("BLIP","OBJ 7",7))]),
      ("ninjas","Teahouse",[("SENSEI",("POET","OBJ 5",5),("own","OBJ 5",None)),("POET",("own","OBJ 5",None),("SENSEI","OBJ 5","SENSEI")),("MONK",("RONIN","OBJ 7",7),("RONIN","OBJ 7",7))]),
      ("aliens","Space",[("MOTH",("own","OBJ 3",None),("XENO","OBJ 2",2)),("VIXEN_B",("XENO","OBJ 2",2),("XENO","OBJ 2",2)),("VIXEN_D",("BLOB","OBJ 4",4),("own","OBJ 3",None))])]
S=4; F=16*S; font=ImageFont.load_default()
try: font=ImageFont.truetype('/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',13)
except Exception:
    import glob; fs=glob.glob('/usr/share/fonts/**/DejaVuSans*.ttf',recursive=True)
    if fs: font=ImageFont.truetype(fs[0],13)
CW=F+60; RH=F+34
rows_total=sum(len(r)+1 for _,_,r in SETS)
W=110+3*CW; H=rows_total*RH+10
im=Image.new('RGB',(W,H),'#1c2026'); d=ImageDraw.Draw(im)
def fig(k,name,cols,x,y):
    v=V[k]; m=g['model'](v); f=g['field_model'](v,m); wall=g['eff'](f[0])[0]
    rows=g['art_rows'](v,name); c=[wall]+list(cols)
    d.rectangle([x,y,x+F-1,y+F-1],fill=wall)
    for r,line in enumerate(rows):
        for cx,ch in enumerate(line):
            i='.-+#'.index(ch)
            if i: d.rectangle([x+cx*S,y+r*S,x+cx*S+S-1,y+r*S+S-1],fill=c[i])
y=6
for k,title,rows in SETS:
    d.text((8,y+8),title,fill='#f2d24b',font=font)
    for j,h in enumerate(["Own","A","B"]): d.text((110+j*CW,y+8),h,fill='#f2d24b',font=font)
    y+=RH//2+6
    for name,A,B in rows:
        d.text((8,y+F//2-8),name,fill='#e6eaee',font=font)
        fig(k,name,NP[name],110,y)
        for j,(lab,slot,o) in enumerate((A,B)):
            x=110+(j+1)*CW; cols=NP[name] if o is None else NP[o] if isinstance(o,str) else pal(k,o)
            fig(k,name,cols,x,y); d.text((x,y+F+2),lab if o is None else lab,fill='#9aa4ae',font=font)
        y+=RH
    y+=RH//2-6
im=im.crop((0,0,W,y)); im.save('/workspace/tools/artifacts/open_questions/media/q43_merges.png'); print(im.size)
