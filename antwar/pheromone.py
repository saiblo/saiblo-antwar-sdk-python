from .coord import Coord, headquarter_coord, neighbor, is_in_map, is_ant_can_go, distance
from .gamedata import Ant


class Pheromone:
    """
    存储、修改某一方的信息素以及相关的“蚂蚁”寻路算法。

    信息素是本游戏的核心设定，它完全控制了双方蚂蚁的行动过程。
    """


    value: list[list[float]] = []  #: 19x19的信息素数组

    @staticmethod
    def tau_base() -> float:
        """信息素基准值，设定为 :math:`\\tau_{0} = 10.0` """
        return 10.0

    @staticmethod
    def decay_rate() -> float:
        """每回合全局信息素衰减比例，设定为 :math:`\\lambda = 0.97` """
        return 0.97

    def decay(self) -> None:
        """进行全局信息素衰减: :math:`\\tau' = \\lambda\\tau + (1-\\lambda)\\tau_{0}` """
        _lambda = Pheromone.decay_rate()
        for i in range(19):
            for j in range(19):
                self.value[i][j] = _lambda * self.value[i][j] + (1 - _lambda) * Pheromone.tau_base()

    def pheromone_of_neighbors(self, coord: Coord) -> list[float]:
        """输出给定点相邻六个方向的信息素分布 :math:`\\tau_p` 。若超出地图范围则置为-10。"""
        return list(
            map(
                lambda c: self.value[c.x][c.y] if is_in_map(c) else -10.0,
                map(lambda dir: neighbor(coord, dir), range(6)),
            )
        )

    def multiplier_of_neighbors(self, coord: Coord, target: Coord) -> list[float]:
        """输出给定点周围六个方向的目标偏好修正 :math:`\\eta_p`。若向某一方向行动后里目标点更近，则置为1.25；若距离相同，置为1.00；若距离更远，置为0.75。"""
        return list(
            map(
                lambda delta_dis: [1.25, 1.00, 0.75][delta_dis + 1],
                map(
                    lambda c: distance(c, target) - distance(coord, target),
                    map(lambda dir: neighbor(coord, dir), range(6)),
                ),
            )
        )

    def next_move_direction(self, ant: Ant) -> int:
        """
        核心寻路算法。

        实际上是寻找六个方向中移动概率最大的方向，即：

        :math:`\\mathrm{argmax}_i P_i = \\mathrm{argmax}_i \\tau_i\\cdot\\eta_i\\cdot v_i`

        其中 :math:`\\tau_i` 是上面描述的信息素，:math:`\\eta_i` 是上面描述的目标偏好修正。而 :math:`v_i`描述这个方向是否可以行动，如果可以则为1，否则为0。

        :param ant: 要求下一步动作的蚂蚁
        :return: 应当行动的方向
        """
        last_pos = ant.path[-2] if len(ant.path) > 1 else ant.coord
        valid = list(
            map(
                lambda c: is_ant_can_go(c) and c != last_pos,
                map(lambda dir: neighbor(ant.coord, dir), range(6)),
            )
        )
        tau = self.pheromone_of_neighbors(ant.coord)
        eta = self.multiplier_of_neighbors(ant.coord, headquarter_coord(1 - ant.player))

        max_dir, max_p = 0, -1000
        for i in range(6):
            if valid[i]:
                p = tau[i] * eta[i]
                if p > max_p:
                    max_dir, max_p = i, p
                elif p == max_p:
                    if tau[i] > tau[max_dir]:
                        max_dir, max_p = i, p
        return max_dir

    def modify_path(self, path: list[Coord], delta: float) -> None:
        """核心信息素修改函数。实际上是对路径上所有点的信息素加上给定的差值。如果路径多次经过同一个点，只会更改一次。"""
        for coord in set(path):
            self.value[coord.x][coord.y] = max(0.0, self.value[coord.x][coord.y] + delta)

    @staticmethod
    def success_ant_gain() -> float:
        """蚂蚁攻入敌方大本营产生的收益。设定为10.0"""
        return 10.0

    def modify_by_success_ant(self, ant: Ant) -> None:
        """蚂蚁攻入敌方大本营后的更新函数，实际上是对蚂蚁的行动路径进行上面描述的增益的改动。"""
        self.modify_path(ant.path, Pheromone.success_ant_gain())

    @staticmethod
    def failed_ant_gain() -> float:
        """蚂蚁血量耗尽产生的收益。设定为-5.0"""
        return -5.0

    def modify_by_failed_ant(self, ant: Ant) -> None:
        """蚂蚁血量耗尽后的更新函数，实际上是对蚂蚁的行动路径进行上面描述的增益的改动。"""
        self.modify_path(ant.path, Pheromone.failed_ant_gain())

    @staticmethod
    def too_old_ant_gain() -> float:
        """蚂蚁年龄过大产生的收益。设定为-3.0"""
        return -3.0

    def modify_by_too_old_ant(self, ant: Ant) -> None:
        """蚂蚁年龄过大后的更新函数，实际上是对蚂蚁的行动路径进行上面描述的增益的改动。"""
        self.modify_path(ant.path, Pheromone.too_old_ant_gain())


def generate_init_pheromone(seed: int) -> tuple[Pheromone, Pheromone]:
    """规定的双方信息素初始化函数。这实际上是一个线性同余伪随机数发生器。"""

    lcg_seed = seed

    def lcg():
        nonlocal lcg_seed
        lcg_seed = (25214903917 * lcg_seed) & ((1 << 48) - 1)
        return lcg_seed

    def generate() -> Pheromone:
        p = Pheromone()
        p.value = [
            [(lcg() * pow(2, -46) + 8) for j in range(19)] for i in range(19)
        ]
        return p

    return generate(), generate()
