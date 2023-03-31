User Guide: ANTWar-PythonSDK: A Top-Down Approach
=====================================================

使用 ``run_antwar_ai``
------------------------------------------------------

.. code-block:: python
    :linenos:

    from antwar.controller import run_antwar_ai
    from antwar.gamestate import GameState
    from antwar.protocol import *


    def simple_ai(my_seat: int, state: GameState) -> list[Operation]:
        tower_coord = [[Coord(6, 4), Coord(6, 14)], [Coord(11, 4), Coord(11, 14)]]

        if state.round == 0:
            return [build_tower_op(c) for c in tower_coord[my_seat]]

        return []


    run_antwar_ai(simple_ai)

上面的合法且完整的AI代码做的事情主要是在第一回合的对称位置新建两座防御塔。可以看到，玩家几乎完全不需要考虑任何与评测机通讯有关的事宜，
只需要根据提供的 :class:`.gamestate.GameState` 对象进行决策即可。 ``state`` 不仅包含了完整的游戏运行时的信息，还可以通过 ``copy.deepcopy``
等工具轻松进行拷贝，还提供了一系列“未检查”的局面操作API用于选手进行方便的搜索或者实验。

还可以利用SDK代码实现中的相关特性进行某种意义上的计划操作，如：

.. code-block:: python
    :linenos:

    def simple_ai(my_seat: int, state: GameState) -> list[Operation]:
    tower_coord = [[Coord(6, 4), Coord(6, 14)], [Coord(11, 4), Coord(11, 14)]]

    if state.round == 0:
        return [build_tower_op(c) for c in tower_coord[my_seat]]

    return [upgrade_tower_op(my_seat * 2 + i, TowerType.QUICK) for i in range(2)]

如 :meth:`antwar.controller.GameController.try_apply_our_ops` API文档所描述，
:class:`.controller.GameController` 在实施执行操作、发送操作之前都会检查操作的有效性，防止选手因为操作问题崩掉自己。
因此可以一直给SDK一系列操作，然后让SDK自己决定应用和发送的时机。

.. warning::
    但是，这种设计有潜在的隐藏选手自身程序问题的风险，因此我们非常建议不要在复杂的逻辑之中应用这种操作。

使用 :class:`.controller.GameController`
------------------------------------------------------

实际上， ``run_antwar_ai`` 就是一段可能所有用户都要写的代码的封装。如果感觉这种封装给自己的控制权太小，您完全也可以直接使用 :class:`.controller.GameController`
对游戏过程进行直接控制，如下所示：

.. code-block:: python
    :linenos:

    from antwar.controller import GameController
    from antwar.gamestate import GameState
    from antwar.protocol import *


    def simple_ai(my_seat: int, state: GameState) -> list[Operation]:
        tower_coord = [[Coord(6, 4), Coord(6, 14)], [Coord(11, 4), Coord(11, 14)]]

        if state.round == 0:
            return [build_tower_op(c) for c in tower_coord[my_seat]]

        return []


    game = GameController()
    game.init()
    while True:
        if game.my_seat == 0:
            ops = simple_ai(0, game.game_state)
            game.try_apply_our_ops(ops)
            game.finish_and_send_our_ops()

            game.read_and_apply_enemy_ops()
        else:
            game.read_and_apply_enemy_ops()

            ops = simple_ai(1, game.game_state)
            game.try_apply_our_ops(ops)
            game.finish_and_send_our_ops()

        game.next_round()


使用 :class:`.gamestate.GameState`
------------------------------------------------------

无论上面哪一种方法，都离不开最重要的 :class:`.gamestate.GameState` 。我非常建议大家阅读这个类的API文档说明，以了解可以进行的操作、
游戏的策划与实现细节，还有内置的 ``mini-replay`` 调试文件的格式和使用。

使用 :mod:`.protocol`
------------------------------------------------------

:mod:`.protocol` 提供了初始信息、回合信息和操作传输上的高层次封装，在这个层面设计AI也应该非常便捷。

直接面向通讯协议编程有时更有优势。因为可能你的AI并不需要完整的 :class:`.gamestate.GameState` 进行决策，而只依靠 :class:`.protocol.RoundInfo`
中的敌我双方的蚂蚁、防御塔分布等情况就可以展现优异表现，这时再维护完整的游戏状态显然是额外的性能损耗。

.. code-block:: python
    :linenos:

    from antwar.protocol import *

    init_info = read_init_info()
    round_info = RoundInfo(0)


    def simple_ai() -> list[Operation]:
        if round_info.round == 0:
            tower_coord = [[Coord(6, 4), Coord(6, 14)], [Coord(11, 4), Coord(11, 14)]]
            return [build_tower_op(c) for c in tower_coord[init_info.my_seat]]
        return []


    while True:
        if init_info.my_seat == 0:
            ops = simple_ai()
            write_our_operation(ops)

            enemy_ops = read_enemy_operations()

            round_info = read_round_info()
        else:
            enemy_ops = read_enemy_operations()

            ops = simple_ai()
            write_our_operation(ops)

            round_info = read_round_info()

使用 :mod:`.rawio`
------------------------------------------------------

什么？你说你什么都能写，就是不会写正数转大端序？那可能只有 :mod:`.rawio` 符合你的口味了。其中只有两个接口，一个是实现了4+N协议的
输出函数，另一个是向标准错误流输出的调试用函数，相信不需要我多说什么啦。