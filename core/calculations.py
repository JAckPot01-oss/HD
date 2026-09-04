from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, sqrt
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class JFYM150Input:
    project_name: str = "示例项目"
    position_name: str = "外墙1号机位"
    spacing_large_mm: float = 4700
    spacing_small_mm: float = 0
    cantilever_mm: float = 3050
    floor_height_mm: float = 4500
    template_height_mm: float = 4500
    opening_height_mm: float = 0
    opening_width_mm: float = 0
    cantilever_template_mm: float = 1600
    upper_support_height_mm: float = 650
    wall_bracket_drop_mm: float = 900
    ladder_share_count: float = 6
    gust_factor: float = 1.59
    height_factor: float = 2.03
    template_retraction_mm: float = 1000
    wall_thickness_mm: float = 400
    template_weight_kg_m2: float = 55
    shield_factor: float = 0.78
    top_live_load_kn_m2: float = 5
    lower_live_load_kn_m2: float = 1
    gamma_g_construction: float = 1.2
    gamma_g_other: float = 1.35
    gamma_q: float = 1.4
    combination_factor: float = 0.9
    moment_factor: float = 1.2
    bolt_count: int = 2
    bolt_effective_area_mm2: float = 817
    bolt_tension_design_mpa: float = 400
    bolt_shear_design_mpa: float = 250
    concrete_tension_mpa: float = 0.91
    concrete_compression_mpa: float = 7.2


