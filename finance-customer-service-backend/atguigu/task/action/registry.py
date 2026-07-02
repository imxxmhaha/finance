from atguigu.task.action.base import Action


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        self._actions[action.name] = action

    def get(self, name: str) -> Action:
        if name not in self._actions:
            raise KeyError(f"Unknown action '{name}'.")
        return self._actions[name]

    def __str__(self) -> str:
        actions = ", ".join(self._actions.keys()) if self._actions else "无"
        return f"ActionRegistry(已注册 {len(self._actions)} 个 action: [{actions}])"
