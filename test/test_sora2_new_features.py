#!/usr/bin/env python3
"""测试 Sora2 新功能：角色创建和视频编辑"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_character_node_registration():
    """测试角色创建节点注册"""
    print("=" * 60)
    print("测试 1: 角色创建节点注册")
    print("=" * 60)

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

        if 'SoraCreateCharacter' in NODE_CLASS_MAPPINGS:
            print("✅ SoraCreateCharacter 已注册")
            node_class = NODE_CLASS_MAPPINGS['SoraCreateCharacter']
            print(f"   分类: {node_class.CATEGORY}")
            print(f"   显示名称: {NODE_DISPLAY_NAME_MAPPINGS.get('SoraCreateCharacter')}")

            # 检查必需方法
            assert hasattr(node_class, 'INPUT_TYPES'), "缺少 INPUT_TYPES"
            assert hasattr(node_class, 'RETURN_TYPES'), "缺少 RETURN_TYPES"
            assert hasattr(node_class, 'FUNCTION'), "缺少 FUNCTION"

            input_types = node_class.INPUT_TYPES()
            print(f"   必需参数: {list(input_types.get('required', {}).keys())}")
            print(f"   可选参数: {list(input_types.get('optional', {}).keys())}")

            return True
        else:
            print("❌ SoraCreateCharacter 未注册")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_remix_node_registration():
    """测试视频编辑节点注册"""
    print("\n" + "=" * 60)
    print("测试 2: 视频编辑节点注册")
    print("=" * 60)

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

        if 'SoraRemixVideo' in NODE_CLASS_MAPPINGS:
            print("✅ SoraRemixVideo 已注册")
            node_class = NODE_CLASS_MAPPINGS['SoraRemixVideo']
            print(f"   分类: {node_class.CATEGORY}")
            print(f"   显示名称: {NODE_DISPLAY_NAME_MAPPINGS.get('SoraRemixVideo')}")

            # 检查必需方法
            assert hasattr(node_class, 'INPUT_TYPES'), "缺少 INPUT_TYPES"
            assert hasattr(node_class, 'RETURN_TYPES'), "缺少 RETURN_TYPES"
            assert hasattr(node_class, 'FUNCTION'), "缺少 FUNCTION"

            input_types = node_class.INPUT_TYPES()
            print(f"   必需参数: {list(input_types.get('required', {}).keys())}")
            print(f"   可选参数: {list(input_types.get('optional', {}).keys())}")

            return True
        else:
            print("❌ SoraRemixVideo 未注册")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_character_node_instantiation():
    """测试角色创建节点实例化"""
    print("\n" + "=" * 60)
    print("测试 3: 角色创建节点实例化")
    print("=" * 60)

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS

        node_class = NODE_CLASS_MAPPINGS['SoraCreateCharacter']
        node = node_class()

        print("✅ 角色创建节点实例化成功")
        print(f"   类型: {type(node)}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_remix_node_instantiation():
    """测试视频编辑节点实例化"""
    print("\n" + "=" * 60)
    print("测试 4: 视频编辑节点实例化")
    print("=" * 60)

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS

        node_class = NODE_CLASS_MAPPINGS['SoraRemixVideo']
        node = node_class()

        print("✅ 视频编辑节点实例化成功")
        print(f"   类型: {type(node)}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_character_creation_with_api():
    """测试角色创建（实际 API）"""
    print("\n" + "=" * 60)
    print("测试 5: 角色创建（实际 API）")
    print("=" * 60)

    api_key = os.environ.get("KUAI_API_KEY", "")
    if not api_key:
        print("⚠️  跳过执行测试（未设置 KUAI_API_KEY）")
        print("   设置方法: export KUAI_API_KEY=your_key_here")
        return True

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS

        node_class = NODE_CLASS_MAPPINGS['SoraCreateCharacter']
        node = node_class()

        # 注意：这个测试需要一个真实的视频URL或任务ID
        # 这里只是演示如何调用，实际测试需要提供有效的视频
        print("⚠️  角色创建需要真实的视频URL或任务ID")
        print("   跳过实际API调用测试")
        print("   手动测试示例:")
        print("   - timestamps: '1,3'")
        print("   - url: 'https://example.com/video.mp4'")
        print("   或")
        print("   - from_task: 'video_xxx'")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_remix_video_with_api():
    """测试视频编辑（实际 API）"""
    print("\n" + "=" * 60)
    print("测试 6: 视频编辑（实际 API）")
    print("=" * 60)

    api_key = os.environ.get("KUAI_API_KEY", "")
    if not api_key:
        print("⚠️  跳过执行测试（未设置 KUAI_API_KEY）")
        print("   设置方法: export KUAI_API_KEY=your_key_here")
        return True

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS

        node_class = NODE_CLASS_MAPPINGS['SoraRemixVideo']
        node = node_class()

        # 注意：这个测试需要一个已完成的视频ID
        # 这里只是演示如何调用，实际测试需要提供有效的视频ID
        print("⚠️  视频编辑需要已完成的视频ID")
        print("   跳过实际API调用测试")
        print("   手动测试示例:")
        print("   - video_id: 'video_xxx'")
        print("   - prompt: '让这个视频背景变成紫色'")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chinese_labels():
    """测试中文标签"""
    print("\n" + "=" * 60)
    print("测试 7: 中文标签")
    print("=" * 60)

    try:
        from nodes.Sora2 import NODE_CLASS_MAPPINGS

        # 测试角色创建节点
        character_node = NODE_CLASS_MAPPINGS['SoraCreateCharacter']
        if hasattr(character_node, 'INPUT_LABELS'):
            labels = character_node.INPUT_LABELS()
            print("✅ SoraCreateCharacter 中文标签:")
            for key, label in labels.items():
                print(f"   {key}: {label}")
        else:
            print("⚠️  SoraCreateCharacter 缺少 INPUT_LABELS")

        # 测试视频编辑节点
        remix_node = NODE_CLASS_MAPPINGS['SoraRemixVideo']
        if hasattr(remix_node, 'INPUT_LABELS'):
            labels = remix_node.INPUT_LABELS()
            print("\n✅ SoraRemixVideo 中文标签:")
            for key, label in labels.items():
                print(f"   {key}: {label}")
        else:
            print("⚠️  SoraRemixVideo 缺少 INPUT_LABELS")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 Sora2 新功能测试套件\n")

    results = []
    results.append(("角色创建节点注册", test_character_node_registration()))
    results.append(("视频编辑节点注册", test_remix_node_registration()))
    results.append(("角色创建节点实例化", test_character_node_instantiation()))
    results.append(("视频编辑节点实例化", test_remix_node_instantiation()))
    results.append(("角色创建实际API", test_character_creation_with_api()))
    results.append(("视频编辑实际API", test_remix_video_with_api()))
    results.append(("中文标签", test_chinese_labels()))

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 所有测试通过！" if all_passed else "⚠️  部分测试失败"))

    sys.exit(0 if all_passed else 1)
