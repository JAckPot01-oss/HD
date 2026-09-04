from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from core.calculations import (
    JFYM150Input,
    calculate_connection_bom,
    calculate_guardrail_bom,
    calculate_jfym150,
    calculate_platform_materials,
)
from core.exporters import build_calculation_summary_docx, export_csv_zip

st.set_page_config(page_title="液压爬模设计辅助系统", page_icon=":material/precision_manufacturing:", layout="wide")

DEFAULT_UNITS=pd.DataFrame([
    ["1筒",2.6,2.6,9.3,9.3,18.6,10.5],
    ["2筒",2.6,2.6,9.3,9.3,18.6,10.5],
    ["3筒",8.8,8.8,2.6,2.6,8.8,10.5],
    ["4筒",11.8,11.8,2.6,2.6,11.8,10.5],
    ["5筒",8.8,8.8,2.6,2.6,8.8,10.5],
    ["6筒",8.8,8.8,2.6,2.6,8.8,10.5],
    ["7筒",2.8,2.8,2.6,2.6,2.8,10.5],
    ["8筒",2.6,2.6,2.8,2.8,2.6,10.5],
],columns=["单元编号","西侧(m)","东侧(m)","北侧(m)","南侧(m)","第三层翻板有效边长(m)","踢脚板附加长度(m)"])

DEFAULT_CONDITIONS=pd.DataFrame([
    ["22F","1","15t",1400,False,False,False,False],
    ["24F","12","15t",1200,True,False,False,True],
    ["25F","18","15t",1200,True,True,False,False],
    ["46F","35","30t",1000,True,True,False,False],
    ["51F","40","15t",500,False,False,True,True],
],columns=["楼层","机位","架体等级","墙厚(mm)","对面有板","梁内型钢","钢柱干涉","变截面"])

st.session_state.setdefault("units",DEFAULT_UNITS)
st.session_state.setdefault("conditions",DEFAULT_CONDITIONS)
st.session_state.setdefault("calc_result",calculate_jfym150(JFYM150Input()))

with st.sidebar:
    st.markdown("### 一期原型")
    st.badge("规则计算内核",icon=":material/check:",color="green")
    st.caption("数据样本：广州平台板、沈阳结构件、JFYM100B/JFYM150B1-B2计算书。")
    st.warning("原型结果用于规则核对，不能替代正式设计复核与签章。",icon=":material/warning:")

st.title("液压爬模设计辅助系统",icon=":material/precision_manufacturing:")
st.caption("施工信息结构化 → 平台与防护算量 → 附墙构件规则匹配 → 常规机位验算 → 成果导出")

overview,platform_tab,connection_tab,calc_tab,export_tab=st.tabs([
    ":material/dashboard: 总览",":material/view_in_ar: 平台与防护",":material/anchor: 附墙构件",":material/calculate: 机位验算",":material/download: 成果导出"
])

with overview:
    result=st.session_state.calc_result
    with st.container(horizontal=True):
        st.metric("计算模型",result["model"],border=True)
        st.metric("架体自重",f"{result['self_weight_kn']:.2f} kN",border=True)
        st.metric("最大螺栓组合比",f"{max(result['bolt_interaction'].values()):.3f}",border=True)
        st.metric("通过项",f"{sum(result['checks'].values())}/{len(result['checks'])}",border=True)
    with st.container(border=True):
        st.subheader("一期计算链",icon=":material/account_tree:")
        st.write("项目/截面/机位 → 几何与工况参数 → 确定性计算 → 规则选型 → 明细BOM → 计算摘要")
    cols=st.columns(2)
    with cols[0].container(border=True):
        st.subheader("当前已实现",icon=":material/task_alt:")
        st.write("平台板、封板、翻板、护栏和踢脚板；防护钢管及三类扣件；锥套、穿板螺栓、钩头螺栓、变截面垫板和特殊预埋件；JFYM150B1-B2常规机位验算。")
    with cols[1].container(border=True):
        st.subheader("下一批规则",icon=":material/pending_actions:")
        st.write("内墙大/小架体完整计算书、JFYM100B、悬挑与声屏障插件、钢柱特殊预埋深化、正式Word模板逐字段生成。")

