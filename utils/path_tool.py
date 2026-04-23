import os
import sys


def get_project_root() -> str:
    """
    获取工程所在的根目录 (D:\\Flask)
    :return: 字符串根目录
    """
    current_file = os.path.abspath(__file__)
    current_dir1 = os.path.dirname(current_file)
    current_dir2 = os.path.dirname(current_dir1)
    project_root = os.path.dirname(current_dir2)
    return project_root


def get_abs_path(relative_path: str) -> str:
    """
    传递相对路径，得到绝对路径（相对于 D:\\Flask）
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)


def get_project_root1() -> str:
    """
    获取工程所在的次级根目录 (D:\\Flask\\Agent_Project)
    :return: 字符串次级根目录
    """
    current_file = os.path.abspath(__file__)
    current_dir2 = os.path.dirname(current_file)
    project_root = os.path.dirname(current_dir2)
    return project_root


def get_abs_path1(relative_path: str) -> str:
    """
    传递相对路径，得到绝对路径（相对于 D:\\Flask\\Agent_Project）
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    project_root = get_project_root1()
    return os.path.join(project_root, relative_path)


if __name__ == '__main__':
    print(f"Project root: {get_project_root()}")
    print(f"Project root1: {get_project_root1()}")
    print(f"Absolute path: {get_abs_path('config/1.txt')}")
    print(f"Absolute path1: {get_abs_path1('config/1.txt')}")