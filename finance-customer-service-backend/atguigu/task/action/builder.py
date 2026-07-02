import importlib
import inspect
import pkgutil

from atguigu.task.action.base import Action
from atguigu.task.action.buitin.listener import ActionListener
from atguigu.task.action.buitin.response import ActionResponse
from atguigu.task.action.registry import ActionRegistry
from atguigu.task.action.runner import ActionRunner


def build_action_runner() -> ActionRunner:
    action_registry = ActionRegistry()

    # 往action_registry中注册
    action_runner = ActionRunner(action_registry)

    # 注册内置的Action
    register_builtin_actions(action_runner)

    # 注册自定义的Action
    register_custom_actions(action_runner)

    return action_runner


def register_builtin_actions(action_runner: ActionRunner):
    action_runner.registry.register(ActionResponse())
    action_runner.registry.register(ActionListener())


def register_custom_actions(action_runner: ActionRunner):
    package = importlib.import_module("atguigu.task.action.customer")

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."):
        if is_pkg:
            continue
        module = importlib.import_module(module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, Action) or obj is Action:
                continue
            if obj.__module__ != module.__name__:
                continue
            action_runner.registry.register(obj())


if __name__ == '__main__':
    runner = build_action_runner()
    print(runner.registry)
