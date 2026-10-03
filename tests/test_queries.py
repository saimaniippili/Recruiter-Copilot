import requests

q1 = 'site:linkedin.com/in/ Technical Product Owner/Staff Engineer Best, Netherlands "C" "C++" "Agile" "Scrum"'
q2 = 'site:linkedin.com/in/ "Technical Product Owner" Best Netherlands C++'
q3 = 'site:linkedin.com/in/ Technical Product Owner Staff Engineer Best Netherlands C++ Agile Scrum'

for q in [q1, q2, q3]:
    params = {'engine':'google', 'q':q, 'api_key':'b9a55df1bec747afa2cf6cb09006f6262670776f721bb09cfbc1a4cd2d3e45d0'}
    res = requests.get('https://serpapi.com/search', params=params).json().get('organic_results', [])
    links = [r.get('link') for r in res if 'linkedin.com/in/' in r.get('link', '')]
    print(f"Query: {q}\nMatches: {len(links)}\n")
