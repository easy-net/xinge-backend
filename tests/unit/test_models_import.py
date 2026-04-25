from app.db.models import Message, Order, PaymentCallback, ProductConfig, Report, School, User, UserDevice


def test_models_are_registered_on_metadata():
    table_names = {
        User.__tablename__,
        UserDevice.__tablename__,
        School.__tablename__,
        ProductConfig.__tablename__,
        Report.__tablename__,
        Order.__tablename__,
        PaymentCallback.__tablename__,
        Message.__tablename__,
    }
    assert "mp_users" in table_names
    assert "mp_user_devices" in table_names
    assert "schools" in table_names
    assert "product_configs" in table_names
    assert "reports" in table_names
    assert "orders" in table_names
    assert "payment_callbacks" in table_names
    assert "messages" in table_names