with platform_tab:
    st.header("首截面平台及防护材料",icon=":material/view_in_ar:")
    st.caption("每行表示一个筒或爬模单元。当前矩形面积采用“西侧×北侧”，不规则单元应拆成多个边段。")
    units=st.data_editor(st.session_state.units,key="platform_units_editor",num_rows="dynamic",hide_index=True,
        column_config={c:st.column_config.NumberColumn(c,min_value=0.0,format="%.3f") for c in DEFAULT_UNITS.columns if c!="单元编号"})
    st.session_state.units=units
    with st.expander("计算参数",icon=":material/tune:"):
        a,b,c,d=st.columns(4)
        platform_layers=a.number_input("平台板层数",1,12,6)
        allowance=b.number_input("材料余量系数",1.0,1.3,1.06,0.01)
        rails=c.number_input("护栏横杆道数",1,8,2)
        guide_count=d.number_input("导轨封板位置数",0,200,17)
        a,b,c,d=st.columns(4)
        sliding=a.number_input("推拉封板宽度(m)",0.0,2.0,0.60,0.05)
        wall_flap=b.number_input("靠墙翻板宽度(m)",0.0,2.0,0.55,0.05)
        third=c.number_input("第三层翻板宽度(m)",0.0,2.0,0.60,0.05)
        back_layers=d.number_input("后封板层数",0,8,0)
        a,b,c,d=st.columns(4)
        post_spacing=a.number_input("立杆间距(m)",0.5,4.0,1.5,0.1)
        post_height=b.number_input("立杆高度(m)",0.5,4.0,1.5,0.1)
        diagonal_spacing=c.number_input("斜撑间距(m)",1.0,12.0,6.0,0.5)
        tie_count=d.number_input("拉结数量",0,200,10)
    config={"platform_layers":platform_layers,"material_allowance":allowance,"back_seal_width_m":0.2,"back_seal_layers":back_layers,
            "sliding_seal_width_m":sliding,"wall_flap_width_m":wall_flap,"wall_flap_layers":1,"guide_width_m":0.72,"guide_depth_m":0.55,
            "guide_sides":2,"guide_count":guide_count,"third_flap_width_m":third,"guardrail_rails":rails,"post_spacing_m":post_spacing,
            "post_height_m":post_height,"include_diagonal":True,"diagonal_spacing_m":diagonal_spacing,"diagonal_length_m":1.5,"tie_count":tie_count,
            "tie_length_m":1.6,"stock_length_m":6.0}
    unit_detail,platform_summary=calculate_platform_materials(units,config)
    guardrail_bom=calculate_guardrail_bom(units,config)
    with st.container(horizontal=True):
        st.metric("单层平台面积",f"{unit_detail['单层平台面积(m²)'].sum():.2f} m²",border=True)
        st.metric("单元总周长",f"{unit_detail['周长(m)'].sum():.2f} m",border=True)
        st.metric("平台板",f"{platform_summary.loc[platform_summary['材料']=='平台板','含余量数量'].iloc[0]:.2f} m²",border=True)
        st.metric("防护钢管",f"{guardrail_bom.loc[guardrail_bom['材料']=='防护钢管','含余量数量'].iloc[0]:.1f} m",border=True)
    left,right=st.columns(2)
    with left.container(border=True):
        st.subheader("平台材料汇总")
        st.dataframe(platform_summary,hide_index=True,column_config={"净计算量":st.column_config.NumberColumn(format="%.3f"),"含余量数量":st.column_config.NumberColumn(format="%.3f")})
    with right.container(border=True):
        st.subheader("钢管与扣件汇总")
        st.dataframe(guardrail_bom,hide_index=True,column_config={"净计算量":st.column_config.NumberColumn(format="%.1f"),"含余量数量":st.column_config.NumberColumn(format="%.1f")})

with connection_tab:
    st.header("逐层附墙连接件",icon=":material/anchor:")
    st.caption("现有企业经验规则已转成透明规则；标记为“待企业复核”的规格不会被系统当成最终批准设计。")
    conditions=st.data_editor(st.session_state.conditions,key="conditions_editor",num_rows="dynamic",hide_index=True,
        column_config={"架体等级":st.column_config.SelectboxColumn(options=["15t","30t"]),"墙厚(mm)":st.column_config.NumberColumn(min_value=100,max_value=3000,step=50),
        "对面有板":st.column_config.CheckboxColumn(),"梁内型钢":st.column_config.CheckboxColumn(),"钢柱干涉":st.column_config.CheckboxColumn(),"变截面":st.column_config.CheckboxColumn()})
    st.session_state.conditions=conditions
    connection_detail,connection_summary=calculate_connection_bom(conditions)
    with st.container(border=True):
        st.subheader("规则输出明细")
        st.dataframe(connection_detail,hide_index=True)
    with st.container(border=True):
        st.subheader("连接件BOM")
        st.dataframe(connection_summary,hide_index=True)

