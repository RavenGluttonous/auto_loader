import pyautogui

import auto_input.util


def autoscope_input(zlkh="", idh="", xm="", nl="", sjks="", sjys="", qcbw="", sjbb="", ):
    """
    autoscope自动输入
    Args:
        zlkh: 诊疗卡号
        idh: ID号
        xm: 姓名
        nl: 年龄
        sjks: 送检科室
        sjys: 送检医师
        qcbw: 取材部位
        sjbb: 送检标本

    """
    auto_input.util.auto_input(zlkh)
    auto_input.util.auto_input(idh)
    auto_input.util.auto_input(xm)
    # 跳过性别
    pyautogui.press('tab')
    auto_input.util.auto_input(nl)
    auto_input.util.auto_input(sjks)
    auto_input.util.auto_input(sjys)
    # 跳过送检标本
    pyautogui.press('tab')
    auto_input.util.auto_input(qcbw)
    auto_input.util.auto_input(sjbb)
    pyautogui.press('tab')
