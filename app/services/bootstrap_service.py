import app.db.models  # noqa: F401
from sqlalchemy import inspect

from app.db.base import Base
from app.db.models.product_config import ProductConfig
from app.db.models.school import College, Major, School
from app.repositories.product_config_repository import ProductConfigRepository

SCHOOL_FIXTURES = [
    {
        "name": "北京大学",
        "city": "北京",
        "city_level": "一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 98,
        "colleges": [
            {
                "name": "信息科学技术学院",
                "college_score": 96,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 97},
                    {"name": "软件工程", "major_type": "工学", "major_score": 95},
                    {"name": "人工智能", "major_type": "工学", "major_score": 96},
                ],
            },
            {
                "name": "工学院",
                "college_score": 92,
                "majors": [
                    {"name": "电子信息工程", "major_type": "工学", "major_score": 91},
                    {"name": "智能制造工程", "major_type": "工学", "major_score": 89},
                    {"name": "机器人工程", "major_type": "工学", "major_score": 90},
                ],
            },
        ],
    },
    {
        "name": "清华大学",
        "city": "北京",
        "city_level": "一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 99,
        "colleges": [
            {
                "name": "计算机系",
                "college_score": 97,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 98},
                    {"name": "数据科学与大数据技术", "major_type": "工学", "major_score": 95},
                    {"name": "人工智能", "major_type": "工学", "major_score": 97},
                ],
            },
            {
                "name": "电子工程系",
                "college_score": 94,
                "majors": [
                    {"name": "电子信息工程", "major_type": "工学", "major_score": 94},
                    {"name": "通信工程", "major_type": "工学", "major_score": 92},
                    {"name": "微电子科学与工程", "major_type": "工学", "major_score": 93},
                ],
            },
        ],
    },
    {
        "name": "复旦大学",
        "city": "上海",
        "city_level": "一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 95,
        "colleges": [
            {
                "name": "计算机科学技术学院",
                "college_score": 92,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 93},
                    {"name": "信息安全", "major_type": "工学", "major_score": 88},
                    {"name": "人工智能", "major_type": "工学", "major_score": 91},
                ],
            },
            {
                "name": "管理学院",
                "college_score": 90,
                "majors": [
                    {"name": "工商管理", "major_type": "管理学", "major_score": 89},
                    {"name": "市场营销", "major_type": "管理学", "major_score": 86},
                    {"name": "信息管理与信息系统", "major_type": "管理学", "major_score": 87},
                ],
            },
        ],
    },
    {
        "name": "上海交通大学",
        "city": "上海",
        "city_level": "一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 96,
        "colleges": [
            {
                "name": "电子信息与电气工程学院",
                "college_score": 94,
                "majors": [
                    {"name": "自动化", "major_type": "工学", "major_score": 90},
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 95},
                    {"name": "软件工程", "major_type": "工学", "major_score": 93},
                ],
            },
            {
                "name": "机械与动力工程学院",
                "college_score": 90,
                "majors": [
                    {"name": "机械工程", "major_type": "工学", "major_score": 88},
                    {"name": "能源与动力工程", "major_type": "工学", "major_score": 87},
                    {"name": "工业工程", "major_type": "工学", "major_score": 85},
                ],
            },
        ],
    },
    {
        "name": "浙江大学",
        "city": "杭州",
        "city_level": "新一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 94,
        "colleges": [
            {
                "name": "计算机科学与技术学院",
                "college_score": 93,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 95},
                    {"name": "人工智能", "major_type": "工学", "major_score": 94},
                    {"name": "数字媒体技术", "major_type": "工学", "major_score": 88},
                ],
            },
            {
                "name": "控制科学与工程学院",
                "college_score": 89,
                "majors": [
                    {"name": "自动化", "major_type": "工学", "major_score": 89},
                    {"name": "机器人工程", "major_type": "工学", "major_score": 87},
                    {"name": "智能科学与技术", "major_type": "工学", "major_score": 88},
                ],
            },
        ],
    },
    {
        "name": "南京大学",
        "city": "南京",
        "city_level": "新一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 92,
        "colleges": [
            {
                "name": "软件学院",
                "college_score": 90,
                "majors": [
                    {"name": "软件工程", "major_type": "工学", "major_score": 92},
                    {"name": "人工智能", "major_type": "工学", "major_score": 91},
                    {"name": "信息管理与信息系统", "major_type": "管理学", "major_score": 85},
                ],
            },
            {
                "name": "现代工程与应用科学学院",
                "college_score": 87,
                "majors": [
                    {"name": "电子信息科学与技术", "major_type": "工学", "major_score": 86},
                    {"name": "材料物理", "major_type": "理学", "major_score": 82},
                    {"name": "新能源科学与工程", "major_type": "工学", "major_score": 84},
                ],
            },
        ],
    },
    {
        "name": "武汉大学",
        "city": "武汉",
        "city_level": "新一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 91,
        "colleges": [
            {
                "name": "计算机学院",
                "college_score": 89,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 90},
                    {"name": "网络空间安全", "major_type": "工学", "major_score": 87},
                    {"name": "软件工程", "major_type": "工学", "major_score": 88},
                ],
            },
            {
                "name": "测绘学院",
                "college_score": 88,
                "majors": [
                    {"name": "测绘工程", "major_type": "工学", "major_score": 89},
                    {"name": "遥感科学与技术", "major_type": "工学", "major_score": 87},
                    {"name": "导航工程", "major_type": "工学", "major_score": 86},
                ],
            },
        ],
    },
    {
        "name": "中山大学",
        "city": "广州",
        "city_level": "一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 90,
        "colleges": [
            {
                "name": "电子与信息工程学院",
                "college_score": 88,
                "majors": [
                    {"name": "电子信息工程", "major_type": "工学", "major_score": 88},
                    {"name": "通信工程", "major_type": "工学", "major_score": 86},
                    {"name": "微电子科学与工程", "major_type": "工学", "major_score": 85},
                ],
            },
            {
                "name": "计算机学院",
                "college_score": 89,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 90},
                    {"name": "软件工程", "major_type": "工学", "major_score": 88},
                    {"name": "保密技术", "major_type": "工学", "major_score": 83},
                ],
            },
        ],
    },
    {
        "name": "四川大学",
        "city": "成都",
        "city_level": "新一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 88,
        "colleges": [
            {
                "name": "计算机学院",
                "college_score": 87,
                "majors": [
                    {"name": "计算机科学与技术", "major_type": "工学", "major_score": 88},
                    {"name": "物联网工程", "major_type": "工学", "major_score": 84},
                    {"name": "信息安全", "major_type": "工学", "major_score": 85},
                ],
            },
            {
                "name": "高分子科学与工程学院",
                "college_score": 84,
                "majors": [
                    {"name": "高分子材料与工程", "major_type": "工学", "major_score": 83},
                    {"name": "材料科学与工程", "major_type": "工学", "major_score": 82},
                    {"name": "功能材料", "major_type": "工学", "major_score": 81},
                ],
            },
        ],
    },
    {
        "name": "西安交通大学",
        "city": "西安",
        "city_level": "新一线城市",
        "is_985": True,
        "is_211": True,
        "is_double_first_class": True,
        "school_level_tag": "985/211/双一流",
        "school_score": 89,
        "colleges": [
            {
                "name": "电气工程学院",
                "college_score": 90,
                "majors": [
                    {"name": "电气工程及其自动化", "major_type": "工学", "major_score": 91},
                    {"name": "能源互联网工程", "major_type": "工学", "major_score": 86},
                    {"name": "自动化", "major_type": "工学", "major_score": 87},
                ],
            },
            {
                "name": "人工智能学院",
                "college_score": 88,
                "majors": [
                    {"name": "人工智能", "major_type": "工学", "major_score": 90},
                    {"name": "智能科学与技术", "major_type": "工学", "major_score": 87},
                    {"name": "数据科学与大数据技术", "major_type": "工学", "major_score": 88},
                ],
            },
        ],
    },
]


