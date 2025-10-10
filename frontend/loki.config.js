module.exports = {
  configurations: {
    chrome: {
      target: "chrome.app",
      width: 1200,
      height: 800,
      deviceScaleFactor: 1,
    },
    mobile: {
      target: "chrome.app",
      width: 375,
      height: 812,
      deviceScaleFactor: 2,
    },
    tablet: {
      target: "chrome.app",
      width: 768,
      height: 1024,
      deviceScaleFactor: 2,
    },
  },
  storiesFilter: (s) => !s.includes("Docs"),
};
