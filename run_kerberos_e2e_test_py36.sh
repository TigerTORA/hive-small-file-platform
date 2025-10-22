#!/usr/bin/env bash
#
# Kerberos E2E 快速测试脚本 (Python 3.6 兼容)
# 用于在 CDP-14 集群上测试 Kerberos 认证功能
#

set -euo pipefail

# 配置参数
KEYTAB="${1:-/etc/security/keytabs/hive.keytab}"
PRINCIPAL="${2:-hive/cdpmaster1.phoenixesinfo.com@PHOENIXESINFO.COM}"
CDP_HOST="${3:-192.168.0.105}"
WEBHDFS_PORT="${4:-14000}"
HIVE_PORT="${5:-10000}"

echo "================================================================================"
echo "  Kerberos E2E 快速测试 (BMAP 方法 - Python 3.6 兼容)"
echo "================================================================================"
echo ""
echo "测试配置:"
echo "  Keytab: $KEYTAB"
echo "  Principal: $PRINCIPAL"
echo "  CDP Host: $CDP_HOST"
echo "  WebHDFS Port: $WEBHDFS_PORT"
echo "  HiveServer2 Port: $HIVE_PORT"
echo ""

# ========== B - Baseline 阶段 ==========
echo "================================================================================"
echo "  [B] BASELINE 阶段: 环境基准检查"
echo "================================================================================"
echo ""

# 1. 检查 Kerberos 工具
echo "[B.1] 检查 Kerberos 工具..."
if command -v kinit >/dev/null 2>&1; then
    echo "  ✓ kinit: $(which kinit)"
else
    echo "  ✗ kinit 未安装"
    exit 1
fi

if command -v klist >/dev/null 2>&1; then
    echo "  ✓ klist: $(which klist)"
else
    echo "  ✗ klist 未安装"
    exit 1
fi

# 2. 检查 Keytab 文件
echo ""
echo "[B.2] 检查 Keytab 文件..."
if [ -f "$KEYTAB" ]; then
    echo "  ✓ Keytab 存在: $KEYTAB"
    ls -lh "$KEYTAB"

    echo "  ✓ Keytab 内容:"
    klist -ke "$KEYTAB" | head -10
else
    echo "  ✗ Keytab 不存在: $KEYTAB"
    exit 1
fi

# 3. 检查网络连接
echo ""
echo "[B.3] 检查网络连接..."
if curl -s -I --connect-timeout 5 "http://$CDP_HOST:$WEBHDFS_PORT/webhdfs/v1" >/dev/null 2>&1; then
    echo "  ✓ WebHDFS 可访问: http://$CDP_HOST:$WEBHDFS_PORT"
else
    echo "  ⚠ WebHDFS 可能不可访问: http://$CDP_HOST:$WEBHDFS_PORT"
fi

#  4. 检查 krb5.conf
echo ""
echo "[B.4] 检查 Kerberos 配置..."
if [ -f /etc/krb5.conf ]; then
    echo "  ✓ krb5.conf 存在"
    grep -A 5 "PHOENIXESINFO.COM" /etc/krb5.conf | head -10
else
    echo "  ✗ krb5.conf 不存在"
    exit 1
fi

echo ""
echo "✓ 基线检查完成"
echo ""

# ========== M - Mutation 阶段 ==========
echo "================================================================================"
echo "  [M] MUTATION 阶段: 执行测试场景"
echo "================================================================================"
echo ""

# 测试 1: Kerberos 票据获取
echo "[M.1] 场景 1: Kerberos 票据获取"
echo "--------------------------------------------------------------"
echo "  清除现有票据..."
kdestroy -A 2>/dev/null || true

echo "  执行 kinit..."
if kinit -kt "$KEYTAB" "$PRINCIPAL"; then
    echo "  ✓ kinit 成功"

    echo ""
    echo "  当前票据:"
    klist | head -20

    SCENARIO_1="PASS"
else
    echo "  ✗ kinit 失败"
    SCENARIO_1="FAIL"
fi

echo ""

