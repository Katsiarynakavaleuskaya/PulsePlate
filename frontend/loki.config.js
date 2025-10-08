module.exports = {
  configurations: {
    chrome: {
      target: "chrome.app",
      width: 1200,
      height: 800,
      deviceScaleFactor: 1,
    },
  },
  storiesFilter: (s) => !s.includes("Docs"),
};
