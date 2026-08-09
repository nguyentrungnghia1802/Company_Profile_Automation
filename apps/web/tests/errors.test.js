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

  test("preserves actionable duplicate-company details from the API", () => {
    const error = normalizeClientError({
      code: "COMPANY_DUPLICATE_REVIEW_REQUIRED",
      message: "duplicate",
      statusCode: 409,
      details: {
        existing_company_id: "company-123",
        existing_company_name: "VNPT",
        match_reason: "EXACT_NORMALIZED_NAME_OR_ALIAS_MATCH",
      },
    });

    expect(error.code).toBe("COMPANY_DUPLICATE_REVIEW_REQUIRED");
    expect(error.message).toContain("đã tồn tại");
    expect(error.details.existing_company_name).toBe("VNPT");
    expect(error.statusCode).toBe(409);
  });
});
