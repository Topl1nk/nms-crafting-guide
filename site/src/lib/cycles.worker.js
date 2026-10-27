// The search for loops (lib/cycles.js) takes seconds: here it runs off the page, and each loop is sent as it is found.
import { findCycles } from "./cycles.js";

self.onmessage = ({ data }) => {
  findCycles(data.recipes, { maxSize: data.maxSize, onFound: (loop) => self.postMessage({ loop }) });
  self.postMessage({ done: true });
};
