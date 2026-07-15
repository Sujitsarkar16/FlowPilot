import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

describe("foundation UI primitives", () => {
  it("renders an accessible button", () => {
    render(<Button>Continue</Button>);

    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
  });

  it("renders card content with a heading", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Foundation ready</CardTitle>
        </CardHeader>
        <CardContent>Shared UI primitives are available.</CardContent>
      </Card>,
    );

    expect(screen.getByRole("heading", { name: "Foundation ready" })).toBeVisible();
    expect(screen.getByText("Shared UI primitives are available.")).toBeVisible();
  });
});
