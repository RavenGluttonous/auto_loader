import pyautogui

import auto_input.util


def xcope_input(xm="", nl="", zlkh="", ybbh="", ch="", bbzl="", sjys="", sjks="", ):
    """
    xcope自动输入
    Args:
        xm: 姓名
        nl: 年龄
        zlkh: 诊疗卡号
        ybbh: 样本编号
        ch: 床号
        bbzl: 标本种类
        sjys: 送检医师
        sjks: 送检科室

    """
    auto_input.util.auto_input(xm)
    # 跳过性别
    pyautogui.press('tab')
    auto_input.util.auto_input(nl)
    auto_input.util.auto_input(zlkh)
    auto_input.util.auto_input(ybbh)
    auto_input.util.auto_input(ch)
    auto_input.util.auto_input(bbzl)
    auto_input.util.auto_input(sjys)
    auto_input.util.auto_input(sjks)
    # 自动输入完成后跳到下个文本框
    pyautogui.press('tab')
