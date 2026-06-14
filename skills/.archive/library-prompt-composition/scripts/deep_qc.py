#!/usr/bin/env python3
"""
deep_qc.py — 深度质控脚本
用于批量检测提示词质量，检测所有41条已知冲突模式
Usage:
  python3 deep_qc.py --sample <input_file> <sample_size>
  python3 deep_qc.py --batch <input_file> [--output <out_file>]
  python3 deep_qc.py --audit <input_file> [--report <report_file>]
"""
import json
import random
import re
from collections import Counter

# ============ 41条冲突检测引擎 ============
CONFLICT_PATTERNS = [
    (re.compile(r"站.{0,15}(浴缸|浴池|淋浴|水中|水池)"), "站+水中"),
    (re.compile(r"躺.{0,15}(站|走|行|迈)"), "躺+站"),
    (re.compile(r"(坐|蹲).{0,15}(浸|泡).{0,10}(水|浴缸|浴池)"), "坐+浸"),
    (re.compile(r"双臂.{5,30}(右手|左手)"), "双臂+单手"),
    (re.compile(r"双手.{5,30}(右手|左手)"), "双手+单手"),
    (re.compile(r"(闭.{0,4}眼|眼.{0,4}闭|紧闭).{0,20}(注视|凝视|阅读|看书|翻书|盯着|瞄准|看到|看见|映入|指缝|视线|目光投向|观察|望向|凝望|打量|端详|仰视|俯视)"), "闭眼+看"),
    (re.compile(r"(床上|枕头上|被子里|床单上).{0,15}(站立|站着|直立|站姿)"), "床+站"),
    (re.compile(r"(站|直立|站立).{0,10}(床上|床边|床头|床沿)"), "站立+床"),
    (re.compile(r"卧室.{0,20}(沙滩|海浪|海滩|户外|草地)"), "卧室+户外"),
    (re.compile(r"客厅.{0,20}(浴缸|淋浴|浴池)"), "客厅+浴缸"),
    (re.compile(r"(道路|街道|马路|户外|花园|草地|沙滩|海滩|湖|河|海|山脉|田野|森林).{0,30}(床|枕头|被子|窗帘|床头柜|浴缸|沙发|台灯|茶几|电视)"), "户外+室内家具"),
    (re.compile(r"(床|卧室|客厅|厨房|浴室|办公室|教室).{0,30}(道路|街道|马路|草地|沙滩|海滩|海浪|森林|山脉|湖泊|河流|田野)"), "室内+户外元素"),
    (re.compile(r"(亚裔|亚洲|黄种|东亚).{0,30}(金发|金长发|金色卷发|铂金|亚麻色长发)"), "亚裔+金发"),
    (re.compile(r"(亚裔|亚洲|黄种|东亚).{0,30}(蓝眼|绿眼|蓝色眼睛|绿色眼睛|碧眼|碧色瞳孔)"), "亚裔+异色瞳"),
    (re.compile(r"(男子|男性|男士|男孩|少男|男青年).{0,30}(裙子|连衣裙|旗袍|短裙|吊带裙|长裙|百褶裙|碎花裙|迷你裙|雪纺裙)"), "男+女装"),
    (re.compile(r"(阳光明媚|阳光灿烂|晴空万里|阳光普照|强烈的阳光|明亮的日光).{0,50}(阴天|乌云|灰云|阴沉|雾蒙蒙|雾气弥漫|细雨|暴雨|乌云密布|阴云)"), "晴+阴矛盾"),
    (re.compile(r"(湖泊|山脉|森林|海滩|海浪|田野|草原|沙漠|雪地|河流|大海|山丘|山谷|湖畔|河畔|公园|花园|草地|道路|街道|马路|码头|桥梁).{0,35}(炉火|灶台|壁炉|铁板烧|燃气灶|烤箱|微波炉|铁板|油烟|灶具|炉灶|锅铲|砧板|洗菜池)"), "户外+厨房设施"),
    (re.compile(r"(湖|河|海|山|草|林|沙).{0,15}(铁板烧|燃气灶|灶台|油烟|炉灶)"), "户外+厨房设施短距"),
    (re.compile(r"(裸露|赤裸|一丝不挂|全裸|裸体).{0,40}(遮住|遮掩|覆盖|包裹|穿着|身着|身穿|披着|裹着)"), "裸体+遮挡"),
    (re.compile(r"^(.{0,1})风[，,]"), "风格开篇截断"),
    (re.compile(r"(成年|女子|男子|大人|成年人|女性|男性).{0,15}(婴儿车|摇椅|奶瓶|摇篮)"), "成人+婴儿用品"),
    (re.compile(r"(乳胶|皮革束缚|SM|捆绑|锁链|皮鞭).{0,30}(公园|散步|购物|日常|休闲|婴儿车|摇篮)"), "乳胶+日常矛盾"),
    (re.compile(r"(长发.{0,30}短发|短发.{0,30}长发)"), "发长矛盾"),
    (re.compile(r"(红发|金发|蓝发|绿发|粉发).{0,30}(黑发|深色头发|深色发)"), "发色矛盾"),
    (re.compile(r"(人类|人|她|他|女子|男子).{0,5}(的尾巴|的角|的翅膀)"), "人类+非人特征"),
    (re.compile(r"(男子|男性|男士|男孩).{0,20}(胸部丰满|乳房|乳沟)"), "男性+女性胸部"),
    (re.compile(r"(女子|男子|女性|男性|人).{0,5}((红色|紫色|金色|银色)眼睛|的尾巴|的角|的翅膀|兽耳|的胡须)"), "人类+非人特征"),
    (re.compile(r"(婴儿|幼儿|女婴|男婴|小孩|儿童|孩童|宝宝).{0,20}(比基尼|内衣|蕾丝|丝袜|高跟鞋|丁字裤|性感|瑜伽|下犬式|文胸|胸罩|吊带袜|蕾丝边|口红|浓妆|诱惑|妩媚|乳沟)"), "婴儿+成人化"),
    (re.compile(r"(芭蕾.{0,10}(鞋|舞).{0,20}(靴|运动鞋|皮鞋)|(靴|运动鞋|皮鞋).{0,20}芭蕾.{0,5}(鞋|舞))"), "穿两双鞋"),
    (re.compile(r"(鲜血|血迹|沾满血|流血|伤口|刀伤|枪伤|尸体|血腥|血污|血红)"), "血腥暴力"),
    (re.compile(r"(亚裔|亚洲|黄种|东亚|中国).{0,30}(紫发|绿发|蓝发|粉发|红发|银发|灰发|挑染|渐变发|彩虹发|荧光发)"), "亚裔+非天然发色"),
    (re.compile(r"(亚裔|亚洲|黄种|东亚|中国).{0,30}(紫眼|灰眼|金眼|琥珀眼|红眼|银眼|紫色眼睛|灰色眼睛|金色眼睛|红色眼睛|银色眼睛)"), "亚裔+非天然瞳色"),
    (re.compile(r"(男子|男性|男士|男孩|少男|男青年|男人).{0,30}(头纱|面纱|芭蕾舞鞋|蓬蓬裙|包臀裙|鱼尾裙|吊带袜|雪纺裙|薄纱裙|百褶裙|过膝袜|蕾丝边|泡泡袖|蝴蝶结发饰|水钻|亮片)"), "男+女装补充"),
    (re.compile(r"(办公室|会议室|教室|医院).{0,15}(比基尼|睡衣|晚礼服|泳装|内衣|丁字裤)"), "场景+服装不匹配"),
    (re.compile(r"(山脉|森林|湖泊|大海|海滩|沙漠|田野|草原|山坡|山谷|洞穴|瀑布|溪流|丛林|雪原).{0,40}(床|沙发|浴缸|马桶|灶台|冰箱|电视|茶几|衣柜|书桌|餐桌|淋浴|洗手台|水槽|床头柜)"), "户外+家具强化"),
    (re.compile(r"(木地板|地毯|瓷砖|大理石).{0,30}(草地|沙地|雪地|泥土|沙滩|泥地|湿沙)"), "地板矛盾"),
    (re.compile(r"^.{0,5}[，,。.\\s]风[，,]"), "风格开篇格式异常"),
    (re.compile(r"室内.{0,10}(摄影|设计|风格|环境)风.{50,200}(户外|花园|公园|海滩|森林|街道|山脉|湖泊|大海)"), "室内风+户外内容"),
    (re.compile(r"(猫|狗|熊猫|兔子|熊|鹿|狐狸|狼|老虎|狮子|马|牛|羊).{0,10}(穿.{0,10}(衣|裙|裤|鞋|帽|袜|装)|发型|头发|辫子|马尾|发髻|刘海|表情|微笑|笑容|眼神|化妆)"), "动物拟人未说明"),
    (re.compile(r"(小女孩|小男孩|男孩|儿童|幼儿|宝宝).{0,20}(性感|诱惑|妩媚|撩人|魅惑|挑逗|暴露|裸露|乳沟|勾引)"), "儿童+性感"),
    (re.compile(r"(户外|花园|公园|海滩|森林|草地|山脉|田野).{0,30}(木地板|地毯|瓷砖地板|抛光地板)"), "户外场景+室内地板"),
    (re.compile(r"(婴儿|幼儿|宝宝).{0,10}(比基尼|性感|乳沟|丁字裤)"), "婴儿+性感矛盾"),
]

