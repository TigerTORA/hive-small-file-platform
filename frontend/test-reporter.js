const fs = require('fs');
const path = require('path');
const TEST_CONFIG = require('./test-config.js');

class TestReporter {
  constructor() {
    this.outputDir = TEST_CONFIG.reporting.outputDir;
    this.ensureOutputDirectory();
  }

  ensureOutputDirectory() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
    
    // 创建子目录
    const subdirs = ['screenshots', 'reports', 'logs'];
    subdirs.forEach(dir => {
      const fullPath = path.join(this.outputDir, dir);
      if (!fs.existsSync(fullPath)) {
        fs.mkdirSync(fullPath, { recursive: true });
      }
    });
  }

  async generateComprehensiveReport(testResults) {
    console.log('📊 生成综合测试报告...');
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const reportBaseName = `test-report-${timestamp}`;
    
    // 生成多种格式的报告
    const reports = {
      html: await this.generateHtmlReport(testResults, reportBaseName),
      json: await this.generateJsonReport(testResults, reportBaseName),
      xml: await this.generateXmlReport(testResults, reportBaseName),
      csv: await this.generateCsvReport(testResults, reportBaseName)
    };
    
    // 生成报告索引
    await this.generateReportIndex(reports, testResults);
    
    console.log('✅ 所有格式的测试报告已生成');
    return reports.html;
  }

  async generateHtmlReport(testResults, baseName) {
    const htmlPath = path.join(this.outputDir, 'reports', `${baseName}.html`);
    
    const htmlContent = this.buildHtmlContent(testResults);
    fs.writeFileSync(htmlPath, htmlContent, 'utf8');
    
    console.log(`📄 HTML报告: ${htmlPath}`);
    return htmlPath;
  }

  buildHtmlContent(testResults) {
    const timestamp = new Date().toLocaleString();
    const overall = testResults.overall;
    const successRate = overall.total > 0 ? ((overall.passed / overall.total) * 100).toFixed(1) : 0;
    
    return `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hive小文件平台 - 综合测试报告</title>
    <style>
        ${this.getCssStyles()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🧪 Hive小文件平台 - 综合测试报告</h1>
            <div class="meta-info">
                <span>📅 生成时间: ${timestamp}</span>
                <span>⏱️ 执行时长: ${this.formatDuration(overall.duration)}</span>
                <span class="success-rate ${this.getSuccessRateClass(successRate)}">
                    📊 成功率: ${successRate}%
                </span>
            </div>
        </header>

        <div class="summary">
            <h2>📋 测试摘要</h2>
            <div class="summary-cards">
                <div class="card total">
                    <h3>总测试数</h3>
                    <div class="number">${overall.total}</div>
                </div>
                <div class="card passed">
                    <h3>通过</h3>
                    <div class="number">${overall.passed}</div>
                </div>
                <div class="card failed">
                    <h3>失败</h3>
                    <div class="number">${overall.failed}</div>
                </div>
                <div class="card rate">
                    <h3>成功率</h3>
                    <div class="number">${successRate}%</div>
                </div>
            </div>
        </div>

        <div class="progress-bar">
            <div class="progress-fill" style="width: ${successRate}%"></div>
        </div>

        <div class="suites">
            <h2>📊 测试套件详情</h2>
            ${this.buildSuitesHtml(testResults.suites)}
        </div>

        ${testResults.errors.length > 0 ? this.buildErrorsHtml(testResults.errors) : ''}

        <div class="recommendations">
            <h2>💡 建议和下一步</h2>
            ${this.buildRecommendationsHtml(testResults)}
        </div>

        <div class="verification-links">
            <h2>🔗 验证链接</h2>
            <div class="links">
                <a href="${TEST_CONFIG.app.baseUrl}/#/clusters" target="_blank" class="link-button">
                    🏗️ 集群管理
                </a>
                <a href="${TEST_CONFIG.app.baseUrl}/#/dashboard" target="_blank" class="link-button">
                    📊 监控仪表板
                </a>
                <a href="${TEST_CONFIG.app.baseUrl}/#/tables" target="_blank" class="link-button">
                    📋 表管理
                </a>
                <a href="${TEST_CONFIG.app.baseUrl}/#/tasks" target="_blank" class="link-button">
                    📝 任务管理
                </a>
                <a href="${TEST_CONFIG.app.apiBaseUrl}/health" target="_blank" class="link-button">
                    ❤️ API健康检查
                </a>
            </div>
        </div>

        <footer class="footer">
            <p>🤖 此报告由 Hive小文件平台自动化测试套件生成</p>
            <p>📧 如有问题，请联系开发团队</p>
        </footer>
    </div>

    <script>
        ${this.getJavaScript()}
    </script>
</body>
</html>`;
  }

  buildSuitesHtml(suites) {
    return Object.entries(suites).map(([key, suite]) => {
      const successRate = suite.total > 0 ? ((suite.passed / suite.total) * 100).toFixed(1) : 0;
      const statusIcon = suite.status === 'PASS' ? '✅' : suite.status === 'FAIL' ? '❌' : '⚠️';
      
      return `
        <div class="suite-card ${suite.status.toLowerCase()}">
            <div class="suite-header">
                <h3>${statusIcon} ${suite.name}</h3>
                <div class="suite-stats">
                    <span class="stat">通过: ${suite.passed}/${suite.total}</span>
                    <span class="stat">成功率: ${successRate}%</span>
                    <span class="stat">耗时: ${this.formatDuration(suite.duration)}</span>
                </div>
            </div>
            
            ${suite.details ? this.buildSuiteDetailsHtml(suite.details) : ''}
            
            ${suite.error ? `<div class="error-message">❌ 错误: ${suite.error}</div>` : ''}
        </div>`;
    }).join('');
  }

  buildSuiteDetailsHtml(details) {
    if (!details || details.length === 0) return '';
    
    const failedTests = details.filter(test => test.status === 'FAIL');
    const passedTests = details.filter(test => test.status === 'PASS');
    
    let html = '<div class="suite-details">';
    
    if (failedTests.length > 0) {
      html += '<div class="failed-tests"><h4>❌ 失败的测试:</h4><ul>';
      failedTests.forEach(test => {
        html += `<li>${test.name}: ${test.details}</li>`;
      });
      html += '</ul></div>';
    }
    
    if (passedTests.length > 5) {
      html += `<div class="passed-summary">✅ ${passedTests.length} 个测试通过</div>`;
    } else if (passedTests.length > 0) {
      html += '<div class="passed-tests"><h4>✅ 通过的测试:</h4><ul>';
      passedTests.forEach(test => {
        html += `<li>${test.name}</li>`;
      });
      html += '</ul></div>';
    }
    
    html += '</div>';
    return html;
  }

  buildErrorsHtml(errors) {
    return `
      <div class="errors-section">
        <h2>❌ 错误详情</h2>
        <div class="errors-list">
          ${errors.map(error => `
            <div class="error-item">
              <div class="error-type">${error.type}</div>
              <div class="error-message">${error.message}</div>
              <div class="error-time">${error.timestamp}</div>
            </div>
          `).join('')}
        </div>
      </div>`;
  }

  buildRecommendationsHtml(testResults) {
    const overall = testResults.overall;
    const successRate = overall.total > 0 ? ((overall.passed / overall.total) * 100) : 0;
    const failedSuites = Object.values(testResults.suites).filter(suite => suite.status === 'FAIL');
    
    let recommendations = '<div class="recommendations-content">';
    
    if (successRate === 100) {
      recommendations += `
        <div class="recommendation success">
          <h3>🎉 恭喜！所有测试都通过了！</h3>
          <ul>
            <li>✨ 您的应用程序功能完整，质量良好</li>
            <li>🚀 可以考虑部署到生产环境</li>
            <li>📈 建议定期运行测试以确保持续质量</li>
            <li>🔄 可以考虑添加更多测试用例来提高覆盖率</li>
          </ul>
        </div>`;
    } else if (successRate >= 80) {
      recommendations += `
        <div class="recommendation warning">
          <h3>✅ 大部分测试通过，应用程序基本正常</h3>
          <ul>
            <li>⚠️ 建议检查和修复 ${overall.failed} 个失败的测试</li>
            <li>🔧 优先处理关键功能相关的失败测试</li>
            <li>📝 记录并跟踪修复进度</li>
            <li>🔄 修复后重新运行测试验证</li>
          </ul>
        </div>`;
    } else if (successRate >= 60) {
      recommendations += `
        <div class="recommendation error">
          <h3>⚠️ 测试通过率偏低，应用程序存在一些问题</h3>
          <ul>
            <li>🚨 建议立即检查核心功能</li>
            <li>🔧 优先修复API连接和导航问题</li>
            <li>📋 制定详细的修复计划</li>
            <li>🧪 增加单元测试和集成测试</li>
          </ul>
        </div>`;
    } else {
      recommendations += `
        <div class="recommendation critical">
          <h3>❌ 测试失败率较高，应用程序存在严重问题</h3>
          <ul>
            <li>🚨 立即停止部署，进行全面检查</li>
            <li>🔧 优先修复基础设施和核心功能</li>
            <li>👥 建议团队协作解决问题</li>
            <li>📊 考虑重新评估开发流程</li>
          </ul>
        </div>`;
    }
    
    if (failedSuites.length > 0) {
      recommendations += `
        <div class="failed-suites-list">
          <h3>🔧 需要修复的测试套件：</h3>
          <ol>
            ${failedSuites.map(suite => `<li>${suite.name}</li>`).join('')}
          </ol>
        </div>`;
    }
    
    recommendations += '</div>';
    return recommendations;
  }

  getCssStyles() {
    return `
      * { margin: 0; padding: 0; box-sizing: border-box; }
      
      body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
      }
      
      .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: white;
        margin: 20px auto;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
      }
      
      .header {
        text-align: center;
        margin-bottom: 30px;
        padding: 20px;
        background: linear-gradient(135deg, #6c5ce7, #fd79a8);
        border-radius: 10px;
        color: white;
      }
      
      .header h1 {
        font-size: 2.5rem;
        margin-bottom: 10px;
      }
      
      .meta-info {
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
      }
      
      .meta-info span {
        background: rgba(255,255,255,0.2);
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9rem;
      }
      
      .success-rate.excellent { background: rgba(0,255,0,0.3); }
      .success-rate.good { background: rgba(255,255,0,0.3); }
      .success-rate.poor { background: rgba(255,165,0,0.3); }
      .success-rate.critical { background: rgba(255,0,0,0.3); }
      
      .summary {
        margin-bottom: 30px;
      }
      
      .summary h2 {
        color: #2d3436;
        margin-bottom: 20px;
        font-size: 1.8rem;
      }
      
      .summary-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
      }
      
      .card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
      }
      
      .card:hover {
        transform: translateY(-5px);
      }
      
      .card.total { background: linear-gradient(135deg, #74b9ff, #0984e3); color: white; }
      .card.passed { background: linear-gradient(135deg, #00b894, #00a085); color: white; }
      .card.failed { background: linear-gradient(135deg, #e84393, #d63031); color: white; }
      .card.rate { background: linear-gradient(135deg, #fdcb6e, #e17055); color: white; }
      
      .card h3 {
        font-size: 1rem;
        margin-bottom: 10px;
        opacity: 0.9;
      }
      
      .card .number {
        font-size: 2.5rem;
        font-weight: bold;
      }
      
      .progress-bar {
        width: 100%;
        height: 20px;
        background: #ecf0f1;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 30px;
      }
      
      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #00b894, #00a085);
        transition: width 1s ease;
      }
      
      .suites {
        margin-bottom: 30px;
      }
      
      .suite-card {
        margin-bottom: 20px;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      }
      
      .suite-card.pass {
        border-left: 5px solid #00b894;
      }
      
      .suite-card.fail {
        border-left: 5px solid #e84393;
      }
      
      .suite-card.error {
        border-left: 5px solid #fdcb6e;
      }
      
      .suite-header {
        padding: 20px;
        background: #f8f9fa;
        display: flex;
        justify-content: between;
        align-items: center;
        flex-wrap: wrap;
      }
      
      .suite-header h3 {
        color: #2d3436;
        margin-bottom: 10px;
        flex: 1;
      }
      
      .suite-stats {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
      }
      
      .stat {
        background: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.85rem;
        color: #636e72;
      }
      
      .suite-details {
        padding: 20px;
        background: white;
      }
      
      .failed-tests h4, .passed-tests h4 {
        margin-bottom: 10px;
        color: #2d3436;
      }
      
      .failed-tests ul, .passed-tests ul {
        list-style: none;
        padding-left: 0;
      }
      
      .failed-tests li {
        padding: 5px 0;
        border-bottom: 1px solid #fee;
        color: #d63031;
      }
      
      .passed-tests li {
        padding: 5px 0;
        color: #00b894;
      }
      
      .passed-summary {
        padding: 10px;
        background: #eafaf1;
        border-radius: 5px;
        color: #00b894;
        font-weight: bold;
      }
      
      .error-message {
        padding: 10px;
        background: #ffeaa7;
        border-radius: 5px;
        color: #d63031;
        margin-top: 10px;
      }
      
      .errors-section {
        margin-bottom: 30px;
      }
      
      .error-item {
        padding: 15px;
        margin-bottom: 10px;
        background: #fff5f5;
        border-left: 4px solid #e84393;
        border-radius: 5px;
      }
      
      .error-type {
        font-weight: bold;
        color: #2d3436;
        margin-bottom: 5px;
      }
      
      .error-message {
        color: #636e72;
        margin-bottom: 5px;
      }
      
      .error-time {
        font-size: 0.8rem;
        color: #95a5a6;
      }
      
      .recommendations {
        margin-bottom: 30px;
      }
      
      .recommendation {
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
      }
      
      .recommendation.success {
        background: #eafaf1;
        border-left: 5px solid #00b894;
      }
      
      .recommendation.warning {
        background: #fff8e1;
        border-left: 5px solid #fdcb6e;
      }
      
      .recommendation.error {
        background: #ffebee;
        border-left: 5px solid #e84393;
      }
      
      .recommendation.critical {
        background: #ffebee;
        border-left: 5px solid #d63031;
        border: 2px solid #d63031;
      }
      
      .recommendation h3 {
        margin-bottom: 15px;
        color: #2d3436;
      }
      
      .recommendation ul {
        list-style: none;
        padding-left: 0;
      }
      
      .recommendation li {
        padding: 5px 0;
        color: #636e72;
      }
      
      .failed-suites-list {
        margin-top: 20px;
        padding: 15px;
        background: #f8f9fa;
        border-radius: 5px;
      }
      
      .verification-links {
        margin-bottom: 30px;
      }
      
      .links {
        display: flex;
        gap: 15px;
        flex-wrap: wrap;
      }
      
      .link-button {
        display: inline-block;
        padding: 12px 24px;
        background: linear-gradient(135deg, #74b9ff, #0984e3);
        color: white;
        text-decoration: none;
        border-radius: 25px;
        transition: all 0.3s ease;
        font-weight: bold;
      }
      
      .link-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(116, 185, 255, 0.4);
      }
      
      .footer {
        text-align: center;
        padding: 20px;
        background: #f8f9fa;
        border-radius: 10px;
        color: #636e72;
      }
      
      @media (max-width: 768px) {
        .summary-cards {
          grid-template-columns: repeat(2, 1fr);
        }
        
        .suite-header {
          flex-direction: column;
          align-items: flex-start;
        }
        
        .links {
          flex-direction: column;
        }
        
        .link-button {
          text-align: center;
        }
      }
    `;
  }

  getJavaScript() {
    return `
      // 页面加载完成后的动画效果
      document.addEventListener('DOMContentLoaded', function() {
        // 进度条动画
        setTimeout(() => {
          const progressBar = document.querySelector('.progress-fill');
          if (progressBar) {
            progressBar.style.width = progressBar.style.width;
          }
        }, 500);
        
        // 卡片动画
        const cards = document.querySelectorAll('.card');
        cards.forEach((card, index) => {
          setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
              card.style.opacity = '1';
              card.style.transform = 'translateY(0)';
            }, 100);
          }, index * 100);
        });
        
        // 套件卡片折叠/展开功能
        const suiteHeaders = document.querySelectorAll('.suite-header');
        suiteHeaders.forEach(header => {
          header.style.cursor = 'pointer';
          header.addEventListener('click', function() {
            const details = this.nextElementSibling;
            if (details && details.classList.contains('suite-details')) {
              if (details.style.display === 'none') {
                details.style.display = 'block';
                this.style.background = '#e9ecef';
              } else {
                details.style.display = 'none';
                this.style.background = '#f8f9fa';
              }
            }
          });
        });
        
        // 添加复制链接功能
        const linkButtons = document.querySelectorAll('.link-button');
        linkButtons.forEach(button => {
          button.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            navigator.clipboard.writeText(this.href).then(() => {
              const originalText = this.textContent;
              this.textContent = '✅ 已复制';
              setTimeout(() => {
                this.textContent = originalText;
              }, 1500);
            });
          });
        });
      });
      
      // 快捷键支持
      document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
          switch(e.key) {
            case 'r':
              e.preventDefault();
              location.reload();
              break;
            case 'p':
              e.preventDefault();
              window.print();
              break;
          }
        }
      });
    `;
  }

  async generateJsonReport(testResults, baseName) {
    const jsonPath = path.join(this.outputDir, 'reports', `${baseName}.json`);
    
    const jsonData = {
      metadata: {
        generatedAt: new Date().toISOString(),
        platform: 'Hive小文件治理平台',
        version: '1.0.0'
      },
      summary: testResults.overall,
      suites: testResults.suites,
      errors: testResults.errors,
      screenshots: testResults.screenshots || []
    };
    
    fs.writeFileSync(jsonPath, JSON.stringify(jsonData, null, 2), 'utf8');
    console.log(`📄 JSON报告: ${jsonPath}`);
    return jsonPath;
  }

  async generateXmlReport(testResults, baseName) {
    const xmlPath = path.join(this.outputDir, 'reports', `${baseName}.xml`);
    
    const xmlContent = this.buildXmlContent(testResults);
    fs.writeFileSync(xmlPath, xmlContent, 'utf8');
    
    console.log(`📄 XML报告: ${xmlPath}`);
    return xmlPath;
  }

  buildXmlContent(testResults) {
    const timestamp = new Date().toISOString();
    
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml += '<testsuites>\n';
    
    Object.entries(testResults.suites).forEach(([key, suite]) => {
      xml += `  <testsuite name="${this.escapeXml(suite.name)}" `;
      xml += `tests="${suite.total}" `;
      xml += `failures="${suite.failed}" `;
      xml += `time="${(suite.duration / 1000).toFixed(3)}" `;
      xml += `timestamp="${timestamp}">\n`;
      
      if (suite.details) {
        suite.details.forEach(test => {
          xml += `    <testcase name="${this.escapeXml(test.name)}" `;
          xml += `classname="${this.escapeXml(suite.name)}">\n`;
          
          if (test.status === 'FAIL') {
            xml += `      <failure message="${this.escapeXml(test.details)}"></failure>\n`;
          }
          
          xml += '    </testcase>\n';
        });
      }
      
      xml += '  </testsuite>\n';
    });
    
    xml += '</testsuites>';
    return xml;
  }

  async generateCsvReport(testResults, baseName) {
    const csvPath = path.join(this.outputDir, 'reports', `${baseName}.csv`);
    
    let csvContent = 'Suite,Test,Status,Details,Timestamp\n';
    
    Object.entries(testResults.suites).forEach(([key, suite]) => {
      if (suite.details) {
        suite.details.forEach(test => {
          csvContent += `"${suite.name}","${test.name}","${test.status}","${test.details}","${test.timestamp}"\n`;
        });
      } else {
        csvContent += `"${suite.name}","Overall","${suite.status}","${suite.error || ''}","${new Date().toISOString()}"\n`;
      }
    });
    
    fs.writeFileSync(csvPath, csvContent, 'utf8');
    console.log(`📄 CSV报告: ${csvPath}`);
    return csvPath;
  }

  async generateReportIndex(reports, testResults) {
    const indexPath = path.join(this.outputDir, 'index.html');
    const timestamp = new Date().toLocaleString();
    
    const indexContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告索引 - Hive小文件平台</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .report-list { list-style: none; padding: 0; }
        .report-item { margin: 15px 0; padding: 15px; background: #ecf0f1; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .report-link { text-decoration: none; color: #3498db; font-weight: bold; }
        .report-link:hover { color: #2980b9; }
        .report-type { background: #3498db; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; }
        .summary { background: #e8f5e8; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
        .summary h2 { color: #27ae60; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 测试报告索引</h1>
        
        <div class="summary">
            <h2>📊 测试摘要</h2>
            <p>生成时间: ${timestamp}</p>
            <p>总测试数: ${testResults.overall.total}</p>
            <p>通过数: ${testResults.overall.passed}</p>
            <p>失败数: ${testResults.overall.failed}</p>
            <p>成功率: ${testResults.overall.total > 0 ? ((testResults.overall.passed / testResults.overall.total) * 100).toFixed(1) : 0}%</p>
        </div>
        
        <h2>📋 可用报告</h2>
        <ul class="report-list">
            <li class="report-item">
                <a href="${path.relative(this.outputDir, reports.html)}" class="report-link">📄 HTML详细报告</a>
                <span class="report-type">HTML</span>
            </li>
            <li class="report-item">
                <a href="${path.relative(this.outputDir, reports.json)}" class="report-link">📋 JSON数据报告</a>
                <span class="report-type">JSON</span>
            </li>
            <li class="report-item">
                <a href="${path.relative(this.outputDir, reports.xml)}" class="report-link">📑 XML报告 (JUnit格式)</a>
                <span class="report-type">XML</span>
            </li>
            <li class="report-item">
                <a href="${path.relative(this.outputDir, reports.csv)}" class="report-link">📊 CSV数据报告</a>
                <span class="report-type">CSV</span>
            </li>
        </ul>
        
        <div style="margin-top: 30px; text-align: center; color: #7f8c8d;">
            <p>🤖 由 Hive小文件平台自动化测试套件生成</p>
        </div>
    </div>
</body>
</html>`;
    
    fs.writeFileSync(indexPath, indexContent, 'utf8');
    console.log(`📄 报告索引: ${indexPath}`);
  }

  formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  }

  getSuccessRateClass(rate) {
    if (rate >= 95) return 'excellent';
    if (rate >= 80) return 'good';
    if (rate >= 60) return 'poor';
    return 'critical';
  }

  escapeXml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}

module.exports = TestReporter;