from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Tuple, TypeVar

from .rawio import write_to_judger, debug

from .gamedata import Ant, Tower, TowerType, SuperWeaponType

from .coord import Coord


def _read_line_of_int() -> list[int]:
    return [int(s) for s in input().split(' ')]


T = TypeVar("T")


def _read_list(read_func: Callable[[], T]) -> list[T]:
    n = int(input())
    return [read_func() for i in range(n)]


@dataclass
class InitInfo:
    """游戏初始化信息"""
    my_seat: int  #: 您的位置。0代表您是先手，1代表您是后手。
    seed: int  #: 用于初始化信息素的随机数种子。


def read_init_info() -> InitInfo:
    """
    读取游戏初始化信息。

    :return: 游戏初始化信息，包括当前玩家的位置/先后手和信息素初始化种子。
    """
    part = _read_line_of_int()
    debug(f"{part}")
    return InitInfo(part[0], part[1])


class OperationType(IntEnum):
    """描述操作类型的枚举。其中给枚举项所赋的值都与游戏文档中的描述吻合。"""
    BUILD_TOWER = 11  #: 建造防御塔。
    UPGRADE_TOWER = 12  #: 升级防御塔。
    DOWNGRADE_TOWER = 13  #: 降级/拆除防御塔。
    DEPLOY_LIGHTNING_STORM = 21  #: 部署闪电风暴：在指定位置生成闪电风暴，每回合对经过此区域的地方蚂蚁造成巨额伤害。
    DEPLOY_EMP_BLASTER = 22  #: 部署EMP轰炸：在指定位置释放EMP轰炸，令敌方防御塔暂时失灵，而且也不能新建/升级/降级防御塔。
    DEPLOY_DEFLECTORS = 23  #: 部署重力偏射盾：在指定位置部署重力偏射盾，在持续时间内让经过次区域的我方蚂蚁免疫低于自身最大生命值50%的防御塔伤害。
    DEPLOY_EMERGENCY_EVASION = 24  #: 部署紧急回避装置：立刻为区域内我方蚂蚁装备紧急回避装置，可以闪避两次来自敌方防御塔的伤害。
    UPGRADE_GENERATE_SPEED = 31  #: 升级主基地的“蚂蚁”生成速度。
    UPGRADE_ANT_MAXHP = 32  #: 升级主基地新生成“蚂蚁”的最大生命值。


@dataclass
class Operation:
    """
    描述具体的操作。根据不同的操作类型，其参数的含义也不同，具体的参数含义参见游戏文档。

    我们推荐使用下面一系列工厂函数来创建操作，防止直接操作参数导致的未知后果。
    """
    type: OperationType  #: :meta private:
    arg0: int = -1  #: :meta private:
    arg1: int = -1  #: :meta private:

    def dump(self) -> str:
        """
        生成操作的字符串形式。这个格式和游戏文档中的吻合，可以直接与评测机交换。

        :return:
        """
        res = str(self.type.value)
        if self.arg0 >= 0:
            res += " " + str(self.arg0)
        if self.arg1 >= 0:
            res += " " + str(self.arg1)
        return res


def build_tower_op(coord: Coord) -> Operation:
    """
    创建新建防御塔操作

    :param coord: 指定的建造位置
    :return: 创建的操作对象
    """
    return Operation(OperationType.BUILD_TOWER, coord.x, coord.y)


def upgrade_tower_op(id: int, type: TowerType) -> Operation:
    """
    创建升级防御塔操作

    :param id: 需要升级的防御塔的ID编号
    :param type: 要升级到的防御塔类型
    :return: 创建的操作对象
    """
    return Operation(OperationType.UPGRADE_TOWER, id, type.value)


def downgrade_tower_op(id: int) -> Operation:
    """
    创建降级防御塔操作。对BASIC防御塔进行降级即为拆除。

    :param id: 要降级/拆除对防御塔ID编号
    :return: 创建的操作对象
    """
    return Operation(OperationType.DOWNGRADE_TOWER, id)


def deploy_super_weapon_op(type: SuperWeaponType, coord: Coord) -> Operation:
    """
    创建部署超级武器的操作。

    :param type: 部署的超级武器类型
    :param coord: 部署的坐标
    :return: 创建的操作对象
    """
    type_to_op = [
        OperationType.DEPLOY_LIGHTNING_STORM,
        OperationType.DEPLOY_EMP_BLASTER,
        OperationType.DEPLOY_DEFLECTORS,
        OperationType.DEPLOY_EMERGENCY_EVASION,
    ]
    return Operation(type_to_op[type.value - 1], coord.x, coord.y)


def upgrade_generate_speed_op() -> Operation:
    """
    创建升级蚂蚁生成速度的操作

    :return: 创建的操作对象
    """
    return Operation(OperationType.UPGRADE_GENERATE_SPEED)


def upgrade_ant_maxhp_op() -> Operation:
    """
    创建升级蚂蚁最大生命值的操作

    :return: 创建的操作对象
    """
    return Operation(OperationType.UPGRADE_ANT_MAXHP)


def read_enemy_operations() -> list[Operation]:
    """
    读取对手的操作列表

    :return: 对手的操作列表
    """

    def read_operation() -> Operation:
        parts = _read_line_of_int()
        op_type = OperationType(parts[0])
        if (
                op_type == OperationType.UPGRADE_GENERATE_SPEED
                or op_type == OperationType.UPGRADE_ANT_MAXHP
        ):
            return Operation(op_type)
        if op_type == OperationType.DOWNGRADE_TOWER:
            return Operation(op_type, parts[1])
        return Operation(op_type, parts[1], parts[2])

    return _read_list(read_operation)


def write_our_operation(ops: list[Operation]) -> None:
    """
    向评测机输出我方的操作列表

    :param ops: 我方的操作列表
    """
    msg = str(len(ops)) + "\n"
    for op in ops:
        msg += op.dump() + "\n"
    write_to_judger(msg)


@dataclass
class RoundInfo:
    """每回合结算后，游戏逻辑向双方发送的回合局面信息。"""

    round: int  #: 当前游戏回合，从0开始计数。
    towers: list[Tower]  #: 当前所有玩家的防御塔列表。
    ants: list[Ant]  #: 当前所有存活蚂蚁的列表。注意，这个列表中的蚂蚁并不包含路径信息。
    coin: Tuple[int, int]  #: 当前双方玩家的金币数量。按下标顺序分别为先手/后手玩家的金币。
    hp: Tuple[int, int]  #: 当前双方玩家的大本营剩余血量。按下标顺序分别为先手/后手玩家的血量。


def read_round_info() -> RoundInfo:
    def read_one_int() -> int:
        return int(input())

    def read_two_ints() -> Tuple[int, int]:
        parts = _read_line_of_int()
        return parts[0], parts[1]

    def read_tower() -> Tower:
        parts = _read_line_of_int()
        return Tower(parts[0], parts[1], Coord(parts[2], parts[3]), parts[4], parts[5])

    def read_ant() -> Ant:
        parts = _read_line_of_int()
        return Ant(
            parts[0],
            parts[1],
            parts[4],
            Ant.maxhp_of_level(parts[5]),
            Coord(parts[2], parts[3]),
            parts[5],
            parts[6],
            0,
            parts[7],
        )

    return RoundInfo(
        read_one_int(),
        _read_list(read_tower),
        _read_list(read_ant),
        read_two_ints(),
        read_two_ints(),
    )
