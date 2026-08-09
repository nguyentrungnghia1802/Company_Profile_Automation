"""Meeting brief generator for 1-minute executive briefs strictly grounded in published fields."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from company_profile.db.models.publication import ProfileVersion


class MeetingBriefGenerator:
    """Generator for grounded 1-minute executive meeting briefs in VI/EN."""

    def generate_brief(self, profile: ProfileVersion, locale: str = "vi") -> dict[str, Any]:
        """Generate structured meeting brief from published profile payload."""
        fields_map = {
            f"{fv.field_key}:{fv.context_key}": fv.display_value
            or (str(fv.get_value()) if fv.get_value() else "")
            for fv in profile.field_values
        }

        legal_name = fields_map.get("identity.legal_name:", profile.title)
        industry = fields_map.get(
            "identity.industry:", fields_map.get("overview.industry:", "Commercial Entity")
        )
        description = fields_map.get("overview.description:", profile.executive_summary)
        tax_id = fields_map.get("identity.tax_id:", "N/A")
        website = fields_map.get("identity.website:", "N/A")
        employee_range = fields_map.get("size.employee_range:", "N/A")

        missing_sections = []
        if "identity.tax_id:" not in fields_map:
            missing_sections.append("tax_id")
        if "overview.description:" not in fields_map:
            missing_sections.append("overview_description")
        if "size.employee_range:" not in fields_map:
            missing_sections.append("employee_size")

        is_vi = locale.startswith("vi")

        # Suggested verification questions (strictly labeled as guidance)
        suggested_questions = []
        if is_vi:
            suggested_questions.append(
                f"Xác nhận tên pháp lý chính thức và mã số thuế hiện tại ({tax_id})."
            )
            if "size.employee_range:" in fields_map:
                suggested_questions.append(
                    f"Xác nhận quy mô nhân sự ({employee_range}) và địa bàn hoạt động chính."
                )
            suggested_questions.append(
                "Hỏi về các sản phẩm/dịch vụ chủ lực đang triển khai trong năm nay."
            )
        else:
            suggested_questions.append(
                f"Verify official legal name and tax registration ID ({tax_id})."
            )
            if "size.employee_range:" in fields_map:
                suggested_questions.append(
                    f"Confirm headcount footprint ({employee_range}) and primary market presence."
                )
            suggested_questions.append(
                "Inquire about flagship products/services actively offered this year."
            )

        header_title = (
            f"Tóm Tắt Cuộc Họp: {legal_name}" if is_vi else f"Executive Meeting Brief: {legal_name}"
        )

        return {
            "company_id": str(profile.company_id),
            "profile_version_id": str(profile.id),
            "version_number": profile.version_number,
            "locale": locale,
            "title": header_title,
            "legal_name": legal_name,
            "industry": industry,
            "description": description,
            "key_metrics": {
                "tax_id": tax_id,
                "website": website,
                "employee_range": employee_range,
                "overall_confidence": profile.overall_confidence,
                "evidence_count": profile.evidence_count,
            },
            "executive_summary": profile.executive_summary,
            "missing_sections": missing_sections,
            "suggested_verification_questions": suggested_questions,
            "disclaimer": (
                "Lưu ý: Các câu hỏi gợi ý là hướng dẫn hỗ trợ cuộc họp, "
                "không phải sự thật được khẳng định."
                if is_vi
                else "Notice: Suggested questions are meeting guidance prompts, "
                "not factual assertions."
            ),
        }
