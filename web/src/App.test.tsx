import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";

describe("App", () => {
  it("redirects the root path to the login page", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: /Sign in|Log in|Welcome/i })).toBeInTheDocument();
  });

  it("renders the component gallery route", () => {
    render(
      <MemoryRouter initialEntries={["/design"]}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: "WareStock Component Library" })
    ).toBeInTheDocument();
  });

  it.each([
    ["/auth/signup", /Create account|Sign up|Register/i],
    ["/auth/recover-password", /Recover|Reset|Forgot/i],
    ["/auth/change-password", /Initial Credential Provisioning|Update Code|Change password/i],
  ])("renders %s", (path, heading) => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  });
});
