from sqlalchemy import insert, update

from workspace_api import tables as t


def idn(n):
    return f"00000000-0000-0000-0000-{n:012d}"


def test_me_exposes_enterprise_role_for_delivery_manager(client, headers):
    response = client.get("/api/v1/team/me", headers=headers("manager-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "manager"
    assert body["business_role"] == "delivery_manager"
    assert body["system_admin"] is False


def test_me_exposes_executive_and_system_admin_for_legacy_admin(client, headers):
    response = client.get("/api/v1/team/me", headers=headers("admin-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["business_role"] == "executive"
    assert body["system_admin"] is True


def test_explicit_access_profile_separates_executive_from_system_admin(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.access_profiles).values(
            user_id=idn(13),
            tenant_id=idn(1),
            business_role="executive",
            system_admin=False,
            created_at=__import__("workspace_api.store", fromlist=["now"]).now(),
            updated_at=__import__("workspace_api.store", fromlist=["now"]).now(),
        ))

    response = client.get("/api/v1/team/me", headers=headers("admin-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["business_role"] == "executive"
    assert body["system_admin"] is False


def test_explicit_system_admin_is_permission_not_business_role(client, headers, seeded):
    with seeded.begin() as conn:
        conn.execute(insert(t.access_profiles).values(
            user_id=idn(12),
            tenant_id=idn(1),
            business_role="delivery_manager",
            system_admin=True,
            created_at=__import__("workspace_api.store", fromlist=["now"]).now(),
            updated_at=__import__("workspace_api.store", fromlist=["now"]).now(),
        ))

    response = client.get("/api/v1/team/me", headers=headers("manager-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["business_role"] == "delivery_manager"
    assert body["system_admin"] is True
