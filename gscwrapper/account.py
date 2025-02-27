from . import query, query_bq, sitemap, inspect_url
from google.cloud import bigquery
import pandas as pd 

class Account_BQ:
    def __init__(self, credentials, dataset):
        self.credentials = credentials
        self.dataset = dataset
        self.client = bigquery.Client(credentials=credentials, project=credentials.project_id)
        self.tables = self.list_tables()
        self.query = query_bq.Query_BQ(self.credentials, self.dataset)
    
    def list_tables(self):
        #list tables in a dataset
        tables = list(self.client.list_tables(self.dataset))
        #get the information in a friendly way 
        if len(tables) > 0:
            tables_df = pd.DataFrame(columns=[attr for attr in dir(tables[0]) if not callable(getattr(tables[0], attr)) and not attr.startswith("_")])
            for table in tables:
                tables_df.loc[len(tables_df)] = [getattr(table, element) for element in tables_df.columns]
        return tables_df.table_id.tolist()

class Account:
    """
    Represents a Google Search Console account, which can be associated with multiple web properties.
    This class provides methods to interact with the account and its web properties.
    """

    def __init__(self, service, credentials):
        """
        Initializes an Account object with the necessary service and credentials.

        Args:
            service (object): The service object used to interact with the Google Search Console API.
            credentials (object): The credentials object used for authentication with the Google Search Console API.
        """
        self.service = service
        self.credentials = credentials
    
    def list_webproperties(self, permissionLevel=None, is_domain_property=None):
        """
        Retrieves a list of all web properties associated with the account and returns
        them as a pandas DataFrame. Optionally filters the web properties based on
        the specified permission level and/or whether the property is a domain property.

        Args:
            permissionLevel (str, optional): The permission level to filter by. Supported values are:
                - 'siteFullUser'
                - 'siteOwner'
                - 'siteRestrictedUser'
                - 'siteUnverifiedUser'
                If not specified, all web properties are returned.
            is_domain_property (bool, optional): If True, only domain properties are returned. If False, only non-domain properties are returned.
                If not specified, all web properties are returned regardless of their domain property status.

        Returns:
            pandas.DataFrame: A DataFrame containing the list of web properties. Each row represents a web property.
        """
        import pandas as pd 
        accounts = pd.DataFrame(self.service.sites().list().execute()['siteEntry'])
        
        # Filter by permissionLevel if specified
        if permissionLevel:
            if permissionLevel not in ['siteFullUser','siteOwner','siteRestrictedUser','siteUnverifiedUser']: 
                raise ValueError('This permission level is not supported. Check https://developers.google.com/webmaster-tools/v1/sites?hl=en for the accepted values.')
            else:
                accounts = accounts.query('permissionLevel == @permissionLevel')
        
        # Filter by is_domain_property if specified
        if is_domain_property:
            if not isinstance(is_domain_property, bool):
                raise ValueError('is_domain_property must be a boolean.')
            else:
                accounts = (
                    accounts
                    .assign(
                        is_domain_property = lambda x: x.siteUrl.str.startswith('sc-domain')
                    )
                    .query('is_domain_property == @is_domain_property')
                    .drop('is_domain_property', axis=1)
                )
        
        return accounts
    
    def __getitem__(self, item):
        if isinstance(item, str):
            properties = [p for p in self.list_webproperties()['siteUrl'] if p == item]
            web_property = properties[0] if properties else None
        else:
            web_property = self.list_webproperties[item]

        return Webproperty(self.service, web_property)

    def __repr__(self):
        return "<searchconsole.account.Account>"


class Webproperty:
    """
    Represents a web property in Google Search Console. This class is used to interact with a specific website's data in Search Console, enabling the execution of Search Analytics queries and other operations related to the web property.

    Attributes:
        service (Service): The service object used for authentication and API calls.
        webproperty (str): The URL of the web property.
        url (str): The URL of the web property.
        permission (str): The permission level of the user for the web property.
        query (Query): An instance of the Query class for executing Search Analytics queries.
        sitemap (Sitemap): An instance of the Sitemap class for managing sitemaps.
        inspect (Inspect): An instance of the Inspect class for inspecting URLs.
        can_query (bool): Indicates if the user has permission to execute Search Analytics queries for the web property.
    """
    def __init__(self, service, webproperty):
        #pass the authentification 
        self.service = service 
        #get the url
        urls = [
            element 
            for element 
            in self.service.sites().list().execute()['siteEntry']
            if element['siteUrl'] == webproperty
        ]
        #if the URL provided by the user is correct 
        try: 
            self.url = urls[0]['siteUrl']
            self.permission = urls[0]['permissionLevel']
        #if it is incorrect 
        except IndexError: 
            raise NameError('Webproperty not found. Check if you have access to this webproperty.')
        
        self.query = query.Query(self.service, self.url)
        self.sitemap = sitemap.Sitemap(self.service, self.url)
        self.inspect = inspect_url.Inspect(self.service, self.url)
        self.can_query = False if 'Unverified' in self.permission else True
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        return False
        
    def __repr__(self):
        return "<searchconsole.account.Webproperty(property='{}')>".format(
            self.url
        )