def _r(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def calculate_jfym150(p: JFYM150Input) -> dict[str, Any]:
    """复现 JFYM150B1-B2 基准Excel的确定性计算链。"""
    if p.floor_height_mm <= 0 or p.ladder_share_count <= 0 or p.bolt_count <= 0:
        raise ValueError("层高、梯子分担机位数和螺栓数量必须大于0。")

    platform_len = (p.spacing_large_mm / 2 + p.spacing_small_mm / 2 + p.cantilever_mm) / 1000
    template_h = p.template_height_mm / 1000
    template_len = (p.spacing_large_mm / 2 + p.spacing_small_mm / 2 + p.cantilever_template_mm) / 1000
    opening_h = p.opening_height_mm / 1000
    opening_len = p.opening_width_mm / 1000
    net_height = (330 + p.upper_support_height_mm + 9450 - p.template_height_mm - p.wall_bracket_drop_mm + 60) / 1000
    net_width = platform_len

    beam_weights = dict(upper=164.104, construction=111.716, operation=61.539, hanger=41.026)
    net_beam_kg_m = 90.0
    net_kg_m = 357.0
    ladder_total_kg = 845.96
    widths = dict(upper=2.525, third=1.44, construction=2.525, operation=2.725, hanger=1.455)
    platform_kg_m2 = 35.0

    weight_kg = {
        "架体": 2914.65,
        "平台梁": sum(beam_weights.values()) * platform_len,
        "附墙装置": 113.77,
        "机位分担斜梯": ladder_total_kg / p.ladder_share_count,
        "护网托梁": net_beam_kg_m * platform_len,
        "护网": net_kg_m * net_width,
        "平台": (widths["upper"] * 2 + widths["third"] + widths["construction"] + widths["operation"] + widths["hanger"]) * platform_len * platform_kg_m2,
        "模板": (template_h * template_len - opening_h * opening_len / 2) * p.template_weight_kg_m2,
    }
    weight_kn = {k: v * 10 / 1000 for k, v in weight_kg.items()}
    self_weight = sum(weight_kn.values())

    top_live = 2.25 * platform_len * p.top_live_load_kn_m2
    lower_live = 2.5 * platform_len * p.lower_live_load_kn_m2
    wind_pressure_7_shield = p.gust_factor * p.shield_factor * p.height_factor * (17.1**2 / 1600)
    wind_pressure_7_full = p.gust_factor * p.height_factor * (17.1**2 / 1600)
    wind_pressure_9 = p.gust_factor * p.shield_factor * p.height_factor * (24.4**2 / 1600)
    wind_construction = wind_pressure_7_shield * net_height * net_width
    wind_climbing = (
        wind_pressure_7_shield * (net_height * net_width + opening_h * opening_len / 2)
        + (template_h * template_len - opening_h * opening_len / 2) * wind_pressure_7_full
    )
    wind_shutdown = wind_pressure_9 * net_height * net_width

    shear_total = {
        "施工工况": p.gamma_g_construction * self_weight + p.gamma_q * top_live,
        "爬升工况": p.gamma_g_other * self_weight + p.gamma_q * lower_live,
        "停工工况": p.gamma_g_other * self_weight,
    }

    moments = []
    def add(name: str, force: float, arm: float) -> None:
        moments.append({"项目": name, "重量或作用力(kN)": force, "力臂(m)": arm, "力矩(kN·m)": force * arm})

    add("上架体", 7.9, 2.0)
    add("上架体上层及中层平台梁", beam_weights["upper"] / 8 * 6 * platform_len / 100, 1.57)
    add("上架体底层平台梁", beam_weights["upper"] / 8 * 2 * platform_len / 100, 2.045)
    add("上架体支座", 0.00134 * p.upper_support_height_mm, 2.045)
    add("上架体上层及中间层平台", 2 * platform_kg_m2 * widths["upper"] * platform_len / 100, 1.59)
    add("上架体底层平台", platform_kg_m2 * widths["third"] * platform_len / 100, 2.045)
    add("模板支架", 1.2, 0.246)
    add("滑座", 0.92, 1.0)
    add("移动小车主梁", 1.25, 1.5)
    add("模板调节支腿", 0.432, 0.95)
    add("大平台（两层）", platform_kg_m2 * (widths["construction"] + widths["operation"]) * platform_len / 100, 1.5)
    add("大平台梁（两层）", (beam_weights["construction"] + beam_weights["operation"]) * platform_len / 100, 1.77)
    add("下架体", 7.41, 1.42)
    add("爬升箱及液压系统", 1.93, 0.495)
    add("附墙装置", 1.14, 0.11)
    add("挂架及挂架平台梁", (67.35 + beam_weights["hanger"] * platform_len) / 100, 1.095)
    add("挂架平台", platform_kg_m2 * widths["hanger"] * platform_len / 100, 0.83)
    add("上下架体托梁及护网", net_kg_m / 16 * 14 * platform_len / 100 + weight_kn["护网托梁"], 2.825)
    add("挂架护网", net_kg_m / 16 * 2 * platform_len / 100, 1.6)
    add("导轨", 6.78, 0.285)
    add("上层及中间层斜梯", 294.46 / p.ladder_share_count / 100, 2.15)
    add("底层及大平台斜梯", 394.26 / p.ladder_share_count / 100, 2.048)
    add("挂架斜梯", 157.24 / p.ladder_share_count / 100, 1.235)
    add("模板", weight_kn["模板"], 0.04)
    m_actual = sum(x["力矩(kN·m)"] for x in moments)
    m_factored = p.moment_factor * m_actual
    live_m = p.combination_factor * p.gamma_q * top_live * 1.425
    wind_arm = net_height / 2 + template_h + p.wall_bracket_drop_mm / 1000 - 0.06 + 2.73
    wind_m = p.combination_factor * p.gamma_q * wind_construction * wind_arm
    tension_construction = (m_factored + live_m + wind_m) / 2.73

    original = {x["项目"]: x["力矩(kN·m)"] for x in moments}
    retract_m = p.template_retraction_mm / 1000
    changed = (
        1.2 * (0.246 + retract_m)
        + 0.92 * (1.0 + retract_m)
        + 0.432 * (0.95 + retract_m)
        + weight_kn["模板"] * (0.04 + retract_m)
    )
    m_climb_actual = m_actual - original["模板支架"] - original["滑座"] - original["模板调节支腿"] - original["模板"] + changed
    m_climb_factored = p.moment_factor * m_climb_actual
    lower_live_m = p.combination_factor * p.gamma_q * lower_live * 1.25
    climb_arm_net = net_height / 2 + template_h + p.wall_bracket_drop_mm / 1000 - 0.06 + p.floor_height_mm / 1000
    climb_arm_template = template_h / 2 + p.wall_bracket_drop_mm / 1000 - 0.06 + p.floor_height_mm / 1000
    climb_wind_net_m = p.combination_factor * p.gamma_q * net_height * net_width * wind_pressure_7_shield * climb_arm_net
    climb_template_force = p.combination_factor * p.gamma_q * (
        (template_h * template_len - opening_h * opening_len / 2) * wind_pressure_7_full
        + opening_h * opening_len / 2 * wind_pressure_7_shield
    )
    climb_template_m = climb_template_force * climb_arm_template
    tension_climbing = (m_climb_factored + lower_live_m + climb_wind_net_m + climb_template_m) / (p.floor_height_mm / 1000)

    shutdown_wind_force = p.combination_factor * p.gamma_q * net_height * wind_pressure_9 * net_width
    shutdown_wind_m = shutdown_wind_force * wind_arm
    tension_shutdown = (m_factored + shutdown_wind_m) / 2.73
    tension_total = {"施工工况": tension_construction, "爬升工况": tension_climbing, "停工工况": tension_shutdown}

    single_tension = {k: v / p.bolt_count for k, v in tension_total.items()}
    single_shear = {k: v / p.bolt_count for k, v in shear_total.items()}
    bolt_tension_capacity = p.bolt_effective_area_mm2 * p.bolt_tension_design_mpa / 1000
    bolt_shear_capacity = p.bolt_effective_area_mm2 * p.bolt_shear_design_mpa / 1000
    interaction = {
        k: sqrt((single_tension[k] / bolt_tension_capacity) ** 2 + (single_shear[k] / bolt_shear_capacity) ** 2)
        for k in tension_total
    }

    h0 = p.wall_thickness_mm - 50
    plate_a = 100.0
    punching = 2.8 * (plate_a + h0) * p.concrete_tension_mpa * h0 / 1000
    local_bearing = 2 * plate_a * plate_a * p.concrete_compression_mpa / 1000
    rail_span = p.floor_height_mm / 3 * 2
    rail_force = self_weight * 110 / 340
    rail_deflection = rail_force * 1000 * rail_span**3 / (48 * 210000 * 54425325.06)

    checks = {
        "螺栓施工组合": interaction["施工工况"] <= 1,
        "螺栓爬升组合": interaction["爬升工况"] <= 1,
        "螺栓停工组合": interaction["停工工况"] <= 1,
        "混凝土冲切": punching >= max(single_tension.values()),
        "混凝土局部受压": local_bearing >= max(single_shear.values()),
        "导轨挠度": rail_deflection <= rail_span / 250,
    }
    return {
        "model": "JFYM150B1-B2",
        "inputs": asdict(p),
        "processed": {"平台梁承担长度(m)": _r(platform_len), "模板有效面积(m²)": _r(template_h * template_len - opening_h * opening_len / 2), "模板上方护网高度(m)": _r(net_height), "护网宽度(m)": _r(net_width)},
        "weight_items": {k: _r(v) for k, v in weight_kn.items()},
        "self_weight_kn": _r(self_weight),
        "live_loads_kn": {"上操作平台": _r(top_live), "下操作平台": _r(lower_live)},
        "wind_loads_kn": {"施工": _r(wind_construction), "爬升": _r(wind_climbing), "停工": _r(wind_shutdown)},
        "tension_total_kn": {k: _r(v) for k, v in tension_total.items()},
        "shear_total_kn": {k: _r(v) for k, v in shear_total.items()},
        "tension_per_bolt_kn": {k: _r(v) for k, v in single_tension.items()},
        "shear_per_bolt_kn": {k: _r(v) for k, v in single_shear.items()},
        "bolt_interaction": {k: _r(v) for k, v in interaction.items()},
        "concrete": {"冲切承载力(kN)": _r(punching), "局部受压承载力(kN)": _r(local_bearing)},
        "rail": {"水平力(kN)": _r(rail_force), "跨度(mm)": _r(rail_span, 1), "挠度(mm)": _r(rail_deflection), "允许挠度(mm)": _r(rail_span / 250)},
        "checks": checks,
        "moment_items": [{k: (_r(v) if isinstance(v, (float, int)) else v) for k, v in x.items()} for x in moments],
    }


def calculate_platform_materials(units: pd.DataFrame, config: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = ["单元编号", "西侧(m)", "东侧(m)", "北侧(m)", "南侧(m)", "第三层翻板有效边长(m)", "踢脚板附加长度(m)"]
    missing = [c for c in required if c not in units.columns]
    if missing:
        raise ValueError(f"平台单元表缺少列：{', '.join(missing)}")
    df = units.copy()
    number_cols = required[1:]
    for col in number_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)
    df["周长(m)"] = df[["西侧(m)", "东侧(m)", "北侧(m)", "南侧(m)"]].sum(axis=1)
    df["单层平台面积(m²)"] = df["西侧(m)"] * df["北侧(m)"]
    perimeter = df["周长(m)"].sum()
    base_area = df["单层平台面积(m²)"].sum()
    guide_area = config["guide_width_m"] * config["guide_depth_m"] * config["guide_sides"] * config["guide_count"]
    rows = [
        ("平台板", base_area * config["platform_layers"], "m²"),
        ("后封板", perimeter * config["back_seal_width_m"] * config["back_seal_layers"], "m²"),
        ("推拉式封板", perimeter * config["sliding_seal_width_m"], "m²"),
        ("靠墙翻板", perimeter * config["wall_flap_width_m"] * config["wall_flap_layers"], "m²"),
        ("导轨封板", guide_area, "m²"),
        ("第三层翻板", df["第三层翻板有效边长(m)"].sum() * config["third_flap_width_m"], "m²"),
        ("护栏横杆", perimeter * config["guardrail_rails"], "m"),
        ("踢脚板", perimeter * config["guardrail_rails"] + df["踢脚板附加长度(m)"].sum(), "m"),
    ]
    summary = pd.DataFrame(rows, columns=["材料", "净计算量", "单位"])
    summary["含余量数量"] = summary["净计算量"] * config["material_allowance"]
    return df, summary


def calculate_guardrail_bom(units: pd.DataFrame, config: dict[str, float]) -> pd.DataFrame:
    segments=[]
    for _, row in units.iterrows():
        for side in ["西侧", "东侧", "北侧", "南侧"]:
            length=max(float(row.get(f"{side}(m)", 0) or 0), 0)
            if length:
                segments.append((str(row["单元编号"]), side, length))
    post_count=sum(ceil(length/config["post_spacing_m"])+1 for _,_,length in segments)
    horizontal=sum(length*config["guardrail_rails"] for _,_,length in segments)
    vertical=post_count*config["post_height_m"]
    diagonal_count=sum(ceil(length/config["diagonal_spacing_m"]) for _,_,length in segments) if config["include_diagonal"] else 0
    diagonal=diagonal_count*config["diagonal_length_m"]
    tie=config["tie_count"]*config["tie_length_m"]
    pipe_net=horizontal+vertical+diagonal+tie
    pipe_total=pipe_net*config["material_allowance"]
    butt=sum(max(ceil(length/config["stock_length_m"])-1,0)*config["guardrail_rails"] for _,_,length in segments)
    right_angle=post_count*config["guardrail_rails"]
    swivel=2*diagonal_count+2*config["tie_count"]
    rows=[
        ("防护钢管", "长度", pipe_net, pipe_total, "m"),
        ("立杆", "数量", post_count, ceil(post_count*config["material_allowance"]), "根"),
        ("旋转扣件", "斜撑及拉结两端", swivel, ceil(swivel*config["material_allowance"]), "个"),
        ("直角扣件", "横杆与立杆节点", right_angle, ceil(right_angle*config["material_allowance"]), "个"),
        ("对接扣件", "横杆定尺接长", butt, ceil(butt*config["material_allowance"]), "个"),
    ]
    return pd.DataFrame(rows,columns=["材料","计算依据","净计算量","含余量数量","单位"])


def calculate_connection_bom(conditions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    details=[]
    for _, row in conditions.iterrows():
        floor=str(row.get("楼层", "")).strip()
        pos=str(row.get("机位", "")).strip()
        if not floor or not pos: continue
        wall=float(row.get("墙厚(mm)", 0) or 0)
        tonnage=str(row.get("架体等级", "15t"))
        dia=42 if tonnage == "30t" else 36
        length=600 if wall <= 600 else 800 if wall <= 800 else 1000
        outputs=[]
        if bool(row.get("钢柱干涉", False)):
            outputs.append(("特殊预埋件", "按钢柱节点深化", 1, "钢柱干涉"))
        elif bool(row.get("对面有板", False)):
            outputs.append(("穿板螺栓", f"φ{dia}×{length}", 1, "对面有板"))
            if bool(row.get("梁内型钢", False)):
                outputs.append(("钩头螺栓", "36×320×200", 1, "梁内型钢"))
            else:
                outputs.append(("锥套", "36×90", 1, "常规有板支撑"))
        else:
            outputs.append(("锥套", "36×90", 2, "对面无板"))
        if bool(row.get("变截面", False)):
            outputs.append(("变截面垫板", "100", 1, "墙厚变化"))
        for material,spec,qty,trigger in outputs:
            details.append({"楼层":floor,"机位":pos,"材料":material,"规格":spec,"数量":qty,"触发条件":trigger,"规则状态":"待企业复核"})
    detail_df=pd.DataFrame(details,columns=["楼层","机位","材料","规格","数量","触发条件","规则状态"])
    if detail_df.empty:
        return detail_df, pd.DataFrame(columns=["材料","规格","施工数量","备用数量","总量"])
    summary=detail_df.groupby(["材料","规格"],as_index=False)["数量"].sum().rename(columns={"数量":"施工数量"})
    summary["备用数量"]=(summary["施工数量"]*0.05).apply(ceil)
    summary["总量"]=summary["施工数量"]+summary["备用数量"]
    return detail_df,summary
