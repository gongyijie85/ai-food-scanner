"""首次使用指引：首页/扫描页可折叠步骤。"""

import streamlit as st


def render_user_guide(page: str = "home") -> None:
    """渲染使用指引。首次进入默认展开，之后默认折叠。"""
    flag = f"guide_seen_{page}"
    expanded = not st.session_state.get(flag, False)

    title = "第一次用？三步看懂配料表"
    if page == "scan":
        title = "拍照小技巧（很重要）"
    elif page == "result":
        title = "结果怎么看"

    with st.expander(title, expanded=expanded):
        if page == "home":
            st.markdown(
                """
1. 点下方 **拍照识别**  
2. **对准包装上的「配料表」小字** 拍照（不要只拍商品名那面）  
3. 看结果：先看 **关注提示**，再听 **听结果**；有疑问以包装和医生为准  

**给谁用？** 建议子女或会用手机的家人操作；结果可以读给老人听。  
**注意：** 本工具是配料说明助手，**不是**医生诊断，也**不能**代替「能不能吃」的医疗判断。
                """.strip()
            )
        elif page == "scan":
            st.markdown(
                """
**拍清楚，才能认得出：**

1. 光线充足，避免反光  
2. 手机与包装尽量 **平行**，配料表文字 **占满屏幕**  
3. 对焦清晰后再拍；模糊、歪斜、只拍广告面 → 容易失败  
4. 可选填健康档案（疾病/用药），便于提示更相关的关注项  

识别后会进入结果页，可点 **听结果** 用语音播报。
                """.strip()
            )
        else:
            st.markdown(
                """
- **配料参考分**：仅供参考，不是「安全认证」或「能吃证明」  
- **注意 / 较友好**：对添加剂的通俗提示，请结合自身情况  
- **听结果**：语音朗读摘要（建议用系统浏览器，微信内可能无声）  
- 若显示 **待核对包装**：表示库中未完全匹配，请以包装原文为准  
                """.strip()
            )

        if st.button("我知道了，下次默认收起", key=f"guide_dismiss_{page}"):
            st.session_state[flag] = True
            st.rerun()
