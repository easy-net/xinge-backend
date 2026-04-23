from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.school import College, School


class SchoolRepository:
    def __init__(self, db: Session):
        self.db = db

    def search(self, *, keyword=None, city=None, is_985=None, is_211=None, page=1, page_size=20):
        stmt = select(School)
        if keyword:
            stmt = stmt.where(School.name.contains(keyword))
        if city:
            stmt = stmt.where(School.city == city)
        if is_985 is not None:
            stmt = stmt.where(School.is_985 == is_985)
        if is_211 is not None:
            stmt = stmt.where(School.is_211 == is_211)
        total = len(self.db.execute(stmt).scalars().all())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def get_by_name(self, name: str):
        stmt = (
            select(School)
            .options(selectinload(School.colleges).selectinload(College.majors))
            .where(School.name == name)
        )
        return self.db.execute(stmt).scalar_one_or_none()
