# pylint: disable=invalid-name, missing-module-docstring, missing-class-docstring, too-few-public-methods, no-member
from dataclasses import dataclass, field
from random import random
from typing import Optional, TypeVar
from .coord import Coord, is_player_highland, distance, neighbor, headquarter_coord
from .gamedata import (
    AntState,
    Ant,
    TowerType,
    Tower,
    SuperWeaponType,
    SuperWeapon,
    can_tower_upgrade_to,
    init_coin,
    init_hp,
)
from .pheromone import Pheromone, generate_init_pheromone
from .protocol import Operation, OperationType

T = TypeVar("T")


def _find_idx_by_id(lst: list[T], id: int) -> int:
    for i, ele in enumerate(lst):
        if ele.id == id:
            return i
    return -1


def _find_by_id(lst: list[T], id: int) -> Optional[T]:
    for ele in lst:
        if ele.id == id:
            return ele
    return None


def _find_by_coord(lst: list[T], coord: Coord) -> list[T]:
    return list(filter(lambda ele: ele.coord == coord, lst))


@dataclass
class GameState:
    """
    游戏核心状态维护类，这实际上就是一个精炼但完整的游戏逻辑程序，用它你可以做几乎任何你想做的事情。

    注意，:class:`.GameState` 和 :class:`.protocol.RoundInfo` 实际上是两套独立的系统。 :class:`.GameState` 包含了完整的逻辑
    更新代码，因此并不依赖游戏逻辑再给信息，但是仍然要注意读取回合信息，否则输入会堵塞。
    """

    round: int = 0  #: 当前回合数，从0开始。
    ants: list[Ant] = field(default_factory=list)  #: 全部存活的蚂蚁列表
    towers: list[Tower] = field(default_factory=list)  #: 全部防御塔列表
    coin: list[int] = field(default_factory=lambda: [init_coin() for p in range(2)])  #: 双方剩余金币
    hp: list[int] = field(default_factory=lambda: [init_hp() for p in range(2)])  #: 双方大本营剩余血量
    active_super_weapon: list[SuperWeapon] = field(default_factory=list)  #: 全部生效中的超级武器列表
    super_weapon_cd: list[list[int]] = field(default_factory=lambda: [[0, 0, 0, 0], [0, 0, 0, 0]])
    """双方超级武器冷却时间。可以使用 :class:`.gamedata.SuperWeaponType` 索引： ``super_weapon_cd[player][type.value - 1]`` """
    phero: list[Pheromone] = field(default_factory=lambda: [Pheromone(), Pheromone()])  #: 双方信息素
    gen_speed_lv: list[int] = field(default_factory=lambda: [0, 0])  #: 双方蚂蚁生产速度等级
    ant_maxhp_lv: list[int] = field(default_factory=lambda: [0, 0])  #: 双方蚂蚁最大血量等级

    next_ant_id: int = 0  #: 下一个蚂蚁的ID标号。双方共用一个编号序列。
    next_tower_id: int = 0  #: 下一个防御塔的ID标号。双方共用一个编号序列。

    __mini_replay_name: str = f"mini-replay-{int(random() * 10000)}.txt"

    def init_with_seed(self, seed: int) -> None:
        """初始化双方信息素"""
        p0, p1 = generate_init_pheromone(seed)
        self.phero = [p0, p1]

    def ant_idx_of_id(self, id: int) -> int:
        """根据蚂蚁ID编号获取在``ants``数组中的位置。若没有找到，返回-1"""
        return _find_idx_by_id(self.ants, id)

    def ant_of_id(self, id: int) -> Optional[Ant]:
        """根据蚂蚁ID编号获取 :class:`.gamedata.Ant` 对象。若没有找到，返回``None`` """
        return _find_by_id(self.ants, id)

    def ant_at(self, coord: Coord) -> list[Ant]:
        """获取指定位置的蚂蚁列表。双方蚂蚁允许重叠在同一位置。若没有找到，返回空列表。"""
        return _find_by_coord(self.ants, coord)

    def tower_idx_of_id(self, id: int) -> int:
        """根据防御塔ID编号获取在``towers``数组中的位置。若没有找到，返回-1"""
        return _find_idx_by_id(self.towers, id)

    def tower_of_id(self, id: int) -> Optional[Tower]:
        """根据防御塔ID编号获取 :class:`.gamedata.Tower` 对象。若没有找到，返回``None`` """
        return _find_by_id(self.towers, id)

    def tower_at(self, coord: Coord) -> Optional[Tower]:
        """获取指定位置的防御塔。若没有找到，返回 ``None`` """
        lst = _find_by_coord(self.towers, coord)
        if len(lst) > 0:
            return lst[0]
        return None

    def build_tower(self, player: int, coord: Coord) -> Optional[Tower]:
        """建造防御塔。仅对建造位置是否为己方高台进行检查。不检查/不处理金币、防御塔重叠等其他约束。"""
        if not is_player_highland(coord, player):
            return None
        t = Tower(self.next_tower_id, player, coord, TowerType.BASIC, 0)
        t.reset_cd()
        self.towers.append(t)
        self.next_tower_id += 1
        return t

    def upgrade_tower(self, id: int, ttype: TowerType) -> Optional[Tower]:
        """升级防御塔。仅对是否存在对应id的防御塔和升级路线做检查。不检查/不处理金币、防御塔重叠等其他约束。"""
        t = self.tower_of_id(id)
        if t is None:
            return None
        if not can_tower_upgrade_to(t.type, ttype):
            return None
        t.type = ttype
        t.reset_cd()
        return t

    def downgrade_tower(self, id: int) -> Optional[Tower]:
        """降级/拆除防御塔。仅对是否存在对应id的防御塔做检查。不检查/不处理金币、防御塔重叠等其他约束。"""
        t = self.tower_of_id(id)
        if t is None:
            return None
        if t.type == TowerType.BASIC:
            self.towers.pop(self.tower_idx_of_id(id))
        else:
            t.type = TowerType(t.type // 10)
            t.reset_cd()
        return t

    def build_tower_cost(self, player: int) -> int:
        """计算玩家建造防御塔的花费，应为 :math:`15\times 2^k` ，其中 :math:`k` 为该玩家已有防御塔的数量。"""
        exist_tower_count = len(list(filter(lambda t: t.player == player, self.towers)))
        return 15 * (2 ** exist_tower_count)

    def upgrade_tower_cost(self, ttype: TowerType) -> int:
        """升级到 ``ttype`` 所需的金币"""
        if ttype.value > 10:
            return 200
        if ttype.value > 0:
            return 60
        return -1

    def downgrade_tower_income(self, id: int) -> int:
        """降级/拆除所返还的金币。等于升级/建造所花价钱的80%。"""
        t = self.tower_of_id(id)
        if t is None:
            return -1
        if t.type.value > 10:
            return 160
        if t.type.value > 0:
            return 48
        if t.type.value == 0:
            return int(self.build_tower_cost(t.player) * 0.4)

    def upgrade_generate_speed(self, player: int) -> bool:
        """升级对应玩家的蚂蚁生成速度。不检查/处理金币约束，仅有最高等级限制。"""
        if self.gen_speed_lv[player] >= 2:
            return False
        self.gen_speed_lv[player] += 1
        return True

    def upgrade_ant_maxhp(self, player: int) -> bool:
        """升级对应玩家的蚂蚁最大血量。不检查/处理金币约束，仅有最高等级限制。"""
        if self.ant_maxhp_lv[player] >= 2:
            return False
        self.ant_maxhp_lv[player] += 1
        return True

    def deploy_super_weapon(
            self, player: int, coord: Coord, swtype: SuperWeaponType
    ) -> bool:
        """直接在指定位置部署超级武器。不检查/处理金币、冷却时间约束。"""
        sw = SuperWeapon(player, swtype, coord)
        sw.init_duration()
        if swtype == SuperWeaponType.EMERGENCY_EVASION:
            for ant in filter(
                    lambda ant: ant.player == player
                                and distance(ant.coord, coord) <= sw.range(),
                    self.ants,
            ):
                ant.evasion_count += sw.duration
        else:
            self.active_super_weapon.append(sw)
        return True

    def check_in_emp_range(self, player: int, coord: Coord) -> bool:
        """检查某一坐标是否处在敌方EMP影响范围之内。"""
        for sw in self.active_super_weapon:
            if (
                    sw.player != player
                    and sw.type == SuperWeaponType.EMP_BLASTER
                    and distance(coord, sw.coord) <= sw.range()
            ):
                return True
        return False

    def set_coin(self, player: int, new_coin: int) -> None:
        """直接设置指定玩家的金币数量"""
        self.coin[player] = new_coin

    def update_coin(self, player: int, delta: int) -> None:
        """更新指定玩家的金币数量"""
        self.coin[player] += delta

    def set_hp(self, player: int, new_hp: int) -> None:
        """直接设置指定玩家的主基地血量"""
        self.hp[player] = new_hp

    def update_hp(self, player: int, delta: int) -> None:
        """更新指定玩家的主基地血量"""
        self.hp[player] += delta

    def pheromone_decay(self) -> None:
        """对双方信息素做全局衰减"""
        for p in self.phero:
            p.decay()

    def is_operation_valid(self, player: int, op: Operation) -> bool:
        """检查给定操作是否有效"""
        return self.apply_operation(player, op, True)

    def apply_operation(
            self, player: int, op: Operation, dry_run: bool = False
    ) -> bool:
        """
        用指定玩家的身份执行给定操作

        :param player: 执行操作的玩家
        :param op: 需要执行的操作
        :param dry_run: 如果为``True``，那么只检查有效性而并不会实际影响内部状态。
        :return: 操作是否有效
        """
        c = Coord(op.arg0, op.arg1)
        if op.type == OperationType.BUILD_TOWER:
            cost = self.build_tower_cost(player)
            valid = (
                    self.coin[player] >= cost
                    and is_player_highland(c, player)
                    and self.tower_at(c) is None
                    and not self.check_in_emp_range(player, c)
            )
            if valid and not dry_run:
                self.build_tower(player, c)
                self.coin[player] -= cost
            return valid
        if op.type == OperationType.UPGRADE_TOWER:
            t = self.tower_of_id(op.arg0)
            newtype = TowerType(op.arg1)
            cost = self.upgrade_tower_cost(newtype)
            valid = (
                    t is not None
                    and t.player == player
                    and self.coin[player] >= cost
                    and not self.check_in_emp_range(player, c)
                    and can_tower_upgrade_to(t.type, newtype)
            )
            if valid and not dry_run:
                self.upgrade_tower(op.arg0, TowerType(op.arg1))
                self.coin[player] -= cost
            return valid
        if op.type == OperationType.DOWNGRADE_TOWER:
            t = self.tower_of_id(op.arg0)
            valid = (
                    t is not None
                    and t.player == player
                    and not self.check_in_emp_range(player, c)
            )
            if valid and not dry_run:
                self.downgrade_tower(op.arg0)
                self.coin[player] += self.downgrade_tower_income(op.arg0)
            return valid

        def check_and_deploy(player: int, swtype: SuperWeaponType) -> bool:
            cost = SuperWeapon.config_of_type(swtype).cost
            if (
                    self.coin[player] >= cost
                    and self.super_weapon_cd[player][swtype.value - 1] == 0
            ):
                if not dry_run:
                    self.deploy_super_weapon(player, c, swtype)
                    self.coin[player] -= cost
                    self.super_weapon_cd[player][
                        swtype.value - 1
                        ] = SuperWeapon.config_of_type(swtype).cd
                return True
            return False

        if op.type == OperationType.DEPLOY_LIGHTNING_STORM:
            return check_and_deploy(player, SuperWeaponType.LIGHTNING_STORM)
        if op.type == OperationType.DEPLOY_EMP_BLASTER:
            return check_and_deploy(player, SuperWeaponType.EMP_BLASTER)
        if op.type == OperationType.DEPLOY_DEFLECTORS:
            return check_and_deploy(player, SuperWeaponType.DEFLECTORS)
        if op.type == OperationType.DEPLOY_EMERGENCY_EVASION:
            return check_and_deploy(player, SuperWeaponType.EMERGENCY_EVASION)

        def check_and_upgrade_hq(player: int, level_array: list[int]) -> bool:
            cost = Ant.upgrade_cost(level_array[player])
            if self.coin[player] >= cost:
                if not dry_run:
                    level_array[player] += 1
                    self.coin[player] -= cost
                return True
            return False

        if op.type == OperationType.UPGRADE_GENERATE_SPEED:
            return check_and_upgrade_hq(player, self.gen_speed_lv)
        if op.type == OperationType.UPGRADE_ANT_MAXHP:
            return check_and_upgrade_hq(player, self.ant_maxhp_lv)

        return False

    def search_attack_target(
            self, player: int, coord: Coord, trange: int, skip: int = -1
    ) -> Optional[Ant]:
        """
        防御塔的核心索敌函数。索敌逻辑为：锁定在防御塔攻击范围内的、血量大于0的敌方蚂蚁中，距离防御塔自身最近的蚂蚁。
        如果有多只蚂蚁距离相等，那么选择ID最小的。

        :param player: 正在索敌的防御塔归属的顽疾
        :param coord: 正在索敌的防御塔的位置
        :param trange: 正在索敌的防御塔的攻击范围
        :param skip: 是否跳过特定编号的蚂蚁。用于``Double``防御塔必须一次锁定两个不同的目标。默认为-1即并不跳过任何蚂蚁。
        :return: 返回锁定的目标蚂蚁。若攻击范围内没有可用目标，则返回``None``。
        """
        target: Optional[Ant] = None
        min_dist = 0
        for ant in self.ants:
            dist = distance(coord, ant.coord)
            if (
                    ant.player != player
                    and dist <= trange
                    and ant.id != skip
                    and ant.hp > 0
            ):
                if (
                        target is None
                        or dist < min_dist
                        or (dist == min_dist and ant.id < target.id)
                ):
                    target = ant
                    min_dist = dist
        return target

    def _try_attack_ant(self, ant: Ant, damage: int):
        if ant.evasion_count > 0:
            ant.evasion_count -= 1
        else:
            if damage < ant.maxhp / 2 and any(
                    map(
                        lambda sw: sw.type == SuperWeaponType.DEFLECTORS
                                   and sw.player == ant.player
                                   and distance(sw.coord, ant.coord) <= sw.range(),
                        self.active_super_weapon,
                    )
            ):
                damage = 0
            ant.hp -= damage
            if ant.hp <= 0:
                ant.state = AntState.FAIL
                self.coin[1 - ant.player] += Ant.coin_of_level(ant.level)

    def _aoe_attack_ant(self, player: int, center: Coord, radius: int, damage: int):
        for ant in filter(
                lambda ant: ant.player != player
                            and ant.hp > 0
                            and distance(ant.coord, center) <= radius,
                self.ants,
        ):
            self._try_attack_ant(ant, damage)

    def simulate_next_round(self) -> None:
        """
        模拟一个回合的结算过程。结算顺序为：

        1. 闪电风暴攻击
        2. 各个防御塔按照ID顺序攻击
        3. 标记老死的蚂蚁
        4. 所有存活且未被冰冻的蚂蚁进行移动
        5. 根据这回合蚂蚁的死亡、成功情况，进行信息素更新
        6. 尝试生成新蚂蚁
        7. 最后清理工作：
            1. 移除死亡的蚂蚁
            2. 解除蚂蚁冰冻状态
            3. 更新回合数和金币数
            4. 检查各个超级武器是否还在生效
        """

        # 1. lightning storm
        for lightning in filter(
                lambda sw: sw.type == SuperWeaponType.LIGHTNING_STORM,
                self.active_super_weapon,
        ):
            for ant in filter(
                    lambda ant: ant.hp > 0 and ant.player != lightning.player
                                and distance(ant.coord, lightning.coord) <= lightning.range(),
                    self.ants,
            ):
                ant.hp -= 100
                self.coin[1 - ant.player] += Ant.coin_of_level(ant.level)

        # 2. tower attack
        for tower in self.towers:
            if self.check_in_emp_range(tower.player, tower.coord):
                continue
            if tower.cd > 0:
                tower.cd -= 1
            if tower.cd > 0:
                continue
            target = self.search_attack_target(tower.player, tower.coord, tower.range())
            if target is None:
                continue
            tower.reset_cd()
            # QUICK_PLUS
            if tower.type == TowerType.QUICK_PLUS:
                self._try_attack_ant(target, tower.damage())
                target = self.search_attack_target(
                    tower.player, tower.coord, tower.range()
                )
                if target is not None:
                    self._try_attack_ant(target, tower.damage())
            # DOUBLE
            elif tower.type == TowerType.DOUBLE:
                self._try_attack_ant(target, tower.damage())
                target = self.search_attack_target(
                    tower.player, tower.coord, tower.range(), target.id
                )
                if target is not None:
                    self._try_attack_ant(target, tower.damage())
            # PULSE
            elif tower.type == TowerType.PULSE:
                self._aoe_attack_ant(
                    tower.player, tower.coord, tower.range(), tower.damage()
                )
            # NORMAL
            elif tower.aoe() == 0:
                # ICE
                if tower.type == TowerType.ICE:
                    target.state = AntState.FROZEN
                self._try_attack_ant(target, tower.damage())
            # AOE
            else:
                self._aoe_attack_ant(
                    tower.player, target.coord, tower.aoe(), tower.damage()
                )

        # 3. filter too-old
        for too_old_ant in filter(
                lambda ant: ant.hp > 0 and ant.age > Ant.max_age(), self.ants
        ):
            too_old_ant.state = AntState.TOO_OLD

        # 4. ant move
        for ant in filter(lambda ant: ant.state == AntState.ALIVE, self.ants):
            direction = self.phero[ant.player].next_move_direction(ant)
            new_coord = neighbor(ant.coord, direction)
            ant.coord = new_coord
            ant.path.append(new_coord)
            if new_coord == headquarter_coord(1 - ant.player):
                ant.state = AntState.SUCCESS
                self.hp[1 - ant.player] -= 1

        # 5. pheromone update
        for p in self.phero:
            p.decay()
        for ant in self.ants:
            if ant.state == AntState.FAIL:
                self.phero[ant.player].modify_by_failed_ant(ant)
            if ant.state == AntState.TOO_OLD:
                self.phero[ant.player].modify_by_too_old_ant(ant)
            if ant.state == AntState.SUCCESS:
                self.phero[ant.player].modify_by_success_ant(ant)

        # 6. generate new ant
        for player in range(2):
            if self.round % Ant.gen_speed_of_level(self.gen_speed_lv[player]) == 0:
                self.ants.append(
                    Ant(
                        self.next_ant_id,
                        player,
                        Ant.maxhp_of_level(self.ant_maxhp_lv[player]),
                        Ant.maxhp_of_level(self.ant_maxhp_lv[player]),
                        headquarter_coord(player),
                        self.ant_maxhp_lv[player],
                        0,
                        0,
                        AntState.ALIVE,
                        [headquarter_coord(player)],
                    )
                )
                self.next_ant_id += 1

        # 7. final update
        self.round += 1
        self.coin[0] += 1
        self.coin[1] += 1
        self.dump_mini_replay()

        for ant in filter(lambda ant: ant.state == AntState.FROZEN, self.ants):
            ant.state = AntState.ALIVE
        self.ants = list(filter(lambda ant: ant.state == AntState.ALIVE, self.ants))
        for ant in self.ants:
            ant.age += 1

        for sw in self.active_super_weapon:
            sw.duration -= 1
        self.active_super_weapon = list(
            filter(lambda sw: sw.duration > 0, self.active_super_weapon)
        )

    def dump_mini_replay(self) -> None:
        """输出“迷你回放文件”所用的接口。可以用来辅助本地调试工作。"""
        with open(self.__mini_replay_name, "a", encoding="utf-8") as f:
            def fprint(*args, **kwargs):
                print(*args, file=f, **kwargs)

            fprint(self.round)
            fprint(len(self.towers))
            for tower in self.towers:
                fprint(
                    f"{tower.id} {tower.player} {tower.coord.x} {tower.coord.y} {tower.type.value} {tower.cd}"
                )
            fprint(len(self.ants))
            for ant in self.ants:
                fprint(
                    f"{ant.id} {ant.player} {ant.coord.x} {ant.coord.y} {ant.hp} {ant.level} {ant.age} {ant.state}"
                )
            fprint(f"{self.coin[0]} {self.coin[1]}")
            fprint(f"{self.hp[0]} {self.hp[1]}")
            for p in self.phero:
                for row in p.value:
                    fprint(" ".join(map(lambda value: f"{value:.4f}", row)))
