from sqlalchemy import select

from app.db.models.distributor import DistributorProfile
from app.db.models.user import User


def test_admin_update_distributor_updates_level_and_withdrawable_amount(client, db_session):
    user = User(openid="admin-dist-openid", unionid="admin-dist-unionid", nickname="待修改分销商", role="distributor", is_distributor=True)
    db_session.add(user)
    db_session.flush()
    db_session.add(
        DistributorProfile(
            user_id=user.id,
            distributor_level="city",
            quota_total=50,
            unsettled_commission=1200,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/admin/distributor/users/{user.id}/update",
        json={"distributor_level": "campus", "unsettled_commission": 880000},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "updated"
    assert data["distributor_level"] == "campus"
    assert data["withdrawable_amount"] == 880000

    updated = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == user.id)).scalar_one()
    assert updated.distributor_level == "campus"
    assert updated.unsettled_commission == 880000
