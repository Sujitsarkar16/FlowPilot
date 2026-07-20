import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, vi } from "vitest";

import { installMockEventSource } from "@/tests/mocks/sse";

afterEach(cleanup);
installMockEventSource();
