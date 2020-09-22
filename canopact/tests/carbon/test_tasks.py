"""Tests for carbon tasks"""

from canopact.blueprints.carbon.tasks import calculate_carbon
from canopact.blueprints.carbon.models.expense import Carbon
from canopact.blueprints.carbon.models.route import Route


def test_calculate_carbon(reports, expenses, carbons, routes):
    """Test for calculate_carbons()

    Args:
        reports (pytest.fixture): fixture for reports using test db.
        expenses (pytest.fixture): fixture for reports using test db.
        carbons (pytest.fixture): fixture for reports using test db.

    """

    og_cbn_cnt = carbons.session.query(Carbon).count()
    og_route_cnt = routes.session.query(Route).count()

    # Calculate carbon to add new record to tables.
    calculate_carbon()
    new_route_cnt = routes.session.query(Route).count()
    new_cbn_cnt = carbons.session.query(Carbon).count()

    assert new_route_cnt == og_route_cnt + 1
    assert new_cbn_cnt == og_cbn_cnt + 1
