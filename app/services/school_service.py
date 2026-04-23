from app.core.errors import NotFoundError
from app.repositories.school_repository import SchoolRepository


class SchoolService:
    def __init__(self, db):
        self.repository = SchoolRepository(db)

    def search(self, body):
        items, total = self.repository.search(
            keyword=body.keyword,
            city=body.city,
            is_985=body.is_985,
            is_211=body.is_211,
            page=body.page,
            page_size=body.page_size,
        )
        return {
            "list": [
                {
                    "city": item.city,
                    "city_level": item.city_level,
                    "is_211": item.is_211,
                    "is_985": item.is_985,
                    "is_double_first_class": item.is_double_first_class,
                    "name": item.name,
                    "school_level_tag": item.school_level_tag,
                    "school_score": item.school_score,
                }
                for item in items
            ],
            "page": body.page,
            "page_size": body.page_size,
            "page_total": (total + body.page_size - 1) // body.page_size if body.page_size else 0,
            "total": total,
        }

    def detail(self, school_name: str):
        school = self.repository.get_by_name(school_name)
        if school is None:
            raise NotFoundError(message="school not found")
        return {
            "city": school.city,
            "city_level": school.city_level,
            "colleges": [
                {
                    "college_score": college.college_score,
                    "name": college.name,
                    "majors": [
                        {
                            "major_score": major.major_score,
                            "major_type": major.major_type,
                            "name": major.name,
                        }
                        for major in college.majors
                    ],
                }
                for college in school.colleges
            ],
            "is_211": school.is_211,
            "is_985": school.is_985,
            "is_double_first_class": school.is_double_first_class,
            "name": school.name,
            "school_level_tag": school.school_level_tag,
            "school_score": school.school_score,
        }

