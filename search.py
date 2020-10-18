import json

materials_json = json.load(open("materials"))

all_material_object = materials_json['data']['materials']
all_tags_object = materials_json['data']['tags']

print (all_material_object[0])
print (all_tags_object[0])


ontology_json = json.load(open("ontology_trees"))

def tree_to_set(root):
    my_set = set()
    my_set.add(root['id'])
    for c in root['children']:
        l = tree_to_set(c)
        my_set = my_set | l # yes, that is a union operator
    return my_set

allacm = tree_to_set(ontology_json['data']['acm'])

print(allacm)
