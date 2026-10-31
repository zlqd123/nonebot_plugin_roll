import random
import re

from nonebot import on_regex
from nonebot.adapters import Event
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata

__plugin_version__ = "v0.2.3"
__plugin_usages__ = f"""
掷骰子 {__plugin_version__}
支持格式：
  rd2                 - 掷1个2面骰
  r1d2                - 掷1个2面骰
  .rd2                - 支持点号开头
  .r1d2               - 支持点号开头
  rd 1d2              - 原格式（有空格）
  roll 2d6            - roll命令（有空格）
  掷骰 2d6            - 中文命令（有空格）
  
附加参数功能（用空格分隔）：
  rd2 大米 白面        - 根据点数选择对应项
  r3d6 攻击 防御 闪避  - 多骰子带参数""".strip()

__plugin_meta__ = PluginMetadata(
    name="掷骰子",
    description="掷骰！扔出指定个数的多面骰子🎲，支持附加参数选择",
    usage=__plugin_usages__,
    type="application",
    homepage="https://github.com/MinatoAquaCrews/nonebot_plugin_roll",
    extra={
        "author": "KafCoppelia <k740677208@gmail.com>",
        "version": __plugin_version__,
    },
    supported_adapters=None,
)

# ==================== 处理器1：忽略无效格式 ====================
# 匹配以 r 开头但格式无效的输入（如 rx, r3, r 2d6 等）
# priority 数值越小优先级越高
ignore_invalid = on_regex(
    r"^\.?r(?:[^d\d\s]|\s+\d*d?\d*|$)",
    priority=5
)


@ignore_invalid.handle()
async def handle_ignore():
    """静默忽略无效输入，不产生任何响应"""
    return


# ==================== 处理器2：紧凑有效格式 ====================
# 匹配：rd2, r2d6, .rd2, .r2d6 等（无空格）
roll_compact = on_regex(
    r"^\.?r(?:d\d+|(?:\d+d\d+))(?:\s+.*)?$",
    priority=8
)


def parse_dice_expression(expr: str):
    """解析骰子表达式，返回 (dice_num, dice_side)"""
    expr = expr.strip().lower()
    
    match = re.match(r"^(\d*)d(\d+)$", expr)
    if match:
        num_str, side_str = match.groups()
        dice_num = int(num_str) if num_str else 1
        dice_side = int(side_str)
        return dice_num, dice_side
    
    match = re.match(r"^(\d+)$", expr)
    if match:
        dice_side = int(match.group(1))
        return 1, dice_side
    
    return None, None


def extract_options(text: str):
    """从文本中提取选项列表"""
    if not text:
        return []
    return [opt.strip() for opt in text.split() if opt.strip()]


def roll_dice(dice_num: int, dice_side: int):
    """掷骰子"""
    results = [random.randint(1, dice_side) for _ in range(dice_num)]
    return results, sum(results)


def format_roll_process(results: list, total: int, bonus: int = 0):
    """格式化掷骰过程"""
    if not results:
        return ""
    process = "+".join(str(r) for r in results)
    if bonus > 0:
        process += f"+{bonus}"
    process += f"={total}"
    return process


async def send_roll_result(
    matcher: Matcher,
    dice_num: int,
    dice_side: int,
    results: list,
    total: int,
    bonus: int,
    options: list
):
    """发送掷骰结果"""
    output_lines = []
    
    if dice_num <= 20 and dice_num > 0:
        process_str = format_roll_process(results, total + bonus, bonus)
        if process_str:
            output_lines.append(process_str)
    
    output_lines.append(f"你掷出了{dice_num}个{dice_side}面骰子, 点数为【{total + bonus}】")
    
    if options:
        idx = (total - 1) % len(options)
        selected = options[idx]
        output_lines.append(selected)
    
    await matcher.finish("\n".join(output_lines))