# 场景群组
SCENE_GROUPS = {
    "卧室": ["床","枕头","床单","被子","卧室","衣柜","梳妆台","床头柜","床头板"],
    "厨房": ["灶台","烤箱","冰箱","微波炉","厨房","水槽","砧板","抽油烟机","厨具"],
    "浴室": ["浴缸","淋浴","马桶","洗手台","水龙头","浴室","花洒","浴帘"],
    "户外自然": ["森林","山脉","湖","海","河","草地","公园","花园","田野","沙漠","雪地","海滩","海岸","悬崖","洞穴"],
    "教室": ["教室","黑板","课桌","讲台","粉笔"],
    "餐厅": ["吧台","酒杯","餐桌","餐厅","餐盘","菜单","酒瓶"],
    "车内": ["汽车","车内","方向盘","引擎盖","驾驶座","后座","车门"],
    "交通工具": ["地铁","火车","车厢","站台","铁轨"],
    "摄影棚": ["影棚","摄影棚","背景布","柔光箱","反光板"],
    "医疗场所": ["医疗","检查室","病床","输液","器械"],
    "办公室": ["办公室","工位","会议室","电脑","打印机"],
    "城市街道": ["街道","马路","人行道","交通灯","路灯"],
}

def qc_one(prompt):
    """单条质检，返回问题列表"""
    issues = []
    cn = sum(1 for c in prompt if "\u4e00"<=c<="\u9fff")

    if cn < 400: issues.append(f"字数不足{cn}")
    if cn > 1000: issues.append(f"字数超标{cn}")

    if not any(k in prompt[:80] for k in ["风，","风,","风。","风格","美学"]):
        issues.append("缺风格开篇")

    # 比喻词
    for kw in ["仿佛","犹如","就像","好似","宛如","如同"]:
        if kw in prompt: issues.append("比喻词"); break
    # 科技词
    for kw in ["量子","夸克","粒子","齿轮","青铜","全息","数据","光纤","纳米","芯片","电路","像素","矩阵"]:
        if kw in prompt: issues.append("科技词"); break

    # 三手
    seen_hands = set()
    for s in prompt.replace("。","。\n").split("\n"):
        if "左手" in s: seen_hands.add("L")
        if "右手" in s: seen_hands.add("R")
        if "双手" in s or "两手" in s or "双臂" in s: seen_hands.add("B")
    if len(seen_hands) >= 3: issues.append("三手")

    # 服装堆叠
    TOP_KW = ["连衣裙","长袍","旗袍","外套","夹克","大衣","上衣","衬衫","T恤","毛衣","背心","吊带","比基尼","卫衣","风衣"]
    tops_found = [t for t in TOP_KW if t in prompt]
    if len(tops_found) >= 3: issues.append("服装堆叠")

    # 裸体+服装
    if ("裸体" in prompt or "赤裸" in prompt) and any(k in prompt for k in ["穿着","身着","身穿","上衣","连衣裙","衬衫","外套","长袍","旗袍"]):
        issues.append("裸体+服装")

    # 41条冲突引擎
    for pat, name in CONFLICT_PATTERNS:
        if pat.search(prompt):
            issues.append(name)

    # 场景3组以上共存
    present_groups = []
    for group, keywords in SCENE_GROUPS.items():
        if any(k in prompt for k in keywords):
            present_groups.append(group)
    if len(present_groups) >= 3:
        issues.append(f"多场景共存:{','.join(present_groups)}")

    return issues

