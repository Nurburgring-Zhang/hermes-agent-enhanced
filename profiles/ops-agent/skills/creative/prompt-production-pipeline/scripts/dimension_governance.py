#!/usr/bin/env python3
"""
维度库治理脚本
基于500条逐字审核总结的维度库不合理条目过滤规则
治理7个维度: B01/A02/A04/D01/D02/A05/A01
"""
import os

V7_DIR = "/mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7/"
OUT_DIR = "/mnt/d/Hermes/1000000提示词/高质量模板/维度库_api_v7_governed/"
os.makedirs(OUT_DIR, exist_ok=True)

# === B01_场景环境 ===
def govern_B01(lines):
    INDOOR_KW = ["床","沙发","卧室","客厅","厨房","浴室","室内","房间","衣柜","梳妆台","床头柜","餐桌","书桌","台灯","壁灯","吊灯","地毯","窗帘","枕头","被子","床单","浴缸","淋浴","马桶","洗手台"]
    OUTDOOR_KW = ["森林","海滩","山脉","雪地","草地","花园","公园","湖泊","大海","河流","田野","沙漠","山坡","山谷","阳台","天台","露台","街道","马路","户外"]
    kept = []; removed = 0
    for line in lines:
        if len(line) < 10: removed += 1; continue
        hi = sum(1 for k in INDOOR_KW if k in line)
        ho = sum(1 for k in OUTDOOR_KW if k in line)
        if hi and ho:
            kept.append(("indoor" if hi >= ho else "outdoor", line))
        elif hi: kept.append(("indoor", line))
        elif ho: kept.append(("outdoor", line))
        else: kept.append(("unknown", line))
    return kept, removed

# === A02_发型 ===
def govern_A02(lines):
    UNNATURAL = ["金","铂","亚麻","浅棕","浅褐","银白","银发","紫","绿","蓝","粉","红","灰发","挑染","渐变","彩虹","荧光","奶奶灰","雾霾","北极星","脏橘","樱花"]
    nat = []; unat = []; removed = 0
    for line in lines:
        if len(line) < 6: removed += 1; continue
        (unat if any(k in line for k in UNNATURAL) else nat).append(line)
    return nat, unat, removed

# === A04_表情眼神 ===
def govern_A04(lines):
    UNNATURAL = ["蓝眼","绿眼","碧眼","紫眼","灰眼","金眼","琥珀","红眼","银眼","蓝色","绿色","紫色","灰色","金色","红色","银色","碧色"]
    nat = []; unat = []; removed = 0
    for line in lines:
        if len(line) < 6: removed += 1; continue
        (unat if any(k in line for k in UNNATURAL) else nat).append(line)
    return nat, unat, removed

# === D01_服装款式 ===
def govern_D01(lines):
    MALE = ["西装","领带","衬衫","夹克","皮鞋","马甲","西裤","领结","袖扣"]
    FEMALE = ["连衣裙","旗袍","裙子","文胸","比基尼","丝袜","高跟鞋","蕾丝","吊带裙","百褶裙","碎花裙","胸罩","内衣","丁字裤","睡衣","睡裙","吊带袜","连裤袜"]
    m = []; f = []; u = []; removed = 0
    for line in lines:
        if len(line) < 8: removed += 1; continue
        if any(k in line for k in FEMALE): f.append(line)
        elif any(k in line for k in MALE): m.append(line)
        else: u.append(line)
    return m, f, u, removed

# === D02_配饰鞋帽 ===
def govern_D02(lines):
    FEMALE = ["发夹","发簪","蝴蝶结","耳环","头纱","面纱","手链","手镯","项链","珍珠","发带","发箍"]
    MALE = ["领带夹","手表","皮带","帽子","袖扣","胸针","眼镜","墨镜"]
    m = []; f = []; u = []; removed = 0
    for line in lines:
        if len(line) < 6: removed += 1; continue
        if any(k in line for k in FEMALE): f.append(line)
        elif any(k in line for k in MALE): m.append(line)
        else: u.append(line)
    return m, f, u, removed

# === A05_姿势 ===
def govern_A05(lines):
    KW = {"stand":["站","直立","站立","站着","立正","伫立"],
          "sit":["坐","坐姿","坐下","端坐","盘腿","跪坐"],
          "lie":["躺","卧","仰卧","侧卧","俯卧","平躺"],
          "kneel":["跪","跪姿","跪下","单膝跪"],
          "bend":["弯腰","俯身","前倾","后仰","弯曲","侧身"]}
    result = {k:[] for k in list(KW.keys())+["mixed","unknown"]}
    for line in lines:
        if len(line) < 8: continue
        types = [k for k,v in KW.items() if any(x in line for x in v)]
        if not types: result["unknown"].append(line)
        elif len(types) >= 2: result["mixed"].append(line)
        else: result[types[0]].append(line)
    return result