@roll_compact.handle()
async def handle_compact(matcher: Matcher, event: Event):
    """处理紧凑格式（无空格：rd2, r2d6, .rd2, .r2d6）"""
    raw_msg = event.get_plaintext().strip()
    
    # 提取骰子表达式和选项
    match = re.match(
        r"^\.?r(?:d(\d+)|(\d+)d(\d+))(?:\s+(.*))?$",
        raw_msg,
        re.IGNORECASE
    )
    
    if not match:
        return
    
    if match.group(1):  # rd2 格式
        dice_expr = match.group(1)
        options_text = match.group(4) or ""
    else:  # r2d6 格式
        num = match.group(2)
        side = match.group(3)
        dice_expr = f"{num}d{side}"
        options_text = match.group(4) or ""
    
    options = extract_options(options_text)
    dice_num, dice_side = parse_dice_expression(dice_expr)
    
    if dice_num is None or dice_side is None:
        await matcher.finish("骰子格式错误")
        return
    
    # 限制检查
    if dice_num > 999 or dice_side > 999:
        await matcher.finish("错误！谁没事干扔那么多骰子啊😅")
    
    if dice_num <= 0 or dice_side <= 0:
        await matcher.finish("错误！你掷出了不存在的骰子")
    
    # 彩蛋
    if (dice_num == 114 and dice_side == 514) or (dice_num == 514 and dice_side == 114):
        await matcher.finish("恶臭！奇迹和魔法可不是免费的！🤗")
    
    if random.randint(1, 100) == 99:
        await matcher.finish("彩蛋！骰子之神似乎不看好你，你掷出的骰子全部消失了😥")
    
    _bonus_rand = random.randint(1, 1000)
    bonus = 0
    if _bonus_rand % 111 == 0:
        bonus = _bonus_rand
        await matcher.send(f"彩蛋！你掷出的点数将增加【{bonus}】")
    
    results, total = roll_dice(dice_num, dice_side)
    final_total = total + bonus
    
    if final_total == 6324:
        await matcher.send("彩蛋！6324工作室祝大家新年快乐！")
    
    await send_roll_result(matcher, dice_num, dice_side, results, total, bonus, options)


# ==================== 处理器3：带空格格式 ====================
roll_spaced = on_regex(
    r"^(?:rd|roll|掷骰)\s+(\S+)(?:\s+(.*))?$",
    priority=10
)


@roll_spaced.handle()
async def handle_spaced(matcher: Matcher, event: Event):
    """处理带空格格式（rd 1d2, roll 2d6, 掷骰 1d20）"""
    raw_msg = event.get_plaintext().strip()
    
    match = re.match(
        r"^(?:rd|roll|掷骰)\s+(\S+)(?:\s+(.*))?$",
        raw_msg,
        re.IGNORECASE
    )
    
    if not match:
        return
    
    dice_expr = match.group(1)
    options_text = match.group(2) or ""
    options = extract_options(options_text)
    
    dice_num, dice_side = parse_dice_expression(dice_expr)
    
    if dice_num is None or dice_side is None:
        await matcher.finish("骰子格式错误，请使用：rd 2d6")
        return
    
    # 限制检查
    if dice_num > 999 or dice_side > 999:
        await matcher.finish("错误！谁没事干扔那么多骰子啊😅")
    
    if dice_num <= 0 or dice_side <= 0:
        await matcher.finish("错误！你掷出了不存在的骰子")
    
    # 彩蛋
    if (dice_num == 114 and dice_side == 514) or (dice_num == 514 and dice_side == 114):
        await matcher.finish("恶臭！奇迹和魔法可不是免费的！🤗")
    
    if random.randint(1, 100) == 99:
        await matcher.finish("彩蛋！骰子之神似乎不看好你，你掷出的骰子全部消失了😥")
    
    _bonus_rand = random.randint(1, 1000)
    bonus = 0
    if _bonus_rand % 111 == 0:
        bonus = _bonus_rand
        await matcher.send(f"彩蛋！你掷出的点数将增加【{bonus}】")
    
    results, total = roll_dice(dice_num, dice_side)
    final_total = total + bonus
    
    if final_total == 6324:
        await matcher.send("彩蛋！6324工作室祝大家新年快乐！")
    
    await send_roll_result(matcher, dice_num, dice_side, results, total, bonus, options)