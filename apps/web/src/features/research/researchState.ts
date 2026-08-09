export interface TaskStep {
  id: string;
  step_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  completed_at?: string | null;
  output_payload?: string | null;
  error_message?: string | null;
}

export interface PipelineState {
  result_status?: string;
  warnings?: string[];
  source_discovery_warnings?: string[];
  source_candidates?: unknown[];
  selected_sources?: unknown[];
  fetched_sources?: unknown[];
  parsed_snapshots?: Array<{ block_count?: number }>;
  deterministic_fact_count?: number;
  review_task_count?: number;
  review_task_ids?: string[];
  source_provider_outcomes?: Array<{
    provider?: string;
    outcome?: string;
    reason?: string;
  }>;
  ai?: {
    status?: string;
    reason?: string;
    semantic_extraction?: string;
    translation?: string;
    comparison?: string;
    summary?: string;
  };
}

export const PIPELINE_STEPS = [
  ["entity_resolution", "Entity resolved"],
  ["source_discovery", "Sources discovered"],
  ["source_selection", "Sources selected"],
  ["source_fetch", "Sources fetched"],
  ["document_parse", "Document blocks parsed"],
  ["deterministic_extraction", "Deterministic facts extracted"],
  ["ai_extraction", "Optional AI extraction"],
  ["fact_processing", "Conflicts and review"],
  ["finalize", "Research finalized"],
] as const;

const STEP_RANK = new Map<string, number>(
  PIPELINE_STEPS.map(([step], index) => [step, index]),
);

export function parsePipelineState(tasks: TaskStep[] | undefined): PipelineState {
  let best: { rank: number; completedAt: string; state: PipelineState } | null = null;
  for (const task of tasks || []) {
    if (!task.output_payload) continue;
    try {
      const value: unknown = JSON.parse(task.output_payload);
      if (!value || typeof value !== "object" || Array.isArray(value)) continue;
      const candidate = {
        rank: STEP_RANK.get(task.step_type) ?? -1,
        completedAt: task.completed_at || "",
        state: value as PipelineState,
      };
      if (
        best === null ||
        candidate.rank > best.rank ||
        (candidate.rank === best.rank && candidate.completedAt > best.completedAt)
      ) {
        best = candidate;
      }
    } catch {
      // A task can be running before its durable output exists.
    }
  }
  return best?.state || {};
}

function diagnosticGroup(value: string): string {
  if (value.startsWith("SEARCH_PROVIDER_UNAVAILABLE:")) return "SEARCH_PROVIDER_UNAVAILABLE";
  return value;
}

export function deduplicateDiagnostics(values: string[]): string[] {
  const seen = new Set<string>();
  return values.filter((value) => {
    const group = diagnosticGroup(value);
    if (seen.has(group)) return false;
    seen.add(group);
    return true;
  });
}

export function aiUnavailableMessage(reason?: string): string {
  const messages: Record<string, string> = {
    AI_QUOTA_EXCEEDED:
      "Gemini đã hết hoặc chưa được cấp quota cho project/model hiện tại. Kiểm tra quota và billing trong Google AI Studio rồi chạy lại; dữ liệu deterministic vẫn được giữ nguyên.",
    AI_AUTHENTICATION_FAILED:
      "Gemini từ chối thông tin xác thực. Kiểm tra GEMINI_API_KEY ở backend rồi build lại API/worker.",
    AI_MODEL_NOT_FOUND:
      "Gemini model đã cấu hình không tồn tại hoặc project không được phép sử dụng. Kiểm tra GEMINI_MODEL.",
    AI_REQUEST_REJECTED:
      "Gemini từ chối request. Kiểm tra model, giới hạn input và cấu hình provider.",
    AI_TIMEOUT:
      "Gemini không phản hồi trong thời gian cho phép. Kiểm tra kết nối hoặc tăng AI_TIMEOUT có kiểm soát.",
    AI_PROVIDER_SDK_UNAVAILABLE:
      "Worker thiếu thư viện Gemini runtime. Build lại image API/worker từ dependency hiện tại.",
    AI_PROVIDER_UNAVAILABLE:
      "Không kết nối được Gemini sau số lần thử cho phép. Kiểm tra trạng thái provider và network của worker.",
    AI_DISABLED:
      "AI đang tắt theo cấu hình. Pipeline deterministic vẫn hoạt động độc lập.",
    GEMINI_KEY_MISSING:
      "Backend chưa có GEMINI_API_KEY. Thêm key vào .env rồi build lại API/worker.",
  };
  return messages[reason || ""] || "AI không hoàn tất; hãy xem mã chẩn đoán và log worker.";
}

