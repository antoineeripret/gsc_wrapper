from . import query, query_bq, sitemap, inspect_url
from google.cloud import bigquery
import pandas as pd
from typing import List, Optional

# Constants
VALID_PERMISSION_LEVELS = [
    'siteFullUser',
    'siteOwner',
    'siteRestrictedUser',
    'siteUnverifiedUser'
]
UNVERIFIED_PERMISSION_INDICATOR = 'Unverified'
DOMAIN_PROPERTY_PREFIX = 'sc-domain'


class AccountBQ:
    def __init__(self, credentials, dataset: str):
        """
        Initialize an AccountBQ object for BigQuery operations.

        Args:
            credentials: Google Cloud credentials object.
            dataset: BigQuery dataset name in format 'project_id.dataset_name'.

        Raises:
            ValueError: If dataset format is invalid.
        """
        if not dataset or not isinstance(dataset, str):
            raise ValueError('Dataset must be a non-empty string.')
        if len(dataset.split('.')) != 2:
            raise ValueError(
                'Dataset name must be in the format project_id.dataset_name'
            )
        self.credentials = credentials
        self.dataset = dataset
        self.client = bigquery.Client(
            credentials=credentials, project=credentials.project_id
        )
        self.tables = self.list_tables()
        self.query = query_bq.Query_BQ(self.credentials, self.dataset)
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the dataset.

        Returns:
            List of table IDs. Returns empty list if no tables exist.
        """
        tables = list(self.client.list_tables(self.dataset))
        if len(tables) > 0:
            attrs = [
                attr for attr in dir(tables[0])
                if not callable(getattr(tables[0], attr))
                and not attr.startswith("_")
            ]
            tables_df = pd.DataFrame(columns=attrs)
            for table in tables:
                tables_df.loc[len(tables_df)] = [
                    getattr(table, element) for element in tables_df.columns
                ]
            return tables_df.table_id.tolist()
        else:
            return []

class Account:
    """
    Represents a Google Search Console account, which can be associated
    with multiple web properties. This class provides methods to interact
    with the account and its web properties.
    """

    def __init__(self, service, credentials):
        """
        Initializes an Account object with the necessary service and
        credentials.

        Args:
            service: The service object used to interact with
                the Google Search Console API.
            credentials: The credentials object used for
                authentication with the Google Search Console API.

        Raises:
            ValueError: If service or credentials are None.
        """
        if service is None:
            raise ValueError('Service cannot be None.')
        if credentials is None:
            raise ValueError('Credentials cannot be None.')
        self.service = service
        self.credentials = credentials
    
    def list_webproperties(
        self,
        permissionLevel: Optional[str] = None,
        is_domain_property: Optional[bool] = None
    ) -> pd.DataFrame:
        """
        Retrieves a list of all web properties associated with the account
        and returns them as a pandas DataFrame. Optionally filters the web
        properties based on the specified permission level and/or whether
        the property is a domain property.

        Args:
            permissionLevel: The permission level to filter by. Supported
                values are: 'siteFullUser', 'siteOwner', 'siteRestrictedUser',
                'siteUnverifiedUser'. If not specified, all web properties
                are returned.
            is_domain_property: If True, only domain properties are returned.
                If False, only non-domain properties are returned. If not
                specified, all web properties are returned regardless of
                their domain property status.

        Returns:
            A DataFrame containing the list of web properties. Each row
            represents a web property.

        Raises:
            ValueError: If permissionLevel is invalid or is_domain_property
                is not a boolean.
            RuntimeError: If API call fails.
        """
        try:
            response = self.service.sites().list().execute()
            accounts = pd.DataFrame(response['siteEntry'])
        except Exception as e:
            raise RuntimeError(
                f'Failed to retrieve web properties: {str(e)}'
            ) from e
        
        # Filter by permissionLevel if specified
        if permissionLevel:
            if permissionLevel not in VALID_PERMISSION_LEVELS:
                raise ValueError(
                    f'Permission level "{permissionLevel}" is not supported. '
                    'Check https://developers.google.com/webmaster-tools/'
                    'v1/sites?hl=en for the accepted values.'
                )
            accounts = accounts.query('permissionLevel == @permissionLevel')
        
        # Filter by is_domain_property if specified
        if is_domain_property is not None:
            if not isinstance(is_domain_property, bool):
                raise ValueError('is_domain_property must be a boolean.')
            accounts = (
                accounts
                .assign(
                    is_domain_property=lambda x: (
                        x.siteUrl.str.startswith(DOMAIN_PROPERTY_PREFIX)
                    )
                )
                .query('is_domain_property == @is_domain_property')
                .drop('is_domain_property', axis=1)
            )
        
        return accounts
    
    def __getitem__(self, item):
        """
        Get a web property by URL string or index.

        Args:
            item: Either a string URL or an integer index.

        Returns:
            Webproperty object for the specified property.

        Raises:
            IndexError: If index is out of range.
            ValueError: If property URL is not found.
        """
        if isinstance(item, str):
            web_properties_df = self.list_webproperties()
            matching_properties = web_properties_df[
                web_properties_df['siteUrl'] == item
            ]
            if matching_properties.empty:
                raise ValueError(
                    f'Web property "{item}" not found. '
                    'Check if you have access to this web property.'
                )
            web_property_url = matching_properties.iloc[0]['siteUrl']
        else:
            web_properties_df = self.list_webproperties()
            if item >= len(web_properties_df) or item < 0:
                raise IndexError(
                    f'Index {item} is out of range. '
                    f'Available properties: 0-{len(web_properties_df) - 1}'
                )
            web_property_url = web_properties_df.iloc[item]['siteUrl']

        return Webproperty(self.service, web_property_url)

    def __repr__(self) -> str:
        return "<searchconsole.account.Account>"


class Webproperty:
    """
    Represents a web property in Google Search Console. This class is used
    to interact with a specific website's data in Search Console,
    enabling the execution of Search Analytics queries and other
    operations related to the web property.

    Attributes:
        service (Service): The service object used for authentication
            and API calls.
        webproperty (str): The URL of the web property.
        url (str): The URL of the web property.
        permission (str): The permission level of the user for the web
            property.
        query (Query): An instance of the Query class for executing
            Search Analytics queries.
        sitemap (Sitemap): An instance of the Sitemap class for managing
            sitemaps.
        inspect (Inspect): An instance of the Inspect class for
            inspecting URLs.
        can_query (bool): Indicates if the user has permission to
            execute Search Analytics queries for the web property.
    """
    def __init__(self, service, webproperty: str):
        """
        Initialize a Webproperty object for a specific web property.

        Args:
            service: The service object used for authentication and API calls.
            webproperty: The URL of the web property.

        Raises:
            ValueError: If service is None or webproperty is invalid.
            NameError: If web property is not found or not accessible.
            RuntimeError: If API call fails.
        """
        if service is None:
            raise ValueError('Service cannot be None.')
        if not webproperty or not isinstance(webproperty, str):
            raise ValueError('Webproperty must be a non-empty string.')
        
        self.service = service
        
        # Get the URL and verify access
        try:
            response = self.service.sites().list().execute()
            site_entries = response['siteEntry']
        except Exception as e:
            raise RuntimeError(
                f'Failed to retrieve web properties: {str(e)}'
            ) from e
        
        matching_urls = [
            entry for entry in site_entries
            if entry['siteUrl'] == webproperty
        ]
        
        if not matching_urls:
            raise NameError(
                f'Webproperty "{webproperty}" not found. '
                'Check if you have access to this webproperty.'
            )
        
        self.url = matching_urls[0]['siteUrl']
        self.permission = matching_urls[0]['permissionLevel']
        
        self.query = query.Query(self.service, self.url)
        self.sitemap = sitemap.Sitemap(self.service, self.url)
        self.inspect = inspect_url.Inspect(self.service, self.url)
        self.can_query = (
            UNVERIFIED_PERMISSION_INDICATOR not in self.permission
        )
        
    def __eq__(self, other) -> bool:
        """
        Check equality with another Webproperty object.

        Args:
            other: Object to compare with.

        Returns:
            True if objects are equal, False otherwise.
        """
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False
        
    def __repr__(self) -> str:
        return f"<searchconsole.account.Webproperty(property='{self.url}')>"