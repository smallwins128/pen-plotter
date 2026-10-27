"""2D SIMP topology optimisation of the tip hanger's front profile (y-z plane), after Andreassen et al. top88.
import pathlib, os; OUT = str(pathlib.Path(__file__).resolve().parents[3] / "out" / "beacon"); os.makedirs(OUT, exist_ok=True)
Domain 126 x 54 mm at 1 mm elements. Pins at the two pivot holes; loads at the crossbar bolt pads.
Two load cases: batten weight (down) and a sideways knock along the batten (30% of weight)."""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
NX, NZ = 126, 54                     # elements along y (x-index) and z (rows, top row = z +10)
Y0, ZT = -63.0, 10.0
vol, penal, rmin = 0.30, 3.0, 2.5
def yc(i): return Y0 + i + 0.5
def zc(j): return ZT - j - 0.5
E0, Emin, nu = 1.0, 1e-9, 0.3
A11=np.array([[12,3,-6,-3],[3,12,3,0],[-6,3,12,-3],[-3,0,-3,12]]);A12=np.array([[-6,-3,0,3],[-3,-6,-3,-6],[0,-3,-6,3],[3,-6,3,-6]])
B11=np.array([[-4,3,-2,9],[3,-4,-9,4],[-2,-9,-4,-3],[9,4,-3,-4]]);B12=np.array([[2,-3,4,-9],[-3,2,9,-2],[4,9,2,3],[-9,-2,3,2]])
KE=1/(1-nu**2)/24*(np.block([[A11,A12],[A12.T,A11]])+nu*np.block([[B11,B12],[B12.T,B11]]))
nodenrs=np.arange((NX+1)*(NZ+1)).reshape(NX+1,NZ+1).T   # node (row j, col i)
edofv=(2*nodenrs[:-1,:-1]+2).reshape(-1,order='F')
# element ordering: column-major over (j,i) like top88
ii=np.repeat(np.arange(NX),NZ); jj=np.tile(np.arange(NZ),NX)
edof=np.zeros((NX*NZ,8),int)
for e,(i,j) in enumerate(zip(ii,jj)):
    n1=nodenrs[j+1,i]; n2=nodenrs[j+1,i+1]; n3=nodenrs[j,i+1]; n4=nodenrs[j,i]
    edof[e]=[2*n1,2*n1+1,2*n2,2*n2+1,2*n3,2*n3+1,2*n4,2*n4+1]
iK=np.kron(edof,np.ones((8,1),int)).ref if False else np.kron(edof,np.ones((8,1))).flatten().astype(int)
jK=np.kron(edof,np.ones((1,8))).flatten().astype(int)
Y=yc(ii); Z=zc(jj)
# regions
pivots=[(-58.0,0.0),(58.0,0.0)]
dpiv=np.min([np.hypot(Y-py,Z-pz) for py,pz in pivots],axis=0)
void=np.zeros(NX*NZ,bool); solid=np.zeros(NX*NZ,bool)
void|=(np.abs(Y)<53)&(Z>-20)            # rails, their swing, and the cable stay clear
void|=(np.abs(Y)>=53)&(Z>0)&(dpiv>10)   # tab tops stay round around the pivot
void|=dpiv<2.2                          # pivot holes
solid|=(dpiv>=2.2)&(dpiv<6.5)           # bearing ring around each pivot hole (nut pocket seat)
pads=[(-50.0,-44.0),(50.0,-44.0)]
for py,pz in pads: solid|=(np.abs(Y-py)<7)&(Z<-35)   # crossbar bolt bosses: full base depth
solid&=~void
ndof=2*(NX+1)*(NZ+1)
# supports: nodes on pivot hole edge (r<=3) fixed
NYn=np.arange(NX+1)+Y0; NZn=ZT-np.arange(NZ+1)
fixed=[]
for py,pz in pivots:
    for i in range(NX+1):
        for j in range(NZ+1):
            if np.hypot(NYn[i]-py,NZn[j]-pz)<=3.0: n=nodenrs[j,i]; fixed+=[2*n,2*n+1]
fixed=np.unique(fixed); free=np.setdiff1d(np.arange(ndof),fixed)
F=np.zeros((ndof,2))
for py,pz in pads:
    for i in range(NX+1):
        if abs(NYn[i]-py)<=4: n=nodenrs[NZ,i]; F[2*n+1,0]-=1.0; F[2*n,1]+=0.3
# filter
iH=[];jH=[];sH=[]
for e in range(NX*NZ):
    i,j=ii[e],jj[e]
    for k in range(max(i-3,0),min(i+4,NX)):
        for l in range(max(j-3,0),min(j+4,NZ)):
            f=k*NZ+l; w=max(0,rmin-np.hypot(i-k,j-l))
            if w>0: iH.append(e);jH.append(f);sH.append(w)
H=sp.coo_matrix((sH,(iH,jH)),shape=(NX*NZ,NX*NZ)).tocsc(); Hs=np.array(H.sum(1)).ravel()
active=~(void|solid)
x=np.where(solid,1.0,np.where(void,0.0,vol)); xPhys=x.copy()
for it in range(120):
    sK=((KE.ravel()[np.newaxis]).T*(Emin+xPhys**penal*(E0-Emin))).flatten(order='F')
    K=sp.coo_matrix((sK,(iK,jK)),shape=(ndof,ndof)).tocsc(); K=(K+K.T)/2
    U=np.zeros((ndof,2)); U[free,:]=spl.spsolve(K[free][:,free],F[free,:]).reshape(-1,2)
    dc=np.zeros(NX*NZ); c=0
    for lc in range(2):
        ce=(np.dot(U[edof,lc],KE)*U[edof,lc]).sum(1)
        c+=((Emin+xPhys**penal*(E0-Emin))*ce).sum(); dc+=-penal*xPhys**(penal-1)*(E0-Emin)*ce
    dv=np.ones(NX*NZ)
    dc=np.asarray(H*(dc[:,None]/Hs[:,None])).ravel(); dv=np.asarray(H*(dv[:,None]/Hs[:,None])).ravel()
    l1,l2,move=0,1e9,0.2; target=vol*active.sum()+solid.sum()
    while (l2-l1)/(l1+l2)>1e-3:
        lmid=0.5*(l2+l1)
        xn=np.maximum(0,np.maximum(x-move,np.minimum(1,np.minimum(x+move,x*np.sqrt(np.maximum(-dc,1e-30)/dv/lmid)))))
        xn[solid]=1; xn[void]=0
        xp=np.asarray(H*xn[:,None]).ravel()/Hs; xp[solid]=1; xp[void]=0
        if xp.sum()>target: l1=lmid
        else: l2=lmid
    change=np.abs(xn-x).max(); x=xn; xPhys=xp
    if it%20==0: print(it,round(c,3),round(change,3))
    if change<0.01 and it>30: break
print('final',it,round(c,3))
np.save(OUT+'/tip_x.npy',xPhys.reshape(NX,NZ).T)
img=xPhys.reshape(NX,NZ).T
plt.figure(figsize=(9,4.2));plt.imshow(1-img,cmap='gray',extent=[Y0,Y0+NX,ZT-NZ,ZT],vmin=0,vmax=1)
plt.title('Tip hanger front profile: SIMP result (black = keep)');plt.xlabel('y along batten (mm)');plt.ylabel('z (mm)')
plt.savefig(OUT+'/tip_topo.png',dpi=110,bbox_inches='tight')
