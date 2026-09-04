import pandas as pd

from core.calculations import JFYM150Input, calculate_connection_bom, calculate_jfym150, calculate_platform_materials


def test_jfym150_matches_reference_workbook():
    r=calculate_jfym150(JFYM150Input())
    assert abs(r["self_weight_kn"]-110.98)<0.02
    assert abs(r["tension_total_kn"]["施工工况"]-179.084)<0.03
    assert abs(r["tension_total_kn"]["爬升工况"]-120.972)<0.03
    # 原表在多级公式链中保留显示精度，容许0.05 kN的累计舍入差。
    assert abs(r["tension_total_kn"]["停工工况"]-203.363)<0.05
    assert abs(r["bolt_interaction"]["施工工况"]-0.600)<0.003
    assert abs(r["rail"]["挠度(mm)"]-1.77)<0.01


def test_guangzhou_platform_reference():
    units=pd.DataFrame([
        ["1",2.6,2.6,9.3,9.3,0,0],["2",2.6,2.6,9.3,9.3,0,0],["3",8.8,8.8,2.6,2.6,0,0],
        ["4",11.8,11.8,2.6,2.6,0,0],["5",8.8,8.8,2.6,2.6,0,0],["6",8.8,8.8,2.6,2.6,0,0],
        ["7",2.8,2.8,2.6,2.6,0,0],["8",2.6,2.6,2.8,2.8,0,0],
    ],columns=["单元编号","西侧(m)","东侧(m)","北侧(m)","南侧(m)","第三层翻板有效边长(m)","踢脚板附加长度(m)"])
    cfg={"platform_layers":6,"material_allowance":1.0,"back_seal_width_m":0.2,"back_seal_layers":0,
         "sliding_seal_width_m":0.6,"wall_flap_width_m":0.55,"wall_flap_layers":1,"guide_width_m":0.72,
         "guide_depth_m":0.55,"guide_sides":2,"guide_count":17,"third_flap_width_m":0.6,"guardrail_rails":2}
    _,s=calculate_platform_materials(units,cfg)
    values=dict(zip(s["材料"],s["净计算量"]))
    assert abs(values["平台板"]-973.44)<1e-6
    assert abs(values["推拉式封板"]-99.84)<1e-6
    assert abs(values["靠墙翻板"]-91.52)<1e-6
    assert abs(values["导轨封板"]-13.464)<1e-6
    assert abs(values["护栏横杆"]-332.8)<1e-6


def test_connection_rules():
    rows=pd.DataFrame([["25F","18","15t",1200,True,True,False,True]],columns=["楼层","机位","架体等级","墙厚(mm)","对面有板","梁内型钢","钢柱干涉","变截面"])
    detail,summary=calculate_connection_bom(rows)
    assert set(detail["材料"])=={"穿板螺栓","钩头螺栓","变截面垫板"}
    assert summary["总量"].sum()==6
