"""Service for Innovation Program Fit Assessment calculation, explainability, and reviewer overrides."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.fact import FactCandidate
from company_profile.db.models.fit_assessment import ProgramFitAssessment


class ProgramFitAssessmentService:
    """Rules-based explainable program fit assessment engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate_program_fit(
        self,
        workspace_id: uuid.UUID,
        company_id: uuid.UUID,
        program_name: str = "AI Riser Innovation Accelerator 2026",
    ) -> ProgramFitAssessment:
        """Evaluate company eligibility against program criteria with evidence references."""
        # 1. Fetch company profile
        query = select(CompanyProfile).where(
            CompanyProfile.workspace_id == workspace_id,
            CompanyProfile.id == company_id,
        )
        res = await self.session.execute(query)
        company = res.scalar_one_or_none()
        if not company:
            raise ValueError(f"Company profile {company_id} not found in workspace.")

        # 2. Fetch accepted facts
        fact_query = select(FactCandidate).where(
            FactCandidate.workspace_id == workspace_id,
            FactCandidate.company_id == company_id,
            FactCandidate.fact_status == "accepted",
        )
        fact_res = await self.session.execute(fact_query)
        facts = list(fact_res.scalars().all())

        # 3. Evaluate criteria
        reasons: list[dict[str, Any]] = []
        matched_count = 0
        total_criteria = 4

        # Criterion 1: Valid legal tax identification
        if company.tax_id:
            matched_count += 1
            reasons.append({
                "criterion": "tax_registration_verified",
                "status": "passed",
                "score": 1.0,
                "explanation": f"Mã số thuế doanh nghiệp hợp lệ ({company.tax_id})",
                "evidence_ref": f"company.tax_id:{company.tax_id}",
            })
        else:
            reasons.append({
                "criterion": "tax_registration_verified",
                "status": "missing",
                "score": 0.0,
                "explanation": "Chưa xác minh mã số thuế hợp lệ",
                "evidence_ref": None,
            })

        # Criterion 2: Verified legal entity name
        if company.legal_name:
            matched_count += 1
            reasons.append({
                "criterion": "legal_name_verified",
                "status": "passed",
                "score": 1.0,
                "explanation": f"Tên pháp lý đã được xác minh: {company.legal_name}",
                "evidence_ref": f"company.legal_name:{company.legal_name}",
            })
        else:
            reasons.append({
                "criterion": "legal_name_verified",
                "status": "missing",
                "score": 0.0,
                "explanation": "Tên pháp lý chính thức cần đối chiếu thêm",
                "evidence_ref": None,
            })

        # Criterion 3: Online Footprint / Website URL
        if company.website_url:
            matched_count += 1
            reasons.append({
                "criterion": "digital_footprint_established",
                "status": "passed",
                "score": 1.0,
                "explanation": f"Hiện diện trực tuyến chính thức qua website: {company.website_url}",
                "evidence_ref": f"company.website_url:{company.website_url}",
            })
        else:
            reasons.append({
                "criterion": "digital_footprint_established",
                "status": "missing",
                "score": 0.0,
                "explanation": "Thiếu website thương mại chính thức",
                "evidence_ref": None,
            })

        # Criterion 4: Facts count threshold
        if len(facts) >= 2:
            matched_count += 1
            reasons.append({
                "criterion": "minimum_fact_density",
                "status": "passed",
                "score": 1.0,
                "explanation": f"Hồ sơ chứa {len(facts)} dữ liệu thực tế đã chấp nhận",
                "evidence_ref": f"facts_count:{len(facts)}",
            })
        else:
            reasons.append({
                "criterion": "minimum_fact_density",
                "status": "missing",
                "score": 0.0,
                "explanation": "Mật độ dữ liệu thực tế chưa đủ ngưỡng tối thiểu",
                "evidence_ref": None,
            })

        fit_score = round(matched_count / total_criteria, 2)
        if fit_score >= 0.75:
            overall_status = "eligible"
        elif fit_score >= 0.5:
            overall_status = "review_recommended"
        else:
            overall_status = "needs_more_data"

        suggested_questions = [
            "Đội ngũ sáng lập có cam kết tham gia toàn thời gian vào chương trình không?",
            "Doanh nghiệp đã hoàn thành đăng ký sở hữu trí tuệ cho sản phẩm lõi chưa?",
            "Kế hoạch tài chính và doanh thu dự kiến trong 12 tháng tới là gì?",
        ]

        assessment_data = {
            "reasons": reasons,
            "matched_criteria": matched_count,
            "total_criteria": total_criteria,
            "suggested_questions": suggested_questions,
            "guidance_disclaimer": "Đánh giá sự phù hợp chương trình chỉ mang tính chất tham khảo hỗ trợ hội đồng, không tự động loại trừ doanh nghiệp.",
        }

        assessment = ProgramFitAssessment(
            workspace_id=workspace_id,
            company_id=company_id,
            program_name=program_name,
            overall_fit_status=overall_status,
            fit_score=fit_score,
            assessment_json=assessment_data,
        )
        self.session.add(assessment)
        await self.session.flush()
        return assessment

    async def list_assessments(
        self, workspace_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[ProgramFitAssessment]:
        """List all program fit assessments for a company profile."""
        query = (
            select(ProgramFitAssessment)
            .where(
                ProgramFitAssessment.workspace_id == workspace_id,
                ProgramFitAssessment.company_id == company_id,
            )
            .order_by(ProgramFitAssessment.created_at.desc())
        )
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def apply_reviewer_override(
        self,
        workspace_id: uuid.UUID,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
        override_status: str,
        notes: str | None = None,
    ) -> ProgramFitAssessment:
        """Apply human reviewer decision override without automatic rejections."""
        valid_statuses = {"eligible", "review_recommended", "ineligible", "needs_more_data"}
        if override_status not in valid_statuses:
            raise ValueError(f"Invalid override status. Allowed: {valid_statuses}")

        query = select(ProgramFitAssessment).where(
            ProgramFitAssessment.workspace_id == workspace_id,
            ProgramFitAssessment.id == assessment_id,
        )
        res = await self.session.execute(query)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found in workspace.")

        assessment.reviewer_override_status = override_status
        assessment.reviewer_notes = notes
        assessment.reviewed_by = user_id

        await self.session.flush()
        return assessment
