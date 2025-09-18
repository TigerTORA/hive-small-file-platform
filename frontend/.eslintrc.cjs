/* eslint-env node */
require("@rushstack/eslint-patch/modern-module-resolution");

module.exports = {
  root: true,
  extends: [
    "plugin:vue/vue3-essential",
    "eslint:recommended",
    "@vue/eslint-config-typescript",
    "@vue/eslint-config-prettier/skip-formatting",
  ],
  parserOptions: {
    ecmaVersion: "latest",
  },
  rules: {
    // Vue 相关规则
    "vue/multi-word-component-names": "off",
    "vue/no-v-html": "warn",
    "vue/component-tags-order": [
      "error",
      {
        order: ["script", "template", "style"],
      },
    ],
    "vue/component-name-in-template-casing": ["error", "PascalCase"],
    "vue/no-unused-vars": "error",

    // TypeScript 相关规则
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/no-non-null-assertion": "warn",

    // 通用规则
    "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
    "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
    "prefer-const": "error",
    "no-var": "error",
    "no-unused-vars": "off", // 使用 TypeScript 版本

    // 代码风格
    eqeqeq: ["error", "always"],
    curly: ["error", "all"],
    "brace-style": ["error", "1tbs"],
    "comma-dangle": ["error", "never"],
    quotes: ["error", "single", { avoidEscape: true }],
    semi: ["error", "never"],

    // 最佳实践
    "no-magic-numbers": [
      "warn",
      {
        ignore: [-1, 0, 1, 2, 10, 100, 1000],
        ignoreArrayIndexes: true,
        detectObjects: false,
      },
    ],
    complexity: ["warn", 10],
    "max-depth": ["warn", 4],
    "max-lines-per-function": ["warn", { max: 50, skipComments: true }],
  },
  overrides: [
    {
      files: ["*.vue"],
      rules: {
        "max-lines-per-function": "off", // Vue 组件可以更长
      },
    },
  ],
};
