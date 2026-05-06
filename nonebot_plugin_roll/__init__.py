import random
import re

from nonebot import on_regex, on_command
from nonebot.adapters import Event, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

__plugin_version__ = "v0.2.3"
__plugin_usages__ = f"""
掷骰子 {__plugin_version__}
支持格式：
  rd2          - 掷1个2面骰
  r1d2         - 掷1个2面骰
  rd 1d2       - 掷1个2面骰
  rd2d6        - 掷2个6面骰
  r2d2 包子 饺子 馄饨 面条 - 掷骰并附加参数
  roll 2d6     - 掷2个6面骰
  掷骰 2d6     - 掷2个6面骰""".strip()

__plugin_meta__ = PluginMetadata(
    name="掷骰子",
    description="掷骰！扔出指定个数的多面骰子🎲",
    usage=__plugin_usages__,
    type="application",
    homepage="https://github.com/MinatoAquaCrews/nonebot_plugin_roll",
    extra={
        "author": "KafCoppelia <k740677208@gmail.com>",
        "version": __plugin_version__,
    },
    supported_adapters=None,
)

# 正则匹配：匹配 r 开头，后面可以是骰子表达式，可选空格和参数
# 注意：这个正则会匹配 rd2、r1d2、r2d2 等格式
roll_regex = on_regex(r"^r(d)?(\d*)?d(\d+)(?:\s+(.*))?$|^r(d)?(\d+)(?:\s+(.*))?$", priority=9)

# 处理 rd 命令（带空格格式）- 提高优先级到 8，让正则优先匹配
# 但注意：rd2 这种无空格的也会被正则匹配，所以需要避免重复
# 解决方案：rd_cmd 只处理有空格的情况
rd_cmd = on_command("rd", priority=10)

# 处理 roll 和 掷骰 命令（带空格格式）
roll_cmd = on_command("roll", aliases={"掷骰"}, priority=10)


def parse_roll_args(roll_str: str):
    """解析骰子参数字符串，返回 (dice_num, dice_side) 或 None"""
    roll_str = roll_str.strip()
    
    # 匹配标准 xdy 或 dy 格式
    match = re.match(r"^((\-|\+)?\d+)?d(\d+)$", roll_str)
    if match:
        dice_num_str = match.group(1)
        dice_side = int(match.group(3))
        if dice_num_str is None or dice_num_str == "":
            dice_num = 1
        else:
            dice_num = int(dice_num_str)
        return dice_num, dice_side
    
    # 匹配纯数字格式（如 rd2 中的 2）
    match_num = re.match(r"^(\d+)$", roll_str)
    if match_num:
        return 1, int(match_num.group(1))
    
    return None


def extract_options(rest_str: str):
    """从剩余字符串中提取参数列表（按空格分割）"""
    if not rest_str:
        return []
    # 按空格分割，过滤空字符串
    return [opt.strip() for opt in rest_str.split() if opt.strip()]