with calc_tab:
    st.header("JFYM150B1-B2常规机位验算",icon=":material/calculate:")
    st.caption("公式已按上传基准表逐项重建，施工、爬升、停工三种工况分别计算。")
    current=st.session_state.calc_result["inputs"]
    with st.form("calc_form"):
        a,b,c=st.columns(3)
        project=a.text_input("项目名称",current["project_name"])
        position=b.text_input("机位名称",current["position_name"])
        wall=c.number_input("墙厚(mm)",100.0,3000.0,float(current["wall_thickness_mm"]),50.0)
        a,b,c=st.columns(3)
        l2=a.number_input("较大机位间距(mm)",0.0,15000.0,float(current["spacing_large_mm"]),50.0)
        l1=b.number_input("较小机位间距(mm)",0.0,15000.0,float(current["spacing_small_mm"]),50.0)
        l3=c.number_input("悬挑端长度(mm)",0.0,10000.0,float(current["cantilever_mm"]),50.0)
        a,b,c=st.columns(3)
        floor=a.number_input("楼层层高(mm)",2000.0,10000.0,float(current["floor_height_mm"]),50.0)
        template_h=b.number_input("模板高度(mm)",1000.0,10000.0,float(current["template_height_mm"]),50.0)
        template_end=c.number_input("悬挑端模板长度(mm)",0.0,10000.0,float(current["cantilever_template_mm"]),50.0)
        a,b,c=st.columns(3)
        opening_h=a.number_input("模板洞口高度(mm)",0.0,10000.0,float(current["opening_height_mm"]),50.0)
        opening_w=b.number_input("模板洞口宽度(mm)",0.0,10000.0,float(current["opening_width_mm"]),50.0)
        retract=c.number_input("模板退出距离(mm)",0.0,3000.0,float(current["template_retraction_mm"]),50.0)
        with st.expander("风荷载、材料和系数",icon=":material/tune:"):
            a,b,c=st.columns(3)
            gust=a.number_input("阵风系数",0.1,5.0,float(current["gust_factor"]),0.01)
            height_factor=b.number_input("风压高度变化系数",0.1,5.0,float(current["height_factor"]),0.01)
            shield=c.number_input("挡风系数",0.1,2.0,float(current["shield_factor"]),0.01)
            a,b,c=st.columns(3)
            template_weight=a.number_input("模板重量(kg/m²)",10.0,200.0,float(current["template_weight_kg_m2"]),5.0)
            support=b.number_input("上架体支座高度(mm)",0.0,2000.0,float(current["upper_support_height_mm"]),50.0)
            drop=c.number_input("附墙座下返高度(mm)",0.0,3000.0,float(current["wall_bracket_drop_mm"]),50.0)
        submitted=st.form_submit_button("执行验算",type="primary",icon=":material/play_arrow:")
    if submitted:
        params=JFYM150Input(project_name=project,position_name=position,spacing_large_mm=l2,spacing_small_mm=l1,cantilever_mm=l3,
            floor_height_mm=floor,template_height_mm=template_h,opening_height_mm=opening_h,opening_width_mm=opening_w,cantilever_template_mm=template_end,
            upper_support_height_mm=support,wall_bracket_drop_mm=drop,gust_factor=gust,height_factor=height_factor,template_retraction_mm=retract,
            wall_thickness_mm=wall,template_weight_kg_m2=template_weight,shield_factor=shield)
        st.session_state.calc_result=calculate_jfym150(params)
        st.toast("验算已完成",icon=":material/check_circle:")
    result=st.session_state.calc_result
    with st.container(horizontal=True):
        for state in ["施工工况","爬升工况","停工工况"]:
            ratio=result["bolt_interaction"][state]
            st.metric(state,f"组合比 {ratio:.3f}","满足" if ratio<=1 else "不满足",delta_color="normal" if ratio<=1 else "inverse",border=True)
    result_df=pd.DataFrame({"工况":["施工工况","爬升工况","停工工况"],
        "单栓拉力(kN)":[result["tension_per_bolt_kn"][x] for x in ["施工工况","爬升工况","停工工况"]],
        "单栓剪力(kN)":[result["shear_per_bolt_kn"][x] for x in ["施工工况","爬升工况","停工工况"]],
        "组合比":[result["bolt_interaction"][x] for x in ["施工工况","爬升工况","停工工况"]]})
    left,right=st.columns(2)
    with left.container(border=True):
        st.subheader("螺栓内力")
        st.dataframe(result_df,hide_index=True,column_config={"单栓拉力(kN)":st.column_config.NumberColumn(format="%.3f"),"单栓剪力(kN)":st.column_config.NumberColumn(format="%.3f"),"组合比":st.column_config.ProgressColumn(min_value=0,max_value=1.2,format="%.3f")})
    with right.container(border=True):
        st.subheader("验算清单")
        st.table({k:(":green-badge[满足]" if v else ":red-badge[不满足]") for k,v in result["checks"].items()},border="horizontal")

with export_tab:
    st.header("成果导出",icon=":material/download:")
    connection_detail,connection_summary=calculate_connection_bom(st.session_state.conditions)
    unit_detail,platform_summary=calculate_platform_materials(st.session_state.units,config)
    guardrail_bom=calculate_guardrail_bom(st.session_state.units,config)
    tables={"平台单元明细":unit_detail,"平台材料汇总":platform_summary,"钢管扣件汇总":guardrail_bom,"连接件明细":connection_detail,"连接件BOM":connection_summary}
    package=export_csv_zip(tables,st.session_state.calc_result)
    docx=build_calculation_summary_docx(st.session_state.calc_result)
    with st.container(horizontal=True):
        st.download_button("下载数据包",package,"液压爬模一期计算数据.zip","application/zip",icon=":material/folder_zip:",type="primary")
        st.download_button("下载计算摘要",docx,"液压爬模机位计算摘要.docx","application/vnd.openxmlformats-officedocument.wordprocessingml.document",icon=":material/description:")
        st.download_button("下载JSON",json.dumps(st.session_state.calc_result,ensure_ascii=False,indent=2),"机位计算结果.json","application/json",icon=":material/data_object:")
    st.caption("数据包使用UTF-8 BOM CSV，便于Excel直接打开；正式Excel模板与完整计算书将在规则确认后接入。")
