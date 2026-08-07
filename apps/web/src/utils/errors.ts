/**
 * Frontend error code mappings and message localization.
 */

export interface ErrorMessage {
  vi: string;
  en: string;
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
