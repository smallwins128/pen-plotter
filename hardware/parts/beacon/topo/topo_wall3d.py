"""Coarse 3D SIMP topology run for the Beacon wall plate (3 mm voxels), after Liu & Tovar's top3d.

Frame: x out from the wall (wall face x = 0), y along the wall, z up (upper pivot z = 0, lower pivot z = -120).
Supports: the two wall screws hold everything near their holes; the back face below z = -90 bears on the wall
(the rails push the lower ears into it), so it is held in x only. The top half is free to lift: the ties pull it.
Loads (whole arm about 0.55 kg at about 0.4 m, estimate): ties pull each upper ear out (+x 9 N) and down (1.4 N);
rails push each lower ear in (-x 9 N) and down (1.4 N). Case 2: a sideways knock at the batten, 30% of the weight.
Passive solid: the ears and a ring round each screw. Kept clear: screw-driver access, the rails' swing, nut access.
"""
import time, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
from itertools import product
import pathlib, os
OUT = str(pathlib.Path(__file__).resolve().parents[3] / "out" / "beacon"); os.makedirs(OUT, exist_ok=True)

H = 3.0
X0, X1, Y0, Y1, Z0, Z1 = 0.0, 24.0, -52.5, 52.5, -145.0, 20.0
NX, NY, NZ = int((X1 - X0) / H), int((Y1 - Y0) / H), int((Z1 - Z0) / H)
VOL, PENAL, RMIN = 0.22, 3.0, 1.6           # volume fraction of the free region; filter radius in elements
NU = 0.35


def ke_h8(nu):
    """8-node brick stiffness for unit E and unit cube, 2x2x2 Gauss."""
    D = 1 / ((1 + nu) * (1 - 2 * nu)) * np.array([
        [1 - nu, nu, nu, 0, 0, 0], [nu, 1 - nu, nu, 0, 0, 0], [nu, nu, 1 - nu, 0, 0, 0],
        [0, 0, 0, (1 - 2 * nu) / 2, 0, 0], [0, 0, 0, 0, (1 - 2 * nu) / 2, 0], [0, 0, 0, 0, 0, (1 - 2 * nu) / 2]])
    corners = np.array(list(product((0, 1), repeat=3)))       # node order: (i, j, k) bits
    K = np.zeros((24, 24)); g = 0.5 / np.sqrt(3)
    for q in product((0.5 - g, 0.5 + g), repeat=3):
        dN = np.zeros((8, 3))
        for a, (i, j, k) in enumerate(corners):
            fx = (q[0] if i else 1 - q[0]); fy = (q[1] if j else 1 - q[1]); fz = (q[2] if k else 1 - q[2])
            dN[a] = [(1 if i else -1) * fy * fz, (1 if j else -1) * fx * fz, (1 if k else -1) * fx * fy]
        B = np.zeros((6, 24))
        for a in range(8):
            B[0, 3*a] = dN[a, 0]; B[1, 3*a+1] = dN[a, 1]; B[2, 3*a+2] = dN[a, 2]
            B[3, 3*a] = dN[a, 1]; B[3, 3*a+1] = dN[a, 0]
            B[4, 3*a+1] = dN[a, 2]; B[4, 3*a+2] = dN[a, 1]
            B[5, 3*a] = dN[a, 2]; B[5, 3*a+2] = dN[a, 0]
        K += B.T @ D @ B / 8
    return K, corners


