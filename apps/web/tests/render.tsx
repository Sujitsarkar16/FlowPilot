import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

import type { CurrentUser } from "@/lib/api/types";

export const authenticatedUser: CurrentUser = {
  id: "user-1",
  email: "pilot@example.test",
  display_name: "Test Pilot",
  default_autonomy: "safe_actions",
};

/** Render a screen with the deterministic authenticated identity used by API mocks. */
export function renderAuthenticated(ui: ReactElement, options?: RenderOptions) {
  return { user: authenticatedUser, ...render(ui, options) };
}
