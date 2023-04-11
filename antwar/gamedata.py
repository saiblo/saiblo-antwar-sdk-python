from dataclasses import dataclass, field
from enum import IntEnum

from .coord import Coord


def init_hp() -> int:
    """初始主基地血量，设置为50"""
    return 50


def init_coin() -> int:
    """初始金币，设置为50"""
    return 50


class AntState(IntEnum):
    """描述蚂蚁状态"""

    ALIVE = 0  #: 蚂蚁正常运行
    SUCCESS = 1  #: 蚂蚁成功攻入对方大本营
    FAIL = 2  #: 蚂蚁血量耗尽，遗憾离场
    TOO_OLD = 3  #: 蚂蚁年龄过大，自动消退
    FROZEN = 4  #: 蚂蚁被冰冻塔攻击，停止行动一回合


@dataclass
class Ant:
    """蚂蚁！"""

    id: int  #: 蚂蚁ID编号
    player: int  #: 归属玩家
    hp: int  #: 当前血量
    maxhp: int  #: 最大血量
    coord: Coord  #: 当前坐标
    level: int  #: 蚂蚁血量等级
    age: int  #: 蚂蚁年龄
    evasion_count: int  #: 蚂蚁拥有的“紧急回避”次数
    state: AntState  #: 蚂蚁状态，参见 :class:`.AntState`
    path: list[Coord] = field(default_factory=list)  #: 蚂蚁走过的路径点，注意包含初始坐标和当前坐标

    @staticmethod
    def upgrade_cost(level: int) -> int:
        """大本营升级所需要的金币。两条升级线路需要的金币相同。因为都是与蚂蚁直接相关因此放在这里。"""
        return [200, 250][level]

    @staticmethod
    def maxhp_of_level(level: int) -> int:
        """等级对应的最大血量"""
        return [10, 25, 50][level]

    @staticmethod
    def coin_of_level(level: int) -> int:
        """最大血量等级对应的击败后获得的金币数"""
        return [3, 5, 7][level]

    @staticmethod
    def gen_speed_of_level(level: int) -> int:
        """等级对应的蚂蚁生产速度，或者更确切的说，应该叫间隔。会在回合数被间隔整除的时机生成蚂蚁。"""
        return [4, 2, 1][level]

    @staticmethod
    def max_age() -> int:
        """蚂蚁的最大年龄，设置为32"""
        return 32


class TowerType(IntEnum):
    """表示防御塔类型的枚举。各个枚举名和TypeID与游戏文档中的描述一致，具体数值参见游戏文档。"""

    BASIC = 0
    HEAVY = 1
    HEAVY_PLUS = 11
    ICE = 12
    CANNON = 13
    QUICK = 2
    QUICK_PLUS = 21
    DOUBLE = 22
    SNIPER = 23
    MORTAR = 3
    MORTAR_PLUS = 31
    PULSE = 32
    MISSILE = 33


def can_tower_upgrade_to(t0: TowerType, t1: TowerType) -> bool:
    """判断``t0``防御塔能否升级为``t1``防御塔"""
    return t1 != TowerType.BASIC and t0.value == t1.value // 10


@dataclass
class TowerConfig:
    """防御塔相关数值配置"""
    damage: int  #: 伤害值
    interval: int  #: 攻击间隔
    range: int  #: 攻击范围
    aoe: int  #: 范围攻击标志


@dataclass
class Tower:
    """防御塔"""

    id: int  #: 防御塔ID编号
    player: int  #: 归属玩家
    coord: Coord  #: 防御塔坐标
    type: TowerType  #: 防御塔的类型，参见 :class:`.TowerType`
    cd: int  #: 防御塔CD。当CD为0时，即为冷却完毕，可以攻击。

    def damage(self) -> int:
        """防御塔的伤害数值"""
        return Tower.config_of_type(self.type).damage

    def interval(self) -> int:
        """防御塔的攻击间隔"""
        return Tower.config_of_type(self.type).interval

    def reset_cd(self) -> None:
        """重新设置防御塔CD为攻击间隔"""
        self.cd = self.interval()

    def range(self) -> int:
        """防御塔的攻击范围"""
        return Tower.config_of_type(self.type).range

    def aoe(self) -> int:
        """防御塔是否为范围伤害，或范围伤害的半径。"""
        return Tower.config_of_type(self.type).aoe

    @staticmethod
    def config_of_type(ttype: TowerType) -> TowerConfig:
        """获取对应类型的防御塔的数值配置"""
        config_map = {
            TowerType.BASIC: TowerConfig(5, 2, 2, 0),
            TowerType.HEAVY: TowerConfig(20, 2, 2, 0),
            TowerType.HEAVY_PLUS: TowerConfig(35, 2, 3, 0),
            TowerType.ICE: TowerConfig(15, 2, 2, 0),
            TowerType.CANNON: TowerConfig(50, 3, 3, 0),
            TowerType.QUICK: TowerConfig(6, 1, 3, 0),
            TowerType.QUICK_PLUS: TowerConfig(8, 1, 3, 0),
            TowerType.DOUBLE: TowerConfig(7, 1, 4, 0),
            TowerType.SNIPER: TowerConfig(15, 2, 6, 0),
            TowerType.MORTAR: TowerConfig(16, 4, 3, 1),
            TowerType.MORTAR_PLUS: TowerConfig(35, 4, 4, 1),
            TowerType.PULSE: TowerConfig(30, 3, 2, 2),
            TowerType.MISSILE: TowerConfig(45, 6, 5, 2),
        }
        return config_map[ttype]


class SuperWeaponType(IntEnum):
    """超级武器的类型枚举"""

    LIGHTNING_STORM = 1  #: 闪电风暴
    EMP_BLASTER = 2  #: EMP轰炸
    DEFLECTORS = 3  #: 重力偏射盾
    EMERGENCY_EVASION = 4  #: 紧急回避装置


@dataclass
class SuperWeaponConfig:
    """超级武器的相关数值配置"""
    cost: int  #: 使用一次所需金币
    cd: int  #: 冷却时间
    duration: int  #: 持续时间
    range: int  #: 影响范围


@dataclass
class SuperWeapon:
    """超级武器"""

    player: int  #: 所属玩家
    type: SuperWeaponType  #: 超级武器类型，参见 :class:`.SuperWeaponType`
    coord: Coord  #: 部署坐标
    duration: int = 0  #: 剩余持续时间，为0表示影响结束

    def init_duration(self):
        """将持续时间重设为类型所规定的初始持续时间"""
        self.duration = SuperWeapon.config_of_type(self.type).duration

    def cost(self) -> int:
        """部署改类型超级武器所需的金币"""
        return SuperWeapon.config_of_type(self.type).cost

    def cd(self) -> int:
        """改类型超级武器的冷却时间"""
        return SuperWeapon.config_of_type(self.type).cd

    def range(self) -> int:
        """改类型超级武器的作用范围"""
        return SuperWeapon.config_of_type(self.type).range

    @staticmethod
    def config_of_type(swtype: SuperWeaponType) -> SuperWeaponConfig:
        """获取对应类型超级武器的数值配置"""
        config_map = {
            SuperWeaponType.LIGHTNING_STORM: SuperWeaponConfig(150, 100, 20, 3),
            SuperWeaponType.EMP_BLASTER: SuperWeaponConfig(150, 100, 20, 3),
            SuperWeaponType.DEFLECTORS: SuperWeaponConfig(100, 50, 10, 3),
            SuperWeaponType.EMERGENCY_EVASION: SuperWeaponConfig(100, 50, 2, 3),
        }
        return config_map[swtype]
