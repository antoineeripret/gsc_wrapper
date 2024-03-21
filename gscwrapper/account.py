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
    An account can be associated with a number of web
    properties.
    """

    def __init__(self, service, credentials):
        self.service = service
        self.credentials = credentials
    
    def list_webproperties(self, permissionLevel=None, is_domain_property=None):
        import pandas as pd 
        """
        Retrieves a list of all web properties associated with the account and returns
        them as a pandas DataFrame. Optionally filters the web properties based on
        the specified permission level.
        """
        accounts = pd.DataFrame(self.service.sites().list().execute()['siteEntry'])
        if permissionLevel:
            #ensure that we have a proper value 
            if permissionLevel not in ['siteFullUser','siteOwner','siteRestrictedUser','siteUnverifiedUser']: 
                raise ValueError('This permission level is not supported. Check https://developers.google.com/webmaster-tools/v1/sites?hl=en for the accepted values.')
            else:
                accounts = accounts.query('permissionLevel == @permissionLevel')
        if is_domain_property:
            #check if we have a boolean 
            if not isinstance(is_domain_property, bool):
                raise ValueError('is_domain_property must be a boolean.')
            #respect what the user wants 
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
        return "<searchconsole.account.Account(client_id='{}')>".format(
            self.credentials.client_id
        )


class Webproperty:
    """
    A web property is a particular website you're tracking
    in Google Search Console. You will use a web property
    to make your Search Analytics queries.
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