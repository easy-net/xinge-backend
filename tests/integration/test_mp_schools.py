from app.db.models.school import College, Major, School


def seed_school(db_session):
    school = School(
        name="北京大学",
        city="北京",
        city_level="一线",
        is_985=True,
        is_211=True,
        is_double_first_class=True,
        school_level_tag="全国强平台",
        school_score=99,
    )
    college = College(name="计算机学院", college_score=95)
    major = Major(name="计算机科学与技术", major_type="计算机类", major_score=47)
    college.majors.append(major)
    school.colleges.append(college)
    db_session.add(school)
    db_session.commit()


def test_mp_schools_list_returns_paginated_results(client, db_session):
    seed_school(db_session)

    response = client.post("/api/v1/mp/schools/list", json={"keyword": "北京", "page": 1, "page_size": 20})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["name"] == "北京大学"


def test_mp_schools_detail_returns_nested_colleges_and_majors(client, db_session):
    seed_school(db_session)

    response = client.post("/api/v1/mp/schools/detail", json={"school_name": "北京大学"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "北京大学"
    assert data["colleges"][0]["majors"][0]["name"] == "计算机科学与技术"