async def process_roll(matcher: Matcher, dice_part: str, options: list):
    """处理掷骰逻辑"""
    # 解析骰子参数
    parsed = parse_roll_args(dice_part)
    if not parsed:
        await matcher.finish("格式不对呢, 请重新输入: rd [x]d[y] [参数1] [参数2] ...")
        return
    
    dice_num, dice_side = parsed
    
    # 限制检查
    if dice_num > 999 or dice_side > 999:
        await matcher.finish("错误！谁没事干扔那么多骰子啊😅")
    
    if dice_num <= 0 or dice_side <= 0:
        await matcher.finish("错误！你掷出了不存在的骰子, 只有上帝知道结果是多少🤔")
    
    # 彩蛋
    if (dice_num == 114 and dice_side == 514) or (dice_num == 514 and dice_side == 114):
        await matcher.finish("恶臭！奇迹和魔法可不是免费的！🤗")
    
    if random.randint(1, 100) == 99:
        await matcher.finish("彩蛋！骰子之神似乎不看好你, 你掷出的骰子全部消失了😥")
    
    _bonus = random.randint(1, 1000)
    bonus = 0
    if _bonus % 111 == 0:
        bonus = _bonus
        await matcher.send(f"彩蛋！你掷出的点数将增加【{bonus}】")
    
    # 掷骰计算（记录每个骰子的结果）
    dice_results = []
    for i in range(dice_num):
        result = random.choice(range(dice_side)) + 1
        dice_results.append(result)
    
    dice_sum = sum(dice_results)
    dice_result = dice_sum + bonus
    
    # 构建输出消息
    output_lines = []
    
    # 显示掷骰过程（不超过20个骰子时）
    if dice_num <= 20 and dice_num > 0:
        process_str = "+".join(str(r) for r in dice_results)
        if bonus > 0:
            process_str += f"+{bonus}"
        process_str += f"={dice_result}"
        output_lines.append(process_str)
    
    # 添加标准输出格式
    output_lines.append(f"你掷出了{dice_num}个{dice_side}面骰子, 点数为【{dice_result}】")
    
    # 附加参数选择
    selected_option = None
    if options:
        # 根据骰子总和（不加成）选择参数
        if 1 <= dice_sum <= len(options):
            selected_option = options[dice_sum - 1]
        else:
            # 如果超出范围，使用循环索引
            selected_option = options[(dice_sum - 1) % len(options)]
        output_lines.append(selected_option)
    
    # 输出结果
    await matcher.finish("\n".join(output_lines))


@roll_regex.handle()
async def handle_regex(matcher: Matcher, event: Event):
    """处理正则匹配的输入（无空格格式，如 rd2, r1d2, r2d2 大米 白面）"""
    msg = event.get_plaintext().strip()
    
    # 使用正则匹配提取骰子部分和附加参数
    # 匹配 r1d2 或 rd2 或 r2d2 等格式，以及可选的附加参数
    match = re.match(r"^r(d)?(?:(?:(\d*)?d(\d+))|(?:(\d+)))(?:\s+(.*))?$", msg)
    
    if not match:
        # 如果正则不匹配，忽略（让其他处理器处理）
        return
    
    # 提取骰子表达式
    if match.group(2) is not None:  # 格式: r1d2 或 r2d6
        num = match.group(2) or ""
        side = match.group(3)
        if num:
            dice_part = f"{num}d{side}"
        else:
            dice_part = f"d{side}"
    elif match.group(4) is not None:  # 格式: r2 或 rd2
        num = match.group(4)
        dice_part = num  # 纯数字，后面解析时会转为 d{num}
    else:
        return
    
    # 提取附加参数
    rest = match.group(5) or ""
    options = extract_options(rest)
    
    await process_roll(matcher, dice_part, options)


@rd_cmd.handle()
async def handle_rd_cmd(matcher: Matcher, args: Message = CommandArg()):
    """处理 rd 命令（带空格格式，如 rd 1d2）"""
    full_arg = args.extract_plain_text().strip()
    if not full_arg:
        await matcher.finish("你还没掷骰子呢：rd [x]d[y] [参数1] [参数2] ...")
        return
    
    # 分离骰子表达式和参数列表
    parts = full_arg.split()
    if not parts:
        await matcher.finish("格式不对呢, 请重新输入: rd [x]d[y] [参数1] [参数2] ...")
        return
    
    dice_part = parts[0]
    options = parts[1:] if len(parts) > 1 else []
    
    await process_roll(matcher, dice_part, options)


@roll_cmd.handle()
async def handle_roll_cmd(matcher: Matcher, args: Message = CommandArg()):
    """处理 roll/掷骰 命令（带空格格式）"""
    full_arg = args.extract_plain_text().strip()
    if not full_arg:
        await matcher.finish("你还没掷骰子呢：roll [x]d[y] [参数1] [参数2] ...")
        return
    
    # 分离骰子表达式和参数列表
    parts = full_arg.split()
    if not parts:
        await matcher.finish("格式不对呢, 请重新输入: roll [x]d[y] [参数1] [参数2] ...")
        return
    
    dice_part = parts[0]
    options = parts[1:] if len(parts) > 1 else []
    
    await process_roll(matcher, dice_part, options)