def qc_batch(prompts, sample_size=100):
    """批量质检"""
    if len(prompts) > sample_size:
        sample = random.sample(prompts, sample_size)
    else:
        sample = prompts

    ok = 0; fail = 0; detail = []
    type_counter = Counter()

    for p in sample:
        iss = qc_one(p)
        if iss:
            fail += 1
            for i in iss:
                type_counter[i] += 1
            detail.append((p[:80], iss[:3]))
        else:
            ok += 1

    return {
        "total": len(sample),
        "pass": ok,
        "fail": fail,
        "rate": round(ok/len(sample)*100, 1),
        "type_stats": type_counter.most_common(20),
        "details": detail[:20],
    }

def load_prompts(filepath):
    """从文件加载prompts"""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    # 尝试双换行分割
    prompts = [p.strip() for p in content.split("\n\n") if p.strip()]
    # 如果太少，尝试单行分割
    if len(prompts) < 5:
        prompts = [p.strip() for p in content.split("\n") if p.strip() and len(p.strip()) > 100]
    return prompts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="深度质控")
    parser.add_argument("--sample", nargs=2, metavar=("FILE", "N"),
                        help="从文件中随机抽N条质检")
    parser.add_argument("--batch", metavar="FILE",
                        help="对整个文件执行质检")
    parser.add_argument("--audit", metavar="FILE",
                        help="对整个文件执行审计（每行标记通过/失败）")
    parser.add_argument("--output", metavar="FILE", default=None,
                        help="输出文件")
    parser.add_argument("--report", metavar="FILE", default=None,
                        help="审计报告文件")

    args = parser.parse_args()

    if args.sample:
        fpath, n = args.sample
        n = int(n)
        prompts = load_prompts(fpath)
        if len(prompts) < n:
            print(f"文件只有{len(prompts)}条，全部使用")
            n = len(prompts)
        sample = random.sample(prompts, n)
        result = qc_batch(sample, n)
        print(f"样本量: {result['total']}")
        print(f"通过: {result['pass']} | 失败: {result['fail']} | 合格率: {result['rate']}%")
        print("\n问题统计:")
        for name, cnt in result["type_stats"][:15]:
            print(f"  {name:<25s}: {cnt}次")
        if result["details"]:
            print("\n问题示例(前20):")
            for txt, iss in result["details"][:10]:
                print(f"  ❌ {','.join(iss)}")
                print(f"     {txt[:60]}...")

    elif args.batch:
        prompts = load_prompts(args.batch)
        result = qc_batch(prompts, min(100, len(prompts)))
        print(f"文件: {args.batch} ({len(prompts)}条)")
        print(f"质检抽样: {result['total']}条")
        print(f"通过: {result['pass']} | 失败: {result['fail']} | 合格率: {result['rate']}%")
        print("\n问题统计:")
        for name, cnt in result["type_stats"][:15]:
            print(f"  {name:<25s}: {cnt}次")
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"结果已写入 {args.output}")

    elif args.audit:
        prompts = load_prompts(args.audit)
        passed = []; failed = []
        for p in prompts:
            iss = qc_one(p)
            if iss:
                failed.append((p, iss))
            else:
                passed.append(p)

        report = f"审计报告: {args.audit}\n"
        report += f"总计: {len(prompts)}条\n"
        report += f"通过: {len(passed)}条 ({(len(passed)/len(prompts))*100:.0f}%)\n"
        report += f"失败: {len(failed)}条 ({(len(failed)/len(prompts))*100:.0f}%)"

        print(report)

        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(report + "\n\n")
                if failed:
                    f.write("失败的prompts:\n\n")
                    for p, iss in failed[:50]:
                        f.write(f"  问题: {','.join(iss)}\n")
                        f.write(f"  内容: {p[:100]}...\n\n")
            print(f"报告已写入 {args.report}")

    else:
        parser.print_help()
