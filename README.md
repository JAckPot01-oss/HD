# 液压爬模设计辅助系统（一期原型）

这是一个可运行的本地原型，将现有 Excel/Word 工作流拆成可追溯的数据和规则计算模块。

当前包含：

- 首截面平台板、封板、翻板、护栏和踢脚板统计；
- 防护钢管、立杆、旋转扣件、直角扣件、对接扣件统计；
- 按楼层和机位生成锥套、穿板螺栓、钩头螺栓、变截面垫板和特殊预埋件明细；
- JFYM150B1-B2常规机位的施工、爬升、停工工况验算；
- CSV数据包、JSON结果和Word计算摘要导出。

## 启动

```powershell
.\.venv\Scripts\streamlit.exe run .\outputs\hydraulic_climbing_formwork_mvp\streamlit_app.py
```

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest .\outputs\hydraulic_climbing_formwork_mvp\tests
```

## 工程边界

当前连接件规格规则标记为“待企业复核”。原型结果不能替代正式设计复核、审查、签字与盖章。
