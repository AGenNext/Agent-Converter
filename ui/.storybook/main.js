/** @type { import('@storybook/html-vite').StorybookConfig } */
const config = {
  stories: ["../src/**/*.stories.js"],
  // Storybook 9+ ships controls/actions/viewport/backgrounds in core, so the
  // former @storybook/addon-essentials package is no longer needed.
  addons: [],
  framework: { name: "@storybook/html-vite", options: {} },
};
export default config;