export function diagnosticLabel(diagnostic: string): string {
  if (diagnostic.includes("GOOGLE_CONFIGURATION_MISSING")) {
    return "Search theo tên chưa chạy: backend thiếu SEARCH_API_KEY hoặc SEARCH_ENGINE_ID.";
  }
  if (
    diagnostic.includes("SEARCH_PROVIDER_UNAVAILABLE:DISABLED") ||
    diagnostic.includes("NOT_CONFIGURED") ||
    diagnostic.includes("FIXTURE_DISABLED_IN_RUNTIME")
  ) {
    return "Search API đang tắt. Đây là giới hạn cấu hình; website chính thức vẫn có thể được crawl.";
  }
  if (diagnostic.startsWith("AI_EXTRACTION_FAILED:")) {
    return aiUnavailableMessage(diagnostic.slice("AI_EXTRACTION_FAILED:".length));
  }
  if (diagnostic.includes("TRUSTED_PROVIDER_MANUAL_REQUIRED:dangkykinhdoanh:")) {
    return "Đăng ký kinh doanh chưa có endpoint công khai ổn định được phê duyệt; cần tra cứu thủ công.";
  }
  if (diagnostic.includes("TRUSTED_PROVIDER_MANUAL_REQUIRED:tracuunnt_gdt:CAPTCHA_REQUIRED")) {
    return "Tra cứu người nộp thuế yêu cầu CAPTCHA; hệ thống không bypass và cần người dùng kiểm tra thủ công.";
  }
  if (diagnostic.includes("TRUSTED_PROVIDER_MANUAL_REQUIRED:vietstock:")) {
    return "Vietstock chưa có endpoint tìm doanh nghiệp công khai, ổn định và được tài liệu hóa; cần tra cứu thủ công.";
  }
  if (diagnostic.startsWith("TRUSTED_PROVIDER_MANUAL_REQUIRED:")) {
    return "Nguồn tin cậy này yêu cầu thao tác thủ công hoặc chưa thể tự động hóa hợp lệ.";
  }
  if (diagnostic.startsWith("REVIEW_REQUIRED_CONFLICTS:")) {
    const count = diagnostic.split(":").at(-1) || "0";
    return `Phát hiện ${count} trường có bằng chứng mâu thuẫn; xử lý trong Review Inbox. Đây không phải lỗi hệ thống.`;
  }
  if (diagnostic.startsWith("REVIEW_REQUIRED:")) {
    const count = diagnostic.split(":").at(-1) || "0";
    return `Có ${count} mục cần người dùng xác minh trong Review Inbox. Đây không phải lỗi hệ thống.`;
  }
  if (diagnostic.includes("NO_SOURCE_CANDIDATES")) {
    return "Không tìm thấy URL nguồn phù hợp từ các nguồn được phép.";
  }
  if (diagnostic.includes("NO_SELECTED_SOURCES")) {
    return "Các URL phát hiện được không vượt qua kiểm tra an toàn hoặc khớp danh tính.";
  }
  if (diagnostic.includes("NO_FETCHED_SOURCES")) {
    return "Không tải được nguồn nào; kiểm tra URL, robots.txt, trạng thái website và network policy.";
  }
  if (diagnostic.includes("NO_EVIDENCE_ACQUIRED")) {
    return "Chưa có snapshot/bằng chứng được lưu. Không có dữ liệu kết quả nào được bịa thêm.";
  }
  if (diagnostic.includes("NO_SUPPORTED_FIELDS_EXTRACTED")) {
    return "Nguồn đã tải nhưng chưa có trường được bộ trích xuất deterministic hỗ trợ; cần xem evidence.";
  }
  if (diagnostic.includes("OFFICIAL_WEBSITE_INVALID_URL")) {
    return "Website không hợp lệ. Dùng URL công khai bắt đầu bằng http:// hoặc https://.";
  }
  if (diagnostic.includes("ROBOTS_")) {
    return "Website không cho phép truy cập theo robots policy; hệ thống không bypass hạn chế này.";
  }
  return diagnostic;
}
