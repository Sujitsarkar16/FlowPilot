import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { installMockEventSource } from "@/tests/mocks/sse";

afterEach(cleanup);
installMockEventSource();
