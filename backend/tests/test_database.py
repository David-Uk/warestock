import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Organisation, PlatformRole, TenantRole, User, Warehouse, WarehouseRole

settings = get_settings()


@pytest.mark.integration
class TestDatabaseConnection:
    """Test database connectivity."""

    async def test_database_connection(self, db_session: AsyncSession):
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_database_version(self, db_session: AsyncSession):
        result = await db_session.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version


@pytest.mark.integration
class TestMigration:
    """Test that migrations create the expected schema."""

    async def test_tables_exist(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        tables = {row[0] for row in result.fetchall()}

        expected_tables = {"organisations", "warehouses", "users"}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    async def test_organisations_schema(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'organisations'"
            )
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        assert "id" in columns
        assert "name" in columns
        assert "slug" in columns
        assert "settings" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    async def test_warehouses_schema(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'warehouses'"
            )
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        assert "id" in columns
        assert "name" in columns
        assert "location" in columns
        assert "organisation_id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    async def test_users_schema(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'users'"
            )
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        assert "id" in columns
        assert "email" in columns
        assert "hashed_password" in columns
        assert "full_name" in columns
        assert "is_active" in columns
        assert "platform_role" in columns
        assert "tenant_role" in columns
        assert "organisation_id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns


@pytest.mark.integration
class TestModelCreation:
    """Test that models can be created and queried."""

    async def test_create_organisation(self, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        assert org.id is not None
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.created_at is not None

    async def test_create_warehouse(self, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        warehouse = Warehouse(
            name="Main Warehouse",
            location="Building A",
            organisation_id=org.id,
        )
        db_session.add(warehouse)
        await db_session.flush()

        assert warehouse.id is not None
        assert warehouse.name == "Main Warehouse"
        assert warehouse.organisation_id == org.id

    async def test_create_user(self, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            full_name="Test User",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.CYCLE_COUNT_AUDITOR,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.organisation_id == org.id
        assert user.is_active is True

    async def test_create_platform_user(self, db_session: AsyncSession):
        user = User(
            email="admin@warestock.local",
            hashed_password="hashed_password_here",
            full_name="Platform Admin",
            platform_role=PlatformRole.SUPERADMIN,
        )
        db_session.add(user)
        await db_session.flush()

        assert user.id is not None
        assert user.platform_role == PlatformRole.SUPERADMIN
        assert user.is_platform_user is True
        assert user.is_tenant_user is False

    async def test_organisation_relationships(self, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        warehouse = Warehouse(
            name="Main Warehouse",
            organisation_id=org.id,
        )
        db_session.add(warehouse)

        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.WAREHOUSE_MANAGER,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(Organisation)
            .where(Organisation.id == org.id)
            .options(selectinload(Organisation.warehouses), selectinload(Organisation.users))
        )
        org = result.scalar_one()

        assert len(org.warehouses) == 1
        assert len(org.users) == 1
        assert org.warehouses[0].name == "Main Warehouse"
        assert org.users[0].email == "test@example.com"

    async def test_cascade_delete(self, db_session: AsyncSession):
        org = Organisation(name="Test Org", slug="test-org")
        db_session.add(org)
        await db_session.flush()

        warehouse = Warehouse(
            name="Main Warehouse",
            organisation_id=org.id,
        )
        db_session.add(warehouse)

        user = User(
            email="test@example.com",
            hashed_password="hashed_password_here",
            tenant_role=TenantRole.WAREHOUSE_STAFF,
            warehouse_role=WarehouseRole.INVENTORY_CONTROLLER,
            organisation_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        await db_session.delete(org)
        await db_session.flush()

        from sqlalchemy import select

        result = await db_session.execute(select(Warehouse).where(Warehouse.organisation_id == org.id))
        assert result.scalars().first() is None

        result = await db_session.execute(select(User).where(User.organisation_id == org.id))
        assert result.scalars().first() is None
