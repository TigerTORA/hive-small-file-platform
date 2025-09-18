/**
 * 文件大小格式化工具函数
 * 将字节数转换为人类可读的文件大小格式
 *
 * TDD实现：最小化实现通过所有测试用例
 */
export function formatFileSize(bytes: number): string {
  // 处理负数边缘情况
  if (bytes < 0) {
    return "0 B";
  }

  // 处理0字节
  if (bytes === 0) {
    return "0 B";
  }

  // 定义单位和对应的字节数
  const units = ["B", "KB", "MB", "GB", "TB"];
  const threshold = 1024;

  // 找到合适的单位
  let unitIndex = 0;
  let size = bytes;

  while (size >= threshold && unitIndex < units.length - 1) {
    size /= threshold;
    unitIndex++;
  }

  // 格式化数字：使用toFixed(1)然后移除不必要的.0
  let formattedSize = size.toFixed(1);
  if (formattedSize.endsWith(".0")) {
    formattedSize = formattedSize.slice(0, -2);
  }

  return `${formattedSize} ${units[unitIndex]}`;
}
