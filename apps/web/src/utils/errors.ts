/**
 * Frontend error code mappings and message localization.
 */

export interface ErrorMessage {
  vi: string;
  en: string;
}

export interface NormalizedClientError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  retryable: boolean;
  statusCode?: number;
}

export const ERROR_MAPPINGS: Record<string, ErrorMessage> = {
  NOT_FOUND: {
    vi: "Không tìm thấy tài nguyên yêu cầu.",
    en: "The requested resource was not found.",
  },
  FORBIDDEN: {
    vi: "Bạn không có quyền thực hiện thao tác này.",
    en: "You do not have permission to perform this action.",
  },
  UNAUTHORIZED: {
    vi: "Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Hãy xác thực lại.",
    en: "The authentication session is invalid or expired. Authenticate again.",
  },
  CONFLICT: {
    vi: "Dữ liệu bị trùng lặp hoặc xung đột phiên bản.",
    en: "Resource conflict or version mismatch.",
  },
  COMPANY_DUPLICATE_REVIEW_REQUIRED: {
    vi: "Phát hiện doanh nghiệp có nguy cơ trùng lặp. Cần người xem xét xác nhận.",
    en: "Potential duplicate company detected. Reviewer confirmation required.",
  },
  COMPANY_ENTITY_AMBIGUOUS: {
    vi: "Thông tin danh tính doanh nghiệp chưa rõ ràng.",
    en: "Company identity is ambiguous.",
  },
  RESEARCH_JOB_ALREADY_ACTIVE: {
    vi: "Đã có tác vụ nghiên cứu đang chạy cho doanh nghiệp này.",
    en: "A research job is already running for this company.",
  },
  SOURCE_BLOCKED_BY_POLICY: {
    vi: "Nguồn dữ liệu bị chặn theo chính sách của hệ thống.",
    en: "Source domain is blocked by system policy.",
  },
  SOURCE_FETCH_SSRF_BLOCKED: {
    vi: "Địa chỉ truy cập bị chặn vì lý do an toàn mạng (SSRF).",
    en: "Fetch target blocked by network security policy (SSRF).",
  },
  AI_OUTPUT_UNGROUNDED: {
    vi: "Dữ liệu trích xuất từ AI không khớp với bằng chứng nguồn.",
    en: "AI extracted output is not supported by source evidence.",
  },
  FACT_EVIDENCE_REQUIRED: {
    vi: "Thông tin bắt buộc phải có bằng chứng xác thực kèm theo.",
    en: "Every accepted fact requires supported evidence.",
  },
  CONFLICT_REVIEW_REQUIRED: {
    vi: "Tồn tại xung đột dữ liệu cần người xem xét xử lý trước khi xuất bản.",
    en: "Unresolved data conflict requires reviewer resolution before publication.",
  },
  PROFILE_PUBLICATION_BLOCKED: {
    vi: "Chưa thể xuất bản hồ sơ do còn điều kiện chưa thỏa mãn.",
    en: "Profile publication is blocked by incomplete mandatory fields or conflicts.",
  },
  REVIEW_VERSION_CONFLICT: {
    vi: "Phiên bản hồ sơ đã được thay đổi bởi người dùng khác.",
    en: "Profile version was modified by another reviewer.",
  },
  INTERNAL_ERROR: {
    vi: "Hệ thống gặp lỗi không mong muốn. Vui lòng thử lại sau.",
    en: "An unexpected system error occurred. Please try again later.",
  },
  NETWORK_ERROR: {
    vi: "Không kết nối được tới API. Hãy kiểm tra backend và thử lại.",
    en: "The API could not be reached. Check the backend and try again.",
  },
  AUTH_NOT_CONFIGURED: {
    vi: "Chưa cấu hình phiên đăng nhập cho ứng dụng local.",
    en: "No local authentication session is configured.",
  },
  AUTH_USER_PAYLOAD_INVALID: {
    vi: "API trả về dữ liệu phiên đăng nhập không hợp lệ.",
    en: "The API returned an invalid authentication session.",
  },
  SEARCH_PROVIDER_UNAVAILABLE: {
    vi: "Chưa có Search API hoạt động để tìm theo tên doanh nghiệp.",
    en: "No search API is available for name-only company lookup.",
  },
  LIVE_SCRAPE_RETIRED: {
    vi: "Luồng cào trực tiếp cũ đã được tắt vì không bảo đảm bằng chứng. Hãy dùng research job.",
    en: "The old synchronous scraper is disabled because it cannot guarantee evidence. Use a research job.",
  },
  COMPANY_NOT_FOUND: {
    vi: "Không tìm thấy hồ sơ doanh nghiệp trong workspace hiện tại.",
    en: "The company profile was not found in the active workspace.",
  },
};

export function getErrorMessage(code: string, locale: "vi" | "en" = "vi"): string {
  const mapping = ERROR_MAPPINGS[code];
  if (mapping) {
    return mapping[locale];
  }
  return locale === "vi"
    ? `Lỗi không xác định (${code})`
    : `Unknown error (${code})`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Normalize API, network, and unexpected errors without exposing raw payloads. */
export function normalizeClientError(
  error: unknown,
  locale: "vi" | "en" = "vi",
): NormalizedClientError {
  if (isRecord(error) && typeof error.code === "string") {
    const statusCode = typeof error.statusCode === "number" ? error.statusCode : undefined;
    const code =
      error.code === "HTTP_ERROR" && statusCode === 401
        ? "UNAUTHORIZED"
        : error.code === "HTTP_ERROR" && statusCode === 403
          ? "FORBIDDEN"
          : error.code;
    const serverMessage = typeof error.message === "string" ? error.message : "";
    return {
      code,
      message: ERROR_MAPPINGS[code]?.[locale] || serverMessage || getErrorMessage(code, locale),
      details: isRecord(error.details) ? error.details : {},
      retryable: error.retryable === true,
      statusCode,
    };
  }

  if (error instanceof TypeError || (error instanceof Error && error.name === "NetworkError")) {
    const reason = error instanceof Error && error.message ? error.message : "Fetch failed";
    return {
      code: "NETWORK_ERROR",
      message: getErrorMessage("NETWORK_ERROR", locale),
      details: {
        reason,
        next_step: locale === "vi"
          ? "Mở /api/v1/health trên cùng địa chỉ web để kiểm tra proxy API."
          : "Open /api/v1/health on the same web origin to check the API proxy.",
      },
      retryable: true,
    };
  }

  return {
    code: "INTERNAL_ERROR",
    message: getErrorMessage("INTERNAL_ERROR", locale),
    details: {},
    retryable: true,
  };
}

/** Convert safe structured error details into short UI lines. */
export function formatErrorDetails(details: Record<string, unknown>): string[] {
  const lines: string[] = [];
  for (const [key, value] of Object.entries(details)) {
    if (/(secret|token|password|credential|stack|raw|payload|api_key)/i.test(key)) continue;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      lines.push(`${key}: ${String(value)}`);
      continue;
    }
    if (Array.isArray(value)) {
      const safeValues = value.filter(
        (item) => typeof item === "string" || typeof item === "number" || typeof item === "boolean",
      );
      if (safeValues.length > 0) lines.push(`${key}: ${safeValues.join(", ")}`);
    }
  }
  return lines;
}
