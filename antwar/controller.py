from typing import Callable

from .gamestate import GameState
from .protocol import read_init_info, Operation, write_our_operation, RoundInfo, read_round_info, read_enemy_operations


class GameController:
    """游戏控制器。可以帮助选手处理通讯与数据维护有关的繁琐操作。"""

    my_seat: int = 0  #: 您的位置。0代表您是先手，1代表您是后手。
    game_state: GameState = GameState()  #: 游戏状态，一个 :class:`.gamestate.GameState` 对象
    my_operation_list: list[Operation] = []  #: 我方未发送的操作列表

    def init(self) -> None:
        """初始化游戏：接受游戏初始化信息，并使用给定的随机种子初始化双方信息素。"""
        init_info = read_init_info()
        self.my_seat = init_info.my_seat
        self.game_state.init_with_seed(init_info.seed)

    def read_enemy_ops(self) -> list[Operation]:
        """读取敌方操作列表"""
        return read_enemy_operations()

    def apply_enemy_ops(self, ops: list[Operation]) -> bool:
        """应用敌方操作。如果返回``False``说明敌方操作不合法。"""
        for op in ops:
            if not self.game_state.apply_operation(1 - self.my_seat, op):
                return False
        return True

    def read_and_apply_enemy_ops(self) -> bool:
        """读取并应用敌方操作。如果返回``False``说明敌方操作不合法。"""
        return self.apply_enemy_ops(self.read_enemy_ops())

    def try_apply_our_op(self, op: Operation) -> bool:
        """尝试执行我方操作。如果返回``False``说明我方操作不合法。"""
        if self.game_state.apply_operation(self.my_seat, op):
            self.my_operation_list.append(op)
            return True
        return False

    def try_apply_our_ops(self, ops: list[Operation]) -> bool:
        """尝试执行我方若干哥操作。如果返回``False``说明我方操作不合法，并停止执行后面的操作。"""
        for op in ops:
            if not self.try_apply_our_op(op):
                return False
        return True

    def finish_and_send_our_ops(self) -> None:
        """结束我方操作回合，将操作列表打包发送并清空。"""
        write_our_operation(self.my_operation_list)
        self.my_operation_list = []

    def next_round(self) -> RoundInfo:
        """执行下一回合：读取回合信息，进行 :class:`.gamestate.GameState` 的模拟以维护游戏数据。"""
        round_info = read_round_info()
        self.game_state.simulate_next_round()
        return round_info


def run_antwar_ai(ai_func: Callable[[int, GameState], list[Operation]]) -> None:
    """
    执行AI。将你的决策过程封装在一个函数中，我们帮你处理各类通讯相关的繁琐事项。
    如果你不喜欢这么做，也可以直接把下面的代码复制到你的主函数中重复利用。

    :param ai_func: 你的决策函数，第一个参数为``my_seat``，第二个参数为当前的 :class:`.gamestate.GameState` 对象。
    """
    game = GameController()
    game.init()
    while True:
        if game.my_seat == 0:
            ops = ai_func(0, game.game_state)
            game.try_apply_our_ops(ops)
            game.finish_and_send_our_ops()

            game.read_and_apply_enemy_ops()
        else:
            game.read_and_apply_enemy_ops()

            ops = ai_func(1, game.game_state)
            game.try_apply_our_ops(ops)
            game.finish_and_send_our_ops()

        game.next_round()
