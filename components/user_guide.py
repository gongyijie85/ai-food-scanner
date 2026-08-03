"""首次使用指引：首页/扫描页可折叠步骤。"""

import streamlit as st


def render_user_guide(page: str = "home") -> None:
    """渲染使用指引。首次进入默认展开，之后默认折叠。"""
    flag = f"guide_seen_{page}"
    # 结果页默认收起，把首屏留给「分数 + 一句话 + 听结果」
    if page == "result":
        expanded = False
    else:
        expanded = not st.session_state.get(flag, False)

    title = "第一次用？三步看懂配料表"
    if page == "scan":
        title = "拍照小技巧（很重要）"
    elif page == "result":
        title = "结果怎么看"

    with st.expander(title, expanded=expanded):
        if page == "home":
            st.markdown(
                "\n".join(
                    [
                        "1. 点 **拍配料表**（对准包装上的配料小字，不是商品名那面）",
                        "2. 记住三步：**光线够 · 尽量平 · 字要大**",
                        "3. 看结果：先看 **一句话**，再点 **听结果**",
                        "4. 历史里可筛选 **要注意**，方便复盘少买的商品",
                        "",
                        "**给谁用？** 建议子女或会用手机的家人操作；结果可以读给老人听。",
                        "**注意：** 本工具是配料说明助手，**不是**医生诊断。",
                    ]
                )
            )
        elif page == "scan":
            st.markdown(
                "\n".join(
                    [
                        "页面上方有 **三步卡片** 和 **清晰/模糊对比图**，先看再拍。",
                        "",
                        "1. **光线够** — 避免反光发白",
                        "2. **尽量平** — 手机与包装平行",
                        "3. **字要大** — 「配料」小字占满画面",
                        "",
                        "识别失败会再次提示这三步；成功后进结果页可点 **听结果**。",
                    ]
                )
            )
        else:
            st.markdown(
                "\n".join(
                    [
                        "- **一句话**：给家人的通俗结论（偶尔吃 / 少买），不是医嘱",
                        "- **配料参考分**：仅供参考，不是「安全认证」",
                        "- **添加剂清单**：默认先列要注意的；较友好的可展开",
                        "- **听结果**：语音朗读（建议系统浏览器；微信内可能无声）",
                        "- **待核对包装**：库未完全匹配，请以包装原文为准",
                    ]
                )
            )

        if st.button("我知道了，下次默认收起", key=f"guide_dismiss_{page}"):
            st.session_state[flag] = True
            st.rerun()