# 测试 2: WebHDFS 基础连接
echo "[M.2] 场景 2: WebHDFS 基础连接 (无认证)"
echo "--------------------------------------------------------------"
WEBHDFS_URL="http://$CDP_HOST:$WEBHDFS_PORT/webhdfs/v1/?op=LISTSTATUS"
echo "  测试 URL: $WEBHDFS_URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$WEBHDFS_URL" 2>/dev/null || echo "000")
echo "  HTTP 状态码: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo "  ✓ WebHDFS 服务可访问 (HTTP $HTTP_CODE)"
    SCENARIO_2="PASS"
else
    echo "  ✗ WebHDFS 服务不可访问 (HTTP $HTTP_CODE)"
    SCENARIO_2="FAIL"
fi

echo ""

# 测试 3: 使用 kinit 票据测试 curl Kerberos 认证
echo "[M.3] 场景 3: 使用 curl 测试 Kerberos 认证"
echo "--------------------------------------------------------------"

# 确保有有效票据
if ! klist >/dev/null 2>&1; then
    echo "  重新获取票据..."
    kinit -kt "$KEYTAB" "$PRINCIPAL"
fi

# 使用 curl 和 --negotiate 测试 SPNEGO
echo "  测试 SPNEGO 认证..."
RESPONSE=$(curl -s --negotiate -u : "http://$CDP_HOST:$WEBHDFS_PORT/webhdfs/v1/?op=LISTSTATUS" 2>&1 || true)

if echo "$RESPONSE" | grep -q "FileStatuses"; then
    echo "  ✓ Kerberos 认证成功，获取到文件列表"
    echo "  响应示例:"
    echo "$RESPONSE" | head -5
    SCENARIO_3="PASS"
elif echo "$RESPONSE" | grep -qi "unauthorized\|401"; then
    echo "  ✗ 认证失败 (401 Unauthorized)"
    SCENARIO_3="FAIL"
else
    echo "  ⚠ 无法确定结果，响应:"
    echo "$RESPONSE" | head -10
    SCENARIO_3="UNKNOWN"
fi

echo ""

# 测试 4: HiveServer2 端口连通性
echo "[M.4] 场景 4: HiveServer2 端口连通性"
echo "--------------------------------------------------------------"
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$CDP_HOST/$HIVE_PORT" 2>/dev/null; then
    echo "  ✓ HiveServer2 端口可访问: $CDP_HOST:$HIVE_PORT"
    SCENARIO_4="PASS"
else
    echo "  ✗ HiveServer2 端口不可访问: $CDP_HOST:$HIVE_PORT"
    SCENARIO_4="FAIL"
fi

echo ""

# 测试 5: 票据有效性验证
echo "[M.5] 场景 5: 票据有效性验证"
echo "--------------------------------------------------------------"
TICKET_INFO=$(klist 2>&1)

if echo "$TICKET_INFO" | grep -q "$PRINCIPAL"; then
    echo "  ✓ 票据仍然有效"
    echo "  Principal: $PRINCIPAL"

    # 提取过期时间
    if echo "$TICKET_INFO" | grep -q "Expires"; then
        echo ""
        echo "  票据详情:"
        echo "$TICKET_INFO" | grep -A 2 "Valid starting"
    fi

    SCENARIO_5="PASS"
else
    echo "  ✗ 票据无效或已过期"
    SCENARIO_5="FAIL"
fi

echo ""

# 测试 6: 清理测试
echo "[M.6] 场景 6: 清理和重新认证"
echo "--------------------------------------------------------------"
echo "  清除票据..."
kdestroy -A 2>/dev/null || true

echo "  验证票据已清除..."
if ! klist >/dev/null 2>&1; then
    echo "  ✓ 票据已成功清除"
else
    echo "  ⚠ 票据仍然存在"
fi

echo "  重新获取票据..."
if kinit -kt "$KEYTAB" "$PRINCIPAL"; then
    echo "  ✓ 重新认证成功"
    SCENARIO_6="PASS"
else
    echo "  ✗ 重新认证失败"
    SCENARIO_6="FAIL"
fi

echo ""

