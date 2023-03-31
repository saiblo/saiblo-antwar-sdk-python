from antwar.controller import run_antwar_ai
from antwar.gamestate import GameState
from antwar.protocol import *


def simple_ai(my_seat: int, state: GameState) -> list[Operation]:
    tower_coord = [[Coord(6, 4), Coord(6, 14)], [Coord(11, 4), Coord(11, 14)]]

    if state.round == 0:
        return [build_tower_op(c) for c in tower_coord[my_seat]]

    return []


run_antwar_ai(simple_ai)
