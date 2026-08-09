import { describe, expect, test } from "bun:test";
import { normalizeClientError } from "../src/utils/errors";

describe("normalizeClientError", () => {
  test("turns an unauthenticated HTTP response into an actionable auth error", () => {
    const error = normalizeClientError({
      code: "HTTP_ERROR",
      message: "Request failed with status 401",
      statusCode: 401,
    });

    expect(error.code).toBe("UNAUTHORIZED");
    expect(error.message).toContain("Phiên đăng nhập");
  });

  test("keeps a safe fetch failure reason and points to the same-origin health route", () => {
    const error = normalizeClientError(new TypeError("Failed to fetch"));

    expect(error.code).toBe("NETWORK_ERROR");
    expect(error.details.reason).toBe("Failed to fetch");
    expect(error.details.next_step).toContain("/api/v1/health");
  });
});
