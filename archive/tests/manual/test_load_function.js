// 模拟前端loadTestTableRun函数测试
const fetch = require('node-fetch');

const API_BASE = 'http://localhost:8000/api/v1';

// 级别映射函数
function levelMap(s) {
    const up = (s || '').toUpperCase();
    return up === 'WARN' ? 'WARN' : up === 'ERROR' ? 'ERROR' : up === 'DEBUG' ? 'DEBUG' : 'INFO';
}

// 模拟前端的loadTestTableRun函数
async function loadTestTableRun(taskId) {
    console.log('🚀 开始测试 loadTestTableRun 函数，任务ID:', taskId);

    let logs = [];
    let taskInfo = null;

    try {
        // 获取日志 (模拟 tasksApi.getLogs)
        console.log('📡 正在获取任务日志...');
        const logsResponse = await fetch(`${API_BASE}/tasks/${taskId}/logs`);
        if (!logsResponse.ok) {
            throw new Error(`日志API返回错误: ${logsResponse.status}`);
        }
        logs = await logsResponse.json();
        console.log('✅ Test table logs loaded:', logs.length, '条');
    } catch (e) {
        console.warn('⚠️ Failed to load test table logs:', e.message);
        logs = [];
    }

    // 尝试获取任务详情
    try {
        console.log('📡 正在获取任务详情...');
        const taskResponse = await fetch(`${API_BASE}/test-tables/tasks/${taskId}`);
        if (!taskResponse.ok) {
            throw new Error(`任务详情API返回错误: ${taskResponse.status}`);
        }
        taskInfo = await taskResponse.json();
        console.log('✅ Test table task info loaded');
    } catch (e) {
        console.warn('⚠️ Failed to load test table task info:', e.message);
    }

    // 测试表生成的阶段
    const steps = [
        { id: 'initialization', name: '初始化', status: 'pending' },
        { id: 'hdfs_setup', name: '创建HDFS目录', status: 'pending' },
        { id: 'data_generation', name: '生成数据文件', status: 'pending' },
        { id: 'hive_table_creation', name: '创建Hive表', status: 'pending' },
        { id: 'partition_creation', name: '添加分区', status: 'pending' },
        { id: 'verification', name: '验证结果', status: 'pending' },
        { id: 'completed', name: '完成', status: 'pending' }
    ];

    // 检查是否有错误日志来确定状态
    const hasError = (logs || []).some(l => (l.log_level || '').toUpperCase() === 'ERROR');
    let status = taskInfo?.status || 'running';

    console.log('📊 状态分析:');
    console.log('   - 原始状态:', status);
    console.log('   - 有错误日志:', hasError);
    console.log('   - 日志数量:', logs.length);

    // 根据任务状态更新步骤状态
    if (status === 'success') {
        steps.forEach(step => step.status = 'success');
    } else if (status === 'failed' || hasError) {
        steps[0].status = 'success';  // 初始化总是成功的
        steps.forEach((step, index) => {
            if (index > 0) step.status = 'failed';
        });
        status = 'failed';
    } else if (status === 'running') {
        steps[0].status = 'success';  // 初始化完成
        steps[1].status = 'running';  // 当前在创建HDFS目录阶段
    }

    const normLogs = (logs || []).map(l => ({
        ts: String(l.timestamp || ''),
        level: levelMap(l.log_level),
        source: 'test-table',
        message: l.message || '',
        step_id: l.phase || 'initialization'
    }));

    const result = {
        title: taskInfo?.task_name || '测试表生成任务',
        status,
        progress: taskInfo?.progress_percentage || 0,
        currentOperation: taskInfo?.current_operation || (hasError ? '执行失败' : '正在执行'),
        startedAt: taskInfo?.started_time,
        finishedAt: taskInfo?.completed_time,
        steps,
        logs: normLogs
    };

    console.log('🎯 最终结果:');
    console.log('   - 任务标题:', result.title);
    console.log('   - 最终状态:', result.status);
    console.log('   - 进度:', result.progress + '%');
    console.log('   - 当前操作:', result.currentOperation);
    console.log('   - 步骤数量:', result.steps.length);
    console.log('   - 标准化日志数量:', result.logs.length);

    // 显示日志详情
    if (result.logs.length > 0) {
        console.log('\n📝 日志详情:');
        result.logs.forEach((log, index) => {
            console.log(`   ${index + 1}. [${log.level}] ${log.message}`);
            console.log(`      时间: ${log.ts}`);
            console.log(`      阶段: ${log.step_id}`);
        });
    }

    return result;
}

// 测试已知任务ID
async function testKnownTasks() {
    console.log('🔍 开始测试已知任务...\n');

    const knownTaskIds = [
        '274486bd-8c6f-4c55-806f-80dbdab621fc',
        '3f5cb0db-79f6-420e-87e0-3b041646f87c',
        '26e8c07c-4eca-47de-96d6-b9814c0e89e3'
    ];

    for (const taskId of knownTaskIds) {
        console.log(`\n${'='.repeat(60)}`);
        console.log(`测试任务: ${taskId}`);
        console.log(`${'='.repeat(60)}`);

        try {
            const result = await loadTestTableRun(taskId);
            console.log('✅ 任务测试成功!');
        } catch (error) {
            console.error('❌ 任务测试失败:', error.message);
        }
    }
}

// 运行测试
testKnownTasks().then(() => {
    console.log('\n🎉 所有测试完成!');
    process.exit(0);
}).catch(error => {
    console.error('💥 测试过程中发生错误:', error);
    process.exit(1);
});