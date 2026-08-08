"""Seed script for populating deterministic demo company profiles for competition live demonstration."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from company_profile.config.settings import get_settings
from company_profile.db.models.company import CompanyProfile
from company_profile.db.models.identity import User, Workspace, WorkspaceMember
from company_profile.modules.drafts.service import ProfileDraftService
from company_profile.modules.facts.repository import FactCandidateRepository
from company_profile.modules.publication.service import PublicationService
from company_profile.modules.review.service import ReviewTaskService


async def seed_demo_data(db_url: str | None = None) -> None:
    """Populate database with demo companies, candidates, review tasks, and published profiles."""
    settings = get_settings()
    url = db_url or settings.database_url
    if url.startswith("postgresql") and "postgres:5432" in url:
        url = "sqlite+aiosqlite:///./data/demo_seed.db"

    engine = create_async_engine(url)
    if "sqlite" in url:
        from company_profile.db.base import Base
        import company_profile.db.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Create Demo Workspace & Admin User
        ws_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        user_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

        ws = Workspace(id=ws_id, name="AI Riser Competition Workspace", slug="ai-riser-demo")
        usr = User(
            id=user_id,
            auth_provider="mock",
            auth_subject="sub-demo-admin",
            email="demo.admin@example.com",
            display_name="Demo Admin",
        )
        member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="workspace_admin")

        session.add_all([ws, usr, member])
        await session.flush()

        # 2. Company 1: FPT Corporation (Published Profile)
        cp1 = CompanyProfile(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            workspace_id=ws_id,
            company_name="FPT Corporation",
            normalized_name="fpt corporation",
            tax_id="0101245200",
            legal_name="Tập đoàn FPT",
            website_url="https://fpt.com.vn",
            status="published",
        )
        session.add(cp1)
        await session.flush()

        fact_repo = FactCandidateRepository(session)

        cand1 = await fact_repo.create_candidate(
            workspace_id=ws_id,
            company_id=cp1.id,
            field_key="identity.legal_name",
            value={"name": "Tập đoàn FPT"},
            confidence_score=0.98,
            confidence_explanation="Xác nhận qua Cổng thông tin đăng ký doanh nghiệp quốc gia",
        )
        cand1.display_value = "Tập đoàn FPT"
        cand1.fact_status = "accepted"

        cand2 = await fact_repo.create_candidate(
            workspace_id=ws_id,
            company_id=cp1.id,
            field_key="overview.description",
            value="FPT là tập đoàn công nghệ thông tin và viễn thông hàng đầu Việt Nam.",
            confidence_score=0.95,
        )
        cand2.display_value = "FPT là tập đoàn công nghệ thông tin và viễn thông hàng đầu Việt Nam."
        cand2.fact_status = "accepted"
        await session.flush()

        draft_svc = ProfileDraftService(session)
        draft1 = await draft_svc.assemble_draft(ws_id, cp1.id, title="Hồ Sơ Doanh Nghiệp FPT v1.0")
        pub_svc = PublicationService(session)
        await pub_svc.publish_draft(ws_id, draft1.id, user_id, "Xuất bản hồ sơ xác minh chính thức")

        # 3. Company 2: VinFast LLC (Review Inbox Task)
        cp2 = CompanyProfile(
            id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
            workspace_id=ws_id,
            company_name="VinFast LLC",
            normalized_name="vinfast llc",
            tax_id="0108922577",
            legal_name="Công ty TNHH Kinh doanh Thương mại và Dịch vụ VinFast",
            status="draft",
        )
        session.add(cp2)
        await session.flush()

        review_svc = ReviewTaskService(session)
        await review_svc.create_task(
            workspace_id=ws_id,
            company_id=cp2.id,
            task_type="identity_ambiguity",
            title="Xác minh địa chỉ trụ sở chính VinFast",
            description="Kiểm tra đối chiếu địa chỉ đăng ký giữa Cổng ĐKKD và báo cáo thường niên",
            priority="high",
        )

        await session.commit()
        print(f"[SUCCESS] Demo data seeded successfully for workspace {ws_id}.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
