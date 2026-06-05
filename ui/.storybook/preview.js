import "../src/theme.css";

/** @type { import('@storybook/html').Preview } */
const preview = {
  parameters: {
    backgrounds: {
      default: "dark",
      values: [{ name: "dark", value: "#0f1115" }],
    },
  },
};
export default preview;