# === A01_年龄性别 ===
def govern_A01(lines):
    MALE_KW = ["男子","男性","男士","男孩","男人","少男","男青年","男生","父亲","爸爸","爷爷","叔叔"]
    FEMALE_KW = ["女子","女性","女士","女孩","女人","少女","女青年","女生","母亲","妈妈","奶奶","阿姨"]
    CHILD_KW = ["儿童","幼儿","婴儿","宝宝","小孩","孩童","女婴","男婴","幼童"]
    NUDE_KW = ["裸体","赤裸","一丝不挂","全裸","裸女","裸男"]
    m=[];f=[];c=[];n=[];u=[]
    for line in lines:
        if any(k in line for k in NUDE_KW): n.append(line)
        elif any(k in line for k in CHILD_KW): c.append(line)
        elif any(k in line for k in MALE_KW): m.append(line)
        elif any(k in line for k in FEMALE_KW): f.append(line)
        else: u.append(line)
    return m,f,c,n,u

# === 主流程 ===
DIMS = {
    "B01_场景环境.txt": govern_B01,
    "A02_发型.txt": govern_A02,
    "A04_表情眼神.txt": govern_A04,
    "D01_服装款式.txt": govern_D01,
    "D02_配饰鞋帽.txt": govern_D02,
    "A05_姿势.txt": govern_A05,
    "A01_年龄性别.txt": govern_A01,
}

TAG_MAP = {
    "B01_场景环境.txt": (["indoor","outdoor","unknown"], "{}"),
    "A02_发型.txt": (["NATURAL","UNNATURAL"], "{}"),
    "A04_表情眼神.txt": (["NATURAL","UNNATURAL"], "{}"),
    "D01_服装款式.txt": (["MALE","FEMALE","UNISEX"], "{}"),
    "D02_配饰鞋帽.txt": (["MALE","FEMALE","UNISEX"], "{}"),
    "A05_姿势.txt": (["stand","sit","lie","kneel","bend","mixed","unknown"], "{}"),
    "A01_年龄性别.txt": (["MALE","FEMALE","CHILD","NUDE","UNKNOWN"], "{}"),
}

print("="*60)
print("  维度库治理")
print("="*60)

for fn, gov in DIMS.items():
    fp = os.path.join(V7_DIR, fn)
    if not os.path.exists(fp): continue
    with open(fp, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    print(f"\n  {fn}: {len(lines):,}条")

    result = gov(lines)

    if fn == "B01_场景环境.txt":
        kept, removed = result
        for t in ["indoor","outdoor","unknown"]:
            cnt = sum(1 for x,_ in kept if x==t)
            print(f"    {t}: {cnt:,}")
        print(f"    碎片删除: {removed}")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
            f.writelines(f"[{tag}] {line}\n" for tag, line in kept)

    elif fn == "A02_发型.txt" or fn == "A04_表情眼神.txt":
        nat, unat, removed = result
        print(f"    NATURAL: {len(nat):,}  UNNATURAL: {len(unat):,}  删除: {removed}")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
            f.writelines(f"[NATURAL] {l}\n" for l in nat)
            f.writelines(f"[UNNATURAL] {l}\n" for l in unat)

    elif fn == "D01_服装款式.txt" or fn == "D02_配饰鞋帽.txt":
        m,f,u,removed = result
        print(f"    MALE:{len(m):,} FEMALE:{len(f):,} UNISEX:{len(u):,} 删除:{removed}")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
            f.writelines(f"[MALE] {l}\n" for l in m)
            f.writelines(f"[FEMALE] {l}\n" for l in f)
            f.writelines(f"[UNISEX] {l}\n" for l in u)

    elif fn == "A05_姿势.txt":
        pts = result
        for k,v in pts.items(): print(f"    {k}: {len(v):,}")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
            for pt in ["stand","sit","lie","kneel","bend"]:
                f.writelines(f"[{pt}] {l}\n" for l in pts[pt])
            f.writelines(f"[MIXED] {l}\n" for l in pts["mixed"])
            f.writelines(f"[UNKNOWN] {l}\n" for l in pts["unknown"])

    elif fn == "A01_年龄性别.txt":
        m,f,c,n,u = result
        print(f"    MALE:{len(m):,} FEMALE:{len(f):,} CHILD:{len(c):,} NUDE:{len(n):,} UNKNOWN:{len(u):,}")
        with open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8") as f:
            f.writelines(f"[MALE] {l}\n" for l in m)
            f.writelines(f"[FEMALE] {l}\n" for l in f)
            f.writelines(f"[CHILD] {l}\n" for l in c)
            f.writelines(f"[NUDE] {l}\n" for l in n)
            f.writelines(f"[UNKNOWN] {l}\n" for l in u)

print(f"\n  输出: {OUT_DIR}")
