import { describe, expect, test } from "bun:test";
import {
  aiUnavailableMessage,
  deduplicateDiagnostics,
  diagnosticLabel,
  parsePipelineState,
} from "../src/features/research/researchState";

describe("research pipeline state", () => {
  test("selects the most advanced durable task regardless of API array order", () => {
    const early = JSON.stringify({ source_candidates: [] });
    const final = JSON.stringify({
      fetched_sources: [{ snapshot_id: "snapshot-1" }],
      deterministic_fact_count: 115,
      review_task_count: 14,
    });

    const state = parsePipelineState([
      {
        id: "final",
        step_type: "finalize",
        status: "completed",
        attempt_count: 1,
        max_attempts: 3,
        output_payload: final,
      },
      {
        id: "discovery",
        step_type: "source_discovery",
        status: "completed",
        attempt_count: 1,
        max_attempts: 3,
        output_payload: early,
      },
    ]);

    expect(state.deterministic_fact_count).toBe(115);
    expect(state.fetched_sources).toHaveLength(1);
    expect(state.review_task_count).toBe(14);
  });

  test("collapses equivalent disabled and unconfigured search diagnostics", () => {
    expect(
      deduplicateDiagnostics([
        "SEARCH_PROVIDER_UNAVAILABLE:DISABLED",
        "SEARCH_PROVIDER_UNAVAILABLE:NOT_CONFIGURED",
        "NO_SELECTED_SOURCES",
      ]),
    ).toEqual(["SEARCH_PROVIDER_UNAVAILABLE:DISABLED", "NO_SELECTED_SOURCES"]);
  });

  test("explains Gemini quota exhaustion without generic provider wording", () => {
    expect(aiUnavailableMessage("AI_QUOTA_EXCEEDED")).toContain("quota");
    expect(
      diagnosticLabel("AI_EXTRACTION_FAILED:AI_QUOTA_EXCEEDED"),
    ).toContain("Google AI Studio");
  });

  test("describes manual providers and review conflicts as expected limitations", () => {
    expect(
      diagnosticLabel(
        "TRUSTED_PROVIDER_MANUAL_REQUIRED:tracuunnt_gdt:CAPTCHA_REQUIRED",
      ),
    ).toContain("không bypass");
    expect(diagnosticLabel("REVIEW_REQUIRED_CONFLICTS:2")).toContain(
      "không phải lỗi hệ thống",
    );
    expect(diagnosticLabel("REVIEW_REQUIRED:9")).toContain("Review Inbox");
  });
});
