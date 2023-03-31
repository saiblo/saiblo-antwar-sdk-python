# pylint: disable=invalid-name, missing-module-docstring, missing-class-docstring, too-few-public-methods

from dataclasses import dataclass


@dataclass(unsafe_hash=True)
class Coord:
    """描述地图坐标"""
    x: int
    y: int

    def __add__(self, other):
        return Coord(self.x + other.x, self.y + other.y)


def headquarter_coord(player: int) -> Coord:
    """获取对应玩家的大本营位置"""
    return [Coord(2, 9), Coord(16, 9)][player]


_highland_map = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 2, 2, 0, 1, 0, 0, 0, 2, 0, 0, 0, 1, 0, 2, 2, 0, 0],
    [0, 0, 0, 2, 0, 0, 2, 2, 0, 2, 0, 2, 2, 0, 0, 2, 0, 0, 0],
    [0, 2, 2, 0, 2, 0, 0, 2, 0, 2, 0, 2, 0, 0, 2, 0, 2, 2, 0],
    [0, 2, 0, 0, 0, 2, 0, 0, 2, 0, 2, 0, 0, 2, 0, 0, 0, 2, 0],
    [0, 0, 2, 0, 2, 0, 0, 2, 0, 0, 0, 2, 0, 0, 2, 0, 2, 0, 0],
    [0, 1, 3, 0, 3, 1, 0, 1, 0, 1, 0, 1, 0, 1, 3, 0, 3, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0],
    [0, 3, 3, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 3, 3, 0],
    [0, 3, 0, 0, 0, 0, 3, 3, 0, 3, 0, 3, 3, 0, 0, 0, 0, 3, 0],
    [0, 0, 3, 3, 0, 0, 0, 3, 0, 3, 0, 3, 0, 0, 0, 3, 3, 0, 0],
    [0, 0, 0, 3, 0, 1, 1, 0, 0, 3, 0, 0, 1, 1, 0, 3, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]


def is_in_map(coord: Coord) -> bool:
    """判断是否在整个地图范围之内"""
    return distance(coord, Coord(9, 9)) <= 9


def is_ant_can_go(coord: Coord) -> bool:
    """判断是否为蚂蚁可以移动的区域"""
    return is_in_map(coord) and _highland_map[coord.x][coord.y] == 0


def is_highland(coord: Coord) -> bool:
    """判断是否为高台，也即地图内蚂蚁不能移动到的区域"""
    return is_in_map(coord) and _highland_map[coord.x][coord.y] != 0


def is_player_highland(coord: Coord, player: int) -> bool:
    """判断是否为某位玩家的高台。玩家只能在自己的高台上建造防御塔。"""
    return is_in_map(coord) and _highland_map[coord.x][coord.y] == player + 2


def distance(c0: Coord, c1: Coord) -> int:
    """计算两个坐标之间的距离"""
    def to_axial(c: Coord) -> Coord:
        return Coord(c.y, c.x - (c.y + (c.y & 1)) // 2)

    def axial_distance(c0: Coord, c1: Coord) -> int:
        return (
                abs(c0.x - c1.x) + abs(c0.x + c0.y - c1.x - c1.y) + abs(c0.y - c1.y)
        ) // 2

    return axial_distance(to_axial(c0), to_axial(c1))


_neighbor_delta = [
    [[0, 1], [-1, 0], [0, -1], [1, -1], [1, 0], [1, 1]],
    [[-1, 1], [-1, 0], [-1, -1], [0, -1], [1, 0], [0, 1]],
]


def neighbor(coord: Coord, direction: int) -> Coord:
    """计算对应方向的相邻坐标。从0到5分别是：右上、上、左上、左下、下、右下。"""
    delta = _neighbor_delta[coord.y % 2][direction]
    return coord + Coord(delta[0], delta[1])
