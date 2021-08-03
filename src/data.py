import requests
import json

# takes an id of a collection and returns a list of all the materials contained by that collection (not recursive)
def all_materials_in_collection(id):
    url = "https://cs-materials-api.herokuapp.com/data/material/meta?id=" + str(id)
    r = requests.get(url)
    mat = json.loads(r.text)['data']
    ret = []
    for c in mat['materials']:
        ret.append(c['id'])
    return ret