class BootstrapService:
    def __init__(self, engine, session_factory):
        self.engine = engine
        self.session_factory = session_factory

    def run(self):
        Base.metadata.create_all(self.engine)
        self._patch_legacy_schema()
        session = self.session_factory()
        try:
            repository = ProductConfigRepository(session)
            if repository.get_current() is None:
                session.add(
                    ProductConfig(
                        current_amount=9900,
                        current_amount_display="99.00",
                        description="完整版学业规划报告",
                        discount_rate=0.5,
                        is_limited_time=True,
                        limited_time_end="2026-05-01T00:00:00Z",
                        original_amount=19900,
                        original_amount_display="199.00",
                        display_count=12345,
                        display_text="已有12345位同学使用",
                    )
                )
                session.commit()

            if session.query(School).count() == 0:
                self._seed_schools(session)
                session.commit()
        finally:
            session.close()

    def _patch_legacy_schema(self):
        if self.engine.dialect.name != "sqlite":
            return
        inspector = inspect(self.engine)
        self._ensure_sqlite_columns(
            inspector=inspector,
            table_name="distributor_applications",
            columns={
                "real_name": "VARCHAR(128) NOT NULL DEFAULT ''",
                "phone": "VARCHAR(32) NOT NULL DEFAULT ''",
                "reason": "VARCHAR(255) NOT NULL DEFAULT ''",
            },
        )

    def _ensure_sqlite_columns(self, *, inspector, table_name: str, columns: dict):
        existing_tables = set(inspector.get_table_names())
        if table_name not in existing_tables:
            return
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = {name: ddl for name, ddl in columns.items() if name not in existing_columns}
        if not missing_columns:
            return
        with self.engine.begin() as connection:
            for column_name, ddl in missing_columns.items():
                connection.exec_driver_sql("ALTER TABLE {} ADD COLUMN {} {}".format(table_name, column_name, ddl))

    def _seed_schools(self, session):
        for school_item in SCHOOL_FIXTURES:
            school = School(
                name=school_item["name"],
                city=school_item["city"],
                city_level=school_item["city_level"],
                is_985=school_item["is_985"],
                is_211=school_item["is_211"],
                is_double_first_class=school_item["is_double_first_class"],
                school_level_tag=school_item["school_level_tag"],
                school_score=school_item["school_score"],
            )
            for college_item in school_item["colleges"]:
                college = College(
                    name=college_item["name"],
                    college_score=college_item["college_score"],
                )
                for major_item in college_item["majors"]:
                    college.majors.append(
                        Major(
                            name=major_item["name"],
                            major_type=major_item["major_type"],
                            major_score=major_item["major_score"],
                        )
                    )
                school.colleges.append(college)
            session.add(school)
