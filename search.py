import json

materials_json = json.load(open("materials"))

all_material_object = materials_json['data']['materials']
all_tags_object = materials_json['data']['tags']

#print (all_material_object[0])
#print (all_tags_object[0])


material_lookup = {}
for m in all_material_object:
    material_lookup[m['id']]= m

ontology_json = json.load(open("ontology_trees"))

def classification_tree_to_set(root):
    my_set = set()
    my_set.add(root['id'])
    for c in root['children']:
        l = classification_tree_to_set(c)
        my_set = my_set | l # yes, that is a union operator
    return my_set

def add_parent_info(root):
    for c in root['children']:
        c['parent'] = root['id']
        add_parent_info(c)

def build_lookup(root, lookup = None):
    if lookup == None:
        lookup = {}
    lookup[root['id']] = root
    for c in root['children']:
        build_lookup(c, lookup)
    return lookup

add_parent_info(ontology_json['data']['acm'])


all_acm_ids = classification_tree_to_set(ontology_json['data']['acm'])

acm_lookup = build_lookup(ontology_json['data']['acm'])

def tag_match_value(t1, t2):
    if t1 == t2:
        return 1
    else:
        
        return 0


def similarity_tags (tags1, tags2, method='jaccard'):
    if (method == 'jaccard'):
        return len((tags1 & tags2))/len((tags1 | tags2))
    if (method == 'matching'):
        tl1 = list(tags1)
        tl2 = list(tags2)
        for ta in tl1:
            for tb in tl2:
                print (tag_match_value(ta, tb), end=' ')
            print ()
        return 0.

def similarity_material (mat1, mat2, method='jaccard'):
    print (mat1)
    print (mat2)
    #extracting list of tags that are acm mappings
    tag1=set()
    for t in mat1['tags']:
        if t['id'] in all_acm_ids:
            tag1.add(t['id'])
    tag2=set()
    for t in mat2['tags']:
        if t['id'] in all_acm_ids:
            tag2.add(t['id'])

    print (tag1)
    print (tag2)
    
    return similarity_tags(tag1, tag2, method)
    
print (similarity_material(material_lookup[148], material_lookup[145], 'matching'))
