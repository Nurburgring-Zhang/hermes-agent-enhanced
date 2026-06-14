#!/usr/bin/env python3
"""
VDrift IDP2 → Three.js JSON v13
基于model_joe03.cpp源码精确还原
格式: [Header 20B] [Faces n×18B] [nverts 4B] [ntex 4B] [verts nverts×12B] [norms num_norms×12B] [tex ntex×8B]
"""
import json
import os
import struct

ENDIAN = "<"

def parse(filepath):
    with open(filepath, "rb") as f:
        raw = f.read()

    num_faces = struct.unpack_from(ENDIAN + "I", raw, 8)[0]
    num_frames = struct.unpack_from(ENDIAN + "I", raw, 12)[0]

    pos = 20
    face_vi, face_ni, face_ti = [], [], []
    for fi in range(num_faces):
        v0 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        v1 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        v2 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        n0 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        n1 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        n2 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        t0 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        t1 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        t2 = struct.unpack_from(ENDIAN + "H", raw, pos)[0]; pos+=2
        face_vi.append((v0,v1,v2))
        face_ni.append((n0,n1,n2))
        face_ti.append((t0,t1,t2))

    nverts = struct.unpack_from(ENDIAN + "I", raw, pos)[0]; pos+=4
    ntex = struct.unpack_from(ENDIAN + "I", raw, pos)[0]; pos+=4

    verts = []
    for i in range(nverts):
        x = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        y = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        z = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        verts.append((x,y,z))

    remaining = len(raw) - pos
    max_ni = 0
    for n in face_ni:
        max_ni = max(max_ni, n[0], n[1], n[2])

    # Try guesses for num_normals, pick first that fits
    n_norm = max_ni + 1
    for guess in [max_ni+1, max_ni+2, nverts, ntex, remaining//12]:
        if 0 < guess <= remaining // 12:
            n_norm = guess
            break

    norms = []
    for i in range(n_norm):
        nx = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        ny = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        nz = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        norms.append((nx,ny,nz))

    uvs = []
    for i in range(min(ntex, (len(raw) - pos)//8)):
        u = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        v = struct.unpack_from(ENDIAN + "f", raw, pos)[0]; pos+=4
        uvs.append((u, v))
    while len(uvs) < ntex:
        uvs.append((0,0))

    # Dedup: (vi,ni,ti) -> unique vertex
    out_verts, out_norms, out_uvs, out_indices = [], [], [], []
    vmap = {}
    skipped = 0

    for fi in range(num_faces):
        v0,v1,v2 = face_vi[fi]
        n0,n1,n2 = face_ni[fi]
        t0,t1,t2 = face_ti[fi]

        if v0 >= nverts or v1 >= nverts or v2 >= nverts:
            skipped += 1; continue
        if n0 >= n_norm or n1 >= n_norm or n2 >= n_norm:
            skipped += 1; continue

        for j in range(3):
            vi = [v0,v1,v2][j]
            ni = [n0,n1,n2][j]
            ti = [t0,t1,t2][j]
            key = (vi, ni, ti)
            if key not in vmap:
                vmap[key] = len(out_verts) // 3  # ← CRITICAL: divide by 3!
                out_verts.extend(verts[vi])
                out_norms.extend(norms[ni])
                t = uvs[ti] if ti < len(uvs) else (0,0)
                out_uvs.extend([t[0], 1-t[1]])
            out_indices.append(vmap[key])

    return {
        "verts": out_verts, "normals": out_norms, "uvs": out_uvs,
        "indices": out_indices,
        "numVerts": len(out_verts)//3, "numTris": len(out_indices)//3,
    }


def convert(model_id, cars_dir, out_dir):
    cd = os.path.join(cars_dir, model_id)
    bf = os.path.join(cd, "body.joe")
    if not os.path.isfile(bf):
        return False

    d = parse(bf)
    if d["numVerts"] == 0:
        print(f"  FAIL {model_id}: no verts")
        return False

    out = {
        "name": model_id,
        "verts": d["verts"], "normals": d["normals"],
        "uvs": d["uvs"], "indices": d["indices"],
        "parts": {"body": {"vertOffset":0,"vertCount":d["numVerts"],"triCount":d["numTris"],"indexCount":len(d["indices"])}},
        "numVerts": d["numVerts"], "numTris": d["numTris"]
    }

    op = os.path.join(out_dir, f"{model_id}.json")
    with open(op, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    print(f"  OK {model_id}: {d['numVerts']}v {d['numTris']}t")
    return True


def main():
    cd = "/tmp/vdrift/data/cars"
    od = "/mnt/d/minimax/racing game package/plush_racing_game/dist/models"
    os.makedirs(od, exist_ok=True)
    cars = ["350Z", "360", "ATT", "CO", "CS", "F1-02", "LE", "M3", "M7", "SV", "TC6", "TL2", "XS"]
    ok = sum(1 for c in cars if convert(c, cd, od))
    print(f"\nDone: {ok}/{len(cars)}")


if __name__ == "__main__":
    main()
