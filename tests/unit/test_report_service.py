from app.services.report_service import ReportService


class UserStub:
    def __init__(self, user_id):
        self.id = user_id


def test_create_report_returns_created_payload(db_session):
    service = ReportService(db_session)
    data = service.create_report(
        user=UserStub(1),
        payload={
            "name": "张三",
            "school_name": "北京大学",
            "study_path_priority": ["国内读研"],
            "employment_intention": ["名企大厂"],
            "target_major": ["软件工程"],
            "target_work_city": ["北京"],
        },
    )

    assert data["name"] == "张三"
    assert data["status"] == "draft"
    assert data["report_type"] == "preview"
    assert data["report_id"] > 0

