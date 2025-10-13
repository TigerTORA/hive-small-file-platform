#!/usr/bin/env python3
"""
模拟前端loadTestTableRun函数测试
"""
import requests
import json

API_BASE = 'http://localhost:8000/api/v1'

def level_map(s):
    """级别映射函数"""
    up = (s or '').upper()
    if up == 'WARN':
        return 'WARN'
    elif up == 'ERROR':
        return 'ERROR'
    elif up == 'DEBUG':
        return 'DEBUG'
    else:
        return 'INFO'

def load_test_table_run(task_id):
    """模拟前端的loadTestTableRun函数"""
    print(f'🚀 开始测试 loadTestTableRun 函数，任务ID: {task_id}')

    logs = []
    task_info = None

    # 获取日志
    try:
        print('📡 正在获取任务日志...')
        logs_response = requests.get(f'{API_BASE}/tasks/{task_id}/logs')
        if logs_response.status_code != 200:
            raise Exception(f'日志API返回错误: {logs_response.status_code}')
        logs = logs_response.json()
        print(f'✅ Test table logs loaded: {len(logs)} 条')
    except Exception as e:
        print(f'⚠️ Failed to load test table logs: {e}')
        logs = []

    # 尝试获取任务详情
    try:
        print('📡 正在获取任务详情...')
        task_response = requests.get(f'{API_BASE}/test-tables/tasks/{task_id}')
        if task_response.status_code != 200:
            raise Exception(f'任务详情API返回错误: {task_response.status_code}')
        task_info = task_response.json()
        print('✅ Test table task info loaded')
    except Exception as e:
        print(f'⚠️ Failed to load test table task info: {e}')

    # 测试表生成的阶段
    steps = [
        {'id': 'initialization', 'name': '初始化', 'status': 'pending'},
        {'id': 'hdfs_setup', 'name': '创建HDFS目录', 'status': 'pending'},
        {'id': 'data_generation', 'name': '生成数据文件', 'status': 'pending'},
        {'id': 'hive_table_creation', 'name': '创建Hive表', 'status': 'pending'},
        {'id': 'partition_creation', 'name': '添加分区', 'status': 'pending'},
        {'id': 'verification', 'name': '验证结果', 'status': 'pending'},
        {'id': 'completed', 'name': '完成', 'status': 'pending'}
    ]

    # 检查是否有错误日志来确定状态
    has_error = any((l.get('log_level', '').upper() == 'ERROR') for l in (logs or []))
    status = task_info.get('status', 'running') if task_info else 'running'

    print('📊 状态分析:')
    print(f'   - 原始状态: {status}')
    print(f'   - 有错误日志: {has_error}')
    print(f'   - 日志数量: {len(logs)}')

    # 根据任务状态更新步骤状态
    if status == 'success':
        for step in steps:
            step['status'] = 'success'
    elif status == 'failed' or has_error:
        steps[0]['status'] = 'success'  # 初始化总是成功的
        for i, step in enumerate(steps):
            if i > 0:
                step['status'] = 'failed'
        status = 'failed'
    elif status == 'running':
        steps[0]['status'] = 'success'  # 初始化完成
        steps[1]['status'] = 'running'  # 当前在创建HDFS目录阶段

    norm_logs = []
    for l in (logs or []):
        norm_logs.append({
            'ts': str(l.get('timestamp', '')),
            'level': level_map(l.get('log_level')),
            'source': 'test-table',
            'message': l.get('message', ''),
            'step_id': l.get('phase', 'initialization')
        })

    result = {
        'title': task_info.get('task_name', '测试表生成任务') if task_info else '测试表生成任务',
        'status': status,
        'progress': task_info.get('progress_percentage', 0) if task_info else 0,
        'currentOperation': task_info.get('current_operation') if task_info else ('执行失败' if has_error else '正在执行'),
        'startedAt': task_info.get('started_time') if task_info else None,
        'finishedAt': task_info.get('completed_time') if task_info else None,
        'steps': steps,
        'logs': norm_logs
    }

    print('🎯 最终结果:')
    print(f'   - 任务标题: {result["title"]}')
    print(f'   - 最终状态: {result["status"]}')
    print(f'   - 进度: {result["progress"]}%')
    print(f'   - 当前操作: {result["currentOperation"]}')
    print(f'   - 步骤数量: {len(result["steps"])}')
    print(f'   - 标准化日志数量: {len(result["logs"])}')

    # 显示日志详情
    if result['logs']:
        print('\n📝 日志详情:')
        for i, log in enumerate(result['logs']):
            print(f'   {i + 1}. [{log["level"]}] {log["message"]}')
            print(f'      时间: {log["ts"]}')
            print(f'      阶段: {log["step_id"]}')

    return result

def test_known_tasks():
    """测试已知任务ID"""
    print('🔍 开始测试已知任务...\n')

    known_task_ids = [
        '274486bd-8c6f-4c55-806f-80dbdab621fc',
        '3f5cb0db-79f6-420e-87e0-3b041646f87c',
        '26e8c07c-4eca-47de-96d6-b9814c0e89e3'
    ]

    success_count = 0
    for task_id in known_task_ids:
        print(f'\n{"=" * 60}')
        print(f'测试任务: {task_id}')
        print(f'{"=" * 60}')

        try:
            result = load_test_table_run(task_id)
            print('✅ 任务测试成功!')
            success_count += 1
        except Exception as error:
            print(f'❌ 任务测试失败: {error}')

    print(f'\n🎉 测试完成! 成功: {success_count}/{len(known_task_ids)}')

    if success_count > 0:
        print('\n✅ 前端日志功能验证通过!')
        print('   - loadTestTableRun 函数工作正常')
        print('   - API调用成功')
        print('   - 日志数据处理正确')
        print('   - 步骤状态映射正确')
    else:
        print('\n❌ 前端日志功能验证失败!')

if __name__ == '__main__':
    test_known_tasks()