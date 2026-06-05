/** @type { import('@storybook/html-vite').StorybookConfig } */
const config = {
  stories: ["../src/**/*.stories.js"],
  addons: ["@storybook/addon-essentials"],
  framework: { name: "@storybook/html-vite", options: {} },
};
export default config;
