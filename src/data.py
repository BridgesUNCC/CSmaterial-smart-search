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


# get materials file and ontology_trees file here:
# https://cs-materials-api.herokuapp.com/data/materials
# https://cs-materials-api.herokuapp.com/data/ontology_trees

# materials_json = json.load(open("materials"))
materials_json = {}

all_material_object = None
all_tags_object = None

# print (all_material_object[0])
# print (all_tags_object[0])

# build a lookup table of materials keyed on their 'id'
material_lookup = {}

tags_lookup = {}

# ontology_json = json.load(open("ontology_trees"))
ontology_json = {}

all_acm_ids = set()  # set of all acm classification tag ids

acm_lookup = {}  # associate 'id' to an acm classification tag object


# return a set of all entry ids in a classification tree
def classification_tree_to_set(root):
    my_set = set()
    my_set.add(root['id'])
    for c in root['children']:
        l = classification_tree_to_set(c)
        my_set = my_set | l  # yes, that is a union operator
    return my_set


# add a 'parent' field in a ontology tree to enable reverse traversals
def add_parent_info(root):
    for c in root['children']:
        c['parent'] = root['id']
        add_parent_info(c)


# build a lookup table that associate tag ids to the ontology entry
def build_lookup(root, lookup=None):
    if lookup == None:
        lookup = {}
    lookup[root['id']] = root
    for c in root['children']:
        build_lookup(c, lookup)
    return lookup



def update_model():
    global materials_json
    global all_material_object
    global all_tags_object
    global material_lookup
    global tags_lookup
    global ontology_json
    global all_acm_ids
    global acm_lookup

    #
    # https://cs-materials-api.herokuapp.com/data/ontology_trees

    materials_json = json.loads(requests.get("https://cs-materials-api.herokuapp.com/data/materials/full").text)

    all_material_object = materials_json['data']['materials']
    all_tags_object = materials_json['data']['tags']

    material_lookup = {}
    for m in all_material_object:
        material_lookup[m['id']] = m

    tags_lookup = {}
    for t in all_tags_object:
        tags_lookup[t['id']] = t

    ontology_json = json.loads(requests.get("https://cs-materials-api.herokuapp.com/data/ontology_trees").text)

    add_parent_info(ontology_json['data']['acm'])

    all_acm_ids = classification_tree_to_set(ontology_json['data']['acm'])

    acm_lookup = build_lookup(ontology_json['data']['acm'])


# return the path from tag to the root
# takes tag id (not tag object)
def tag_path_reverse(t):
    if 'parent' not in acm_lookup[t]:
        return [t]
    else:
        l = list()
        l.append(t)
        l.extend(tag_path_reverse(acm_lookup[t]['parent']))
        return l


# return the path from root of the ontology to tag
# takes tag id (not tag object)
def tag_path(t):
    l = tag_path_reverse(t)
    l.reverse()
    return l


# takes a list of material ID and return all acm tags contained by the materials
def all_acm_tags_in_list(l: list, resolve_collection=False) -> set:
    all_t = set()
    for mid in l:
        mat = material_lookup[mid]
        if 'tags' in mat:
            for tags in mat['tags']:
                if tags['id'] in all_acm_ids:
                    all_t.add(tags['id'])

        if resolve_collection and mat['type'] == 'collection':
            all_t = all_t | all_acm_tags_in_list(all_materials_in_collection(mid), resolve_collection)
                
    return all_t
