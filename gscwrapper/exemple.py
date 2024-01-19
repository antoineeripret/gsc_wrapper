import gscwrapper

#load the credentials 
try: 
    account = gscwrapper.generate_auth('config/client_secret_mvp.json', credentials='config/credentials.json')
except: 
    account = gscwrapper.generate_auth('config/client_secret_mvp.json', serialize='config/credentials.json')


#list all websites
#websites = account.list_webproperties(permissionLevel='siteOwner', is_domain_property=True)

#get the ctr_curve
webproperty = account['sc-domain:mesplaques.fr']
report = (
    webproperty
    .query
    .range(start="2023-01-01", stop="2024-01-01")
    .filter("page", "blog", "contains")
    .dimensions(['date'])
    .limit(100)
    .get()
)

print(report.show_data())


#inspect = (
#    webproperty
#    .inspect
#)

#print(inspect)

#(
# inspect
# .add_urls([
#     'https://www.website.com/page',
#     'https://www.website.com/other-page'
#     ]
#    )
#)

#print(inspect.urls_to_inspect)
