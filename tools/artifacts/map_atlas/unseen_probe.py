import sys; sys.path.insert(0,'tools/artifacts/map_atlas')
import numpy as np, static as S
from collections import Counter
st=S.Static(); CW,CH=S.CW,S.CH
vis=np.zeros((CH,CW),bool); pad=np.zeros((CH,CW),bool)
views=[v for smp in st.leg_samples for (_,_,v) in smp]+[r[3] for r in st.rest]
# resting glides
G=S.G
for n,(sx,sy) in zip(st.order,st.stops):
    vx,vy,_=G.STOP_VIEW.get(n,(None,None,1))
    if vx is not None or vy is not None:
        for i in range(33):
            fx= sx if vx is None else vx+80+(sx-80-vx)*i//32
            fy= sy if vy is None else vy+G.SAL_Y+(sy-G.SAL_Y-vy)*i//32
            views.append(st.view(*S.cam(fx,fy)))
for v in views:
    c0,c1,r0,r1=v["view"]; vis[r0:r1+1,c0:c1+1]=True
    p0,p1,q0,q1=v["win"]; pad[q0:q1+1,p0:p1+1]=True
print("cells total",CW*CH,"seen",vis.sum(),"never seen",(~vis).sum(),"of which loaded in margin only",(pad&~vis).sum())
for name,g in (("DMG",st.gD),("Color",st.gC)):
    seen=set(np.unique(g[vis])); allt=set(np.unique(g)); un=allt-seen
    print(name,"tiles total",len(allt),"never on screen",len(un))
    # which pieces hold them
    c=Counter()
    for y in range(CH):
        for x in range(CW):
            if not vis[y,x] and g[y,x] in un: c[st.piece_names[st.piece[y,x]]]+=1
    print("  cells holding them by piece:",c.most_common(12))
# bounding of unseen regions
ys,xs=np.where(~vis); print("unseen rows",sorted(set(ys))[:5],"...", "cols range",xs.min(),xs.max())
np.save('/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/vis.npy',vis)
# picture
from PIL import Image
im=Image.open('assets/smap/world_c.png').convert('RGB'); a=np.array(im)
m=np.kron(~vis,np.ones((8,8),bool)); a[m]=(a[m]*0.35+np.array([200,0,0])*0.65).astype(np.uint8)
Image.fromarray(a).resize((1024,1120),Image.NEAREST).save('/tmp/claude-1000/-workspace/64761c6b-46f6-4217-a6f1-457b4de3152f/scratchpad/unseen.png')
# effect on path windows: tiles counted in padded windows that live only in never-seen cells
best=[]
for w in st.path_wins:
    p0,p1,q0,q1=w
    sub=st.gD[q0:q1+1,p0:p1+1]; sv=vis[q0:q1+1,p0:p1+1]
    tot=len(np.unique(sub)); onlyhidden=len(set(np.unique(sub[~sv]))-set(np.unique(sub[sv]))) if (~sv).any() else 0
    best.append((tot,tot-onlyhidden,w))
best.sort(reverse=True)
for t in best[:8]: print("pad window",t[2],"DMG tiles",t[0],"-> if hidden cells were plain",t[1])
print("max after",max(b[1] for b in best))
