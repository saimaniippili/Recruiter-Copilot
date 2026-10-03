import requests

q = 'site:linkedin.com/in/ Technical Product Owner/Staff Engineer Best, Netherlands "C" "C++" "Agile" "Scrum"'
params = {'engine':'google', 'q':q, 'api_key':'b9a55df1bec747afa2cf6cb09006f6262670776f721bb09cfbc1a4cd2d3e45d0'}
res = requests.get('https://serpapi.com/search', params=params).json()

print(res.keys())
print("Organic Results Count:", len(res.get('organic_results', [])))
for r in res.get('organic_results', []):
    print("LINK:", r.get('link'))
