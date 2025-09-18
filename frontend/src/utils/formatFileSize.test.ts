import { describe, it, expect } from "vitest";
import { formatFileSize } from "./formatFileSize";

/**
 * 文件大小格式化工具函数测试
 *
 * TDD演示：这些测试用例定义了我们期望的行为
 * 注意：此时 formatFileSize 函数还不存在，测试会失败
 */
describe("formatFileSize", () => {
  it("应该处理0字节", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });

  it("应该格式化字节", () => {
    expect(formatFileSize(500)).toBe("500 B");
    expect(formatFileSize(1000)).toBe("1000 B");
  });

  it("应该格式化KB", () => {
    expect(formatFileSize(1024)).toBe("1 KB");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(2048)).toBe("2 KB");
  });

  it("应该格式化MB", () => {
    expect(formatFileSize(1048576)).toBe("1 MB");
    expect(formatFileSize(1572864)).toBe("1.5 MB");
    expect(formatFileSize(10485760)).toBe("10 MB");
  });

  it("应该格式化GB", () => {
    expect(formatFileSize(1073741824)).toBe("1 GB");
    expect(formatFileSize(1610612736)).toBe("1.5 GB");
  });

  it("应该格式化TB", () => {
    expect(formatFileSize(1099511627776)).toBe("1 TB");
    expect(formatFileSize(1649267441664)).toBe("1.5 TB");
  });

  it("应该处理边缘情况", () => {
    expect(formatFileSize(1023)).toBe("1023 B");
    expect(formatFileSize(1025)).toBe("1 KB");
  });

  it("应该处理小数精度", () => {
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(1740.8)).toBe("1.7 KB");
  });

  it("应该处理负数（边缘情况）", () => {
    expect(formatFileSize(-1024)).toBe("0 B");
  });
});