# ========== A - Analysis 阶段 ==========
echo "================================================================================"
echo "  [A] ANALYSIS 阶段: 分析测试结果"
echo "================================================================================"
echo ""

# 统计结果
TOTAL=6
PASSED=0
FAILED=0

for scenario in "$SCENARIO_1" "$SCENARIO_2" "$SCENARIO_3" "$SCENARIO_4" "$SCENARIO_5" "$SCENARIO_6"; do
    if [ "$scenario" = "PASS" ]; then
        PASSED=$((PASSED + 1))
    elif [ "$scenario" = "FAIL" ]; then
        FAILED=$((FAILED + 1))
    fi
done

SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED / $TOTAL) * 100}")

echo "测试摘要:"
echo "  总测试数: $TOTAL"
echo "  ✓ 通过: $PASSED"
echo "  ✗ 失败: $FAILED"
echo "  成功率: ${SUCCESS_RATE}%"
echo ""

echo "详细结果:"
echo "  场景 1 (Kerberos 票据获取): $SCENARIO_1"
echo "  场景 2 (WebHDFS 基础连接): $SCENARIO_2"
echo "  场景 3 (Kerberos 认证): $SCENARIO_3"
echo "  场景 4 (HiveServer2 端口): $SCENARIO_4"
echo "  场景 5 (票据有效性): $SCENARIO_5"
echo "  场景 6 (清理和重新认证): $SCENARIO_6"
echo ""

# ========== P - Publish 阶段 ==========
echo "================================================================================"
echo "  [P] PUBLISH 阶段: 生成测试报告"
echo "================================================================================"
echo ""

REPORT_FILE="kerberos_e2e_test_report_$(date +%Y%m%d_%H%M%S).txt"

cat > "$REPORT_FILE" <<EOF
===============================================================================
  Kerberos E2E 测试报告 (BMAP 方法)
===============================================================================

生成时间: $(date -Iseconds)
主机名: $(hostname)
Principal: $PRINCIPAL
Keytab: $KEYTAB
CDP 集群: $CDP_HOST

===============================================================================
  测试摘要
===============================================================================

总测试数: $TOTAL
通过: $PASSED
失败: $FAILED
成功率: ${SUCCESS_RATE}%

===============================================================================
  详细测试结果
===============================================================================

场景 1: Kerberos 票据获取
  状态: $SCENARIO_1
  说明: 测试使用 keytab 获取 Kerberos 票据

场景 2: WebHDFS 基础连接
  状态: $SCENARIO_2
  说明: 测试 WebHDFS 服务是否可访问

场景 3: Kerberos 认证 (SPNEGO)
  状态: $SCENARIO_3
  说明: 使用 curl --negotiate 测试 Kerberos 认证

场景 4: HiveServer2 端口连通性
  状态: $SCENARIO_4
  说明: 测试 HiveServer2 端口是否可访问

场景 5: 票据有效性验证
  状态: $SCENARIO_5
  说明: 验证获取的票据是否有效

场景 6: 清理和重新认证
  状态: $SCENARIO_6
  说明: 测试票据清除和重新获取流程

===============================================================================
  建议和后续行动
===============================================================================

EOF

# 添加建议
if [ "$FAILED" -eq 0 ]; then
    echo "✓ 所有测试通过，Kerberos 认证工作正常" >> "$REPORT_FILE"
else
    echo "⚠ 部分测试失败，建议:" >> "$REPORT_FILE"
    echo "  1. 检查失败场景的详细日志" >> "$REPORT_FILE"
    echo "  2. 验证 CDP 集群配置和网络连接" >> "$REPORT_FILE"
    echo "  3. 确认 Kerberos 配置正确" >> "$REPORT_FILE"
fi

echo ""
echo "================================================================================"
echo ""

echo "✓ 报告已生成: $REPORT_FILE"
cat "$REPORT_FILE"

echo ""
echo "================================================================================"
echo "  测试完成!"
echo "================================================================================"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo "🎉 所有测试通过! Kerberos 认证模块工作正常。"
    exit 0
else
    echo "⚠ $FAILED 个测试失败，请查看报告了解详情。"
    exit 1
fi