def main():
    t0 = time.time()
    KE, corners = ke_h8(NU)
    KE = KE * H                                              # scale: unit cube -> H mm brick (stiffness ~ E*H)
    nid = lambda i, j, k: (i * (NY + 1) + j) * (NZ + 1) + k
    I, J, Kk = np.meshgrid(np.arange(NX), np.arange(NY), np.arange(NZ), indexing="ij")
    I, J, Kk = I.ravel(), J.ravel(), Kk.ravel()
    ne = I.size
    edof = np.zeros((ne, 24), int)
    for a, (di, dj, dk) in enumerate(corners):
        n = nid(I + di, J + dj, Kk + dk)
        edof[:, 3*a:3*a+3] = np.stack([3*n, 3*n+1, 3*n+2], 1)
    ndof = 3 * (NX + 1) * (NY + 1) * (NZ + 1)
    iK = np.repeat(edof, 24, 1).ravel(); jK = np.tile(edof, (1, 24)).ravel()
    xc, yc, zc = X0 + (I + .5) * H, Y0 + (J + .5) * H, Z0 + (Kk + .5) * H

    # passive regions
    solid = np.zeros(ne, bool); void = np.zeros(ne, bool)
    def ear(zcen, slot, y_in, y_out):
        ay = np.abs(yc)
        inside_y = (ay >= y_in) & (ay <= y_out)
        dz = np.clip(np.abs(zc - zcen) - slot, 0, None)
        tip = np.hypot(xc - 22.0, dz) <= 10.0
        root = (xc <= 22.0) & (np.abs(zc - zcen) <= slot + 18 - (xc - 8) * (8.0 / 14))
        return inside_y & (xc >= 8) & (tip | root)
    upper = ear(0.0, 0.0, 42.0, 52.0); lower = ear(-120.0, 5.0, 34.5, 44.5)
    solid |= upper | lower
    for zs in (0.0, -120.0):
        r = np.hypot(yc, zc - zs)
        solid |= (xc < 8) & (r < 9.0) & (r > 2.5)            # screw boss ring
        void |= (xc < 8) & (r <= 2.5)                         # screw hole
        void |= (xc >= 8) & (r < 8.0)                         # driver and head access
    for zcen, yin in ((0.0, 42.0), (-120.0, 34.5)):
        void |= (xc >= 8) & (np.abs(yc) < yin) & (np.abs(zc - zcen) < 14)   # nut and spanner access
    void |= (xc >= 8) & (np.abs(yc) > 44.5) & (zc > -140) & (zc < -98)      # rails swing past the lower ears
    void &= ~solid
    free = ~(solid | void)

    # supports
    fixed = []
    for i, j, k in product(range(NX + 1), range(NY + 1), range(NZ + 1)):
        x, y, z = X0 + i * H, Y0 + j * H, Z0 + k * H
        n = nid(i, j, k)
        if i == 0 and min(np.hypot(y, z), np.hypot(y, z + 120)) <= 7.5:
            fixed += [3*n, 3*n+1, 3*n+2]
        elif i == 0 and z <= -90:
            fixed += [3*n]
    fixed = np.unique(fixed); freedofs = np.setdiff1d(np.arange(ndof), fixed)

    # loads at the pivot nodes (x = 21, nearest grid plane) inside each ear
    F = np.zeros((ndof, 2))
    def load(zcen, y_in, y_out, f, lc):
        sel = [nid(7, j, k) for j in range(NY + 1) for k in range(NZ + 1)
               if y_in <= abs(Y0 + j * H) <= y_out and abs(Z0 + k * H - zcen) <= 6]
        for s in (-1, 1):
            ss = [n for n in sel if np.sign(Y0 + (n // (NZ + 1)) % (NY + 1) * H) == s]
            fx, fy, fz = f(s)
            for n in ss:
                F[3*n, lc] += fx / len(ss); F[3*n+1, lc] += fy / len(ss); F[3*n+2, lc] += fz / len(ss)
    load(0.0, 42.0, 52.0, lambda s: (9.0, 0.0, -1.4), 0)
    load(-120.0, 34.5, 44.5, lambda s: (-9.0, 0.0, -1.4), 0)
    load(0.0, 42.0, 52.0, lambda s: (1.6 * s, 0.4, 0.0), 1)       # knock: yaw couple + sideways shear
    load(-120.0, 34.5, 44.5, lambda s: (1.6 * s, 0.4, 0.0), 1)

    # density filter
    rows, cols, vals = [], [], []
    R = int(np.ceil(RMIN))
    idx = lambda i, j, k: (i * NY + j) * NZ + k
    for e in range(ne):
        i, j, k = I[e], J[e], Kk[e]
        for a in range(max(i - R, 0), min(i + R + 1, NX)):
            for b in range(max(j - R, 0), min(j + R + 1, NY)):
                for c in range(max(k - R, 0), min(k + R + 1, NZ)):
                    w = RMIN - np.sqrt((i - a) ** 2 + (j - b) ** 2 + (k - c) ** 2)
                    if w > 0: rows.append(e); cols.append(idx(a, b, c)); vals.append(w)
    Hf = sp.csr_matrix((vals, (rows, cols)), shape=(ne, ne)); Hs = np.asarray(Hf.sum(1)).ravel()

    x = np.where(solid, 1.0, np.where(void, 0.0, VOL)); xp = x.copy()
    target = VOL * free.sum() + solid.sum()
    print(f"grid {NX}x{NY}x{NZ}, {ne} elements, {ndof} dofs, setup {time.time()-t0:.0f}s", flush=True)
    for it in range(60):
        E = 1e-9 + xp ** PENAL * (1 - 1e-9)
        Kg = sp.csc_matrix((np.outer(E, KE.ravel()).ravel(), (iK, jK)), shape=(ndof, ndof))
        lu = spl.splu(Kg[freedofs][:, freedofs].tocsc())
        U = np.zeros_like(F); U[freedofs] = lu.solve(F[freedofs])
        c = 0; dc = np.zeros(ne)
        for lc in (0, 1):
            ue = U[edof, lc]; ce = np.einsum("ij,jk,ik->i", ue, KE, ue)
            c += (E * ce).sum(); dc += -PENAL * xp ** (PENAL - 1) * ce
        dc = Hf @ (dc / Hs); dv = Hf @ (np.ones(ne) / Hs)
        l1, l2 = 0.0, 1e12
        while (l2 - l1) / (l1 + l2 + 1e-30) > 1e-4:
            lm = 0.5 * (l1 + l2)
            xn = np.clip(x * np.sqrt(np.maximum(-dc, 1e-30) / dv / lm), np.maximum(0, x - 0.2), np.minimum(1, x + 0.2))
            xn[solid] = 1; xn[void] = 0
            xq = (Hf @ xn) / Hs; xq[solid] = 1; xq[void] = 0
            if xq.sum() > target: l1 = lm
            else: l2 = lm
        change = np.abs(xn - x).max(); x, xp = xn, xq
        print(f"it {it:2d}  c {c:.4g}  change {change:.3f}  {time.time()-t0:.0f}s", flush=True)
        np.save(OUT + "/wall_x.npy", xp.reshape(NX, NY, NZ))
        if change < 0.01 and it > 25: break
    np.savez(OUT + "/wall_meta.npz", solid=solid.reshape(NX, NY, NZ), void=void.reshape(NX, NY, NZ), H=H, X0=X0, Y0=Y0, Z0=Z0)
    print("done", flush=True)


if __name__ == "__main__":
    main()
