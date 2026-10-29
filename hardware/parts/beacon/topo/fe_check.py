"""Plane-stress check of the v3 front profile: real units (N, mm, MPa). PLA E ~ 3500 MPa (typical, not measured)."""
import sys, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
import pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import beacon_tip_hanger_organic as T
from shapely.geometry import Point
from shapely.prepared import prep
h=0.5; Y0,Y1,Z0,Z1=-64,64,-45,12
NX,NZ=int((Y1-Y0)/h),int((Z1-Z0)/h)
prof=prep(T.front_profile()); t=T.DEPTH; E,nu=3500.0,0.35
ii=np.repeat(np.arange(NX),NZ); jj=np.tile(np.arange(NZ),NX)
yc=Y0+(ii+.5)*h; zc=Z1-(jj+.5)*h
holes=[(-58,0),(58,0)]
dens=np.array([prof.contains(Point(a,b)) and min(np.hypot(a-p,b-q) for p,q in holes)>2.2 for a,b in zip(yc,zc)])
A11=np.array([[12,3,-6,-3],[3,12,3,0],[-6,3,12,-3],[-3,0,-3,12]]);A12=np.array([[-6,-3,0,3],[-3,-6,-3,-6],[0,-3,-6,3],[3,-6,3,-6]])
B11=np.array([[-4,3,-2,9],[3,-4,-9,4],[-2,-9,-4,-3],[9,4,-3,-4]]);B12=np.array([[2,-3,4,-9],[-3,2,9,-2],[4,9,2,3],[-9,-2,3,2]])
KE=t/(1-nu**2)/24*(np.block([[A11,A12],[A12.T,A11]])+nu*np.block([[B11,B12],[B12.T,B11]]))  # x E per element
nodes=np.arange((NX+1)*(NZ+1)).reshape(NX+1,NZ+1).T
n1=nodes[jj+1,ii];n2=nodes[jj+1,ii+1];n3=nodes[jj,ii+1];n4=nodes[jj,ii]
edof=np.stack([2*n1,2*n1+1,2*n2,2*n2+1,2*n3,2*n3+1,2*n4,2*n4+1],1)
Ee=np.where(dens,E,E*1e-9)
iK=np.repeat(edof,8,1).ravel(); jK=np.tile(edof,(1,8)).ravel()
K=sp.coo_matrix(((KE.ravel()[None]*Ee[:,None]).ravel(),(iK,jK)),shape=(2*nodes.size,)*2).tocsc()
NYn=Y0+np.arange(NX+1)*h; NZn=Z1-np.arange(NZ+1)*h
fixed=[]
for p,q in holes:
    m=np.hypot(NYn[None,:]-p,NZn[:,None]-q)<=2.6
    for n in nodes[m]: fixed+=[2*n,2*n+1]
fixed=np.unique(fixed); free=np.setdiff1d(np.arange(2*nodes.size),fixed)
W=0.43*9.81/2                                   # per crossbar bolt: batten 400 g + crossbar ~30 g (estimate)
F=np.zeros((2*nodes.size,2))
for p in (-50,50):
    sel=np.where(np.abs(NYn-p)<=4)[0]
    for i in sel: n=nodes[NZ-2,i]; F[2*n+1,0]-=W/len(sel); F[2*n,1]+=0.3*W/len(sel)
U=np.zeros_like(F); U[free]=spl.spsolve(K[free][:,free],F[free]).reshape(-1,2)
Bc=np.array([[-1,0,1,0,1,0,-1,0],[0,-1,0,-1,0,1,0,1],[-1,-1,-1,1,1,1,1,-1]])/(2*h)
D=E/(1-nu**2)*np.array([[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]])
for lc,name in enumerate(['weight','sideways knock (30%)']):
    s=(D@(Bc@U[edof,lc].T)).T; vm=np.sqrt(s[:,0]**2-s[:,0]*s[:,1]+s[:,1]**2+3*s[:,2]**2); vm[~dens]=0
    dz=np.abs(U[2*nodes[NZ-2,np.abs(NYn-50).argmin()]+1,lc]); dy=np.abs(U[2*nodes[NZ-2,np.abs(NYn-50).argmin()],lc])
    print(f'{name}: max von Mises {vm.max():.2f} MPa at y={yc[vm.argmax()]:.1f} z={zc[vm.argmax()]:.1f}; bolt-pad deflection {max(dz,dy)*1000:.1f} um')
print('elements',dens.sum())
