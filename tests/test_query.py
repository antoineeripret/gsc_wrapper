import pytest
import random
import datetime
import pandas as pd
from gscwrapper.auth import generate_auth
from gscwrapper.account import Account

@pytest.mark.usefixtures("client_secret_dict", "credentials_dict")
def test_query_random_property(client_secret_dict, credentials_dict):
    """
    Test that the Account lists at least one property,
    can run a query for a random property, and retrieves at least one row.
    """
    # Generate authenticated account
    account = generate_auth(
        client_config=client_secret_dict,
        credentials=credentials_dict
    )
    assert isinstance(account, Account)

    # Ensure account has at least one property
    properties = account.list_webproperties()
    assert isinstance(properties, pd.DataFrame)
    assert not properties.empty, "No properties found for the account"

    # Pick a random property
    property_obj = random.choice(properties['siteUrl'].tolist())
    print(f'chosen property: {property_obj}')
    property_url = account[property_obj]

    # Prepare query parameters (last 30 days)
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    # Query data for the property
    results = (
        property_url
        .query
        .range(start=start_date, stop=end_date)
        .dimensions(["date"])
        .get()
        .show_data()
    )
    assert len(results) > 0, "No row data returned by show_data()"

