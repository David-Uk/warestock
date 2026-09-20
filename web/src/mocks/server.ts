// MSW Node server — used in Vitest
// Browser service worker is configured separately in src/mocks/browser.ts
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
