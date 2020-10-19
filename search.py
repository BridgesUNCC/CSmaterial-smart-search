import json
import networkx as nx

materials_json = json.load(open("materials"))

all_material_object = materials_json['data']['materials']
all_tags_object = materials_json['data']['tags']

#print (all_material_object[0])
#print (all_tags_object[0])

#build a lookup table of materials keyed on their 'id'
material_lookup = {}
for m in all_material_object:
    material_lookup[m['id']]= m

ontology_json = json.load(open("ontology_trees"))

# return a set of all entry ids in a classification tree
def classification_tree_to_set(root):
    my_set = set()
    my_set.add(root['id'])
    for c in root['children']:
        l = classification_tree_to_set(c)
        my_set = my_set | l # yes, that is a union operator
    return my_set

# add a 'parent' field in a ontology tree to enable reverse traversals
def add_parent_info(root):
    for c in root['children']:
        c['parent'] = root['id']
        add_parent_info(c)

#build a lookup table that associate tag ids to the ontology entry
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


#return the path from tag to the root
#takes tag id (not tag object)
def tag_path_reverse(t):
    if 'parent' not in acm_lookup[t]:
        return [t]
    else:
        l = list()
        l.append(t)
        l.extend(tag_path_reverse(acm_lookup[t]['parent']))
        return l


#return the path from root of the ontology to tag
#takes tag id (not tag object)
def tag_path(t):
    l = tag_path_reverse(t)
    l.reverse()
    return l

#return similarity value between two tags where the two tags have a
#common ancestor at depth d (root is 0) and the first tag is l1 levels
#deeper than the common ancestor and tag 2 is l2 levels deeper than
#the common ancestor
def tag_similarity (d, l1, l2):
    #this formula is completely arbitrary but it gives reasonnable values:
    #tag_sim(0, 2, 2) = 0.0033749999999999995
    #tag_sim(1, 2, 2) = 0.026999999999999996
    #tag_sim(2, 1, 1) = 0.44999999999999996
    #tag_sim(3, 1, 1) = 0.6
    #tag_sim(3, 2, 1) = 0.36
    #tag_sim(3, 2, 2) = 0.21599999999999997


    base = .15*(d+1)
    return base**(l1+l2-1)

#this assumes that t1 and t2 are part of the same acm ontology tree
def tag_match_value(t1, t2):
    if t1 == t2:
        return 1
    else:
        tp1 = tag_path(t1)
        tp2 = tag_path(t2)
        #print (str(tp1)+ "," + str(tp2))

        first_diff = 0
        while tp1[first_diff] == tp2[first_diff]:
            first_diff = first_diff + 1

        d= first_diff -1
        l1 = len(tp1)-first_diff
        l2 = len(tp2)-first_diff
        
        return tag_similarity(d, l1, l2)

#computes similarity between two sets of tags 
def similarity_tags (tags1, tags2, method='jaccard'):
    if (method == 'jaccard'):
        return len((tags1 & tags2))/len((tags1 | tags2))
    if (method == 'matching'):
        
        #count and remove exact matches
        exact_match = set()
        for t in tags1:
            if t in tags2:
                exact_match.add(t)
        tags1 = tags1-exact_match
        tags2 = tags2-exact_match
        
        #build bipartite graph between tags that remain
        tl1 = list(tags1)
        tl2 = list(tags2)
        g = nx.Graph()
        for ta in tl1:
            for tb in tl2:
                tmv = tag_match_value(ta, tb)
                g.add_edge(ta, tb, weight=tmv)

        print (g)
        
        bipartmatch = nx.max_weight_matching(g) #returns a set of pairs

        val = 0
        for a, b in bipartmatch:
            val += g[a][b]['weight']

        return (val+len(exact_match)) / (len(exact_match) + 2*(len(tags1)+len(tags2)))

#computes similarity between two materials
def similarity_material (mat1, mat2, method='jaccard'):
    print (mat1)
    print (mat2)
    #extracting set of tags that are acm mappings
    tag1=set()
    for t in mat1['tags']:
        if t['id'] in all_acm_ids:
            tag1.add(t['id'])
    tag2=set()
    for t in mat2['tags']:
        if t['id'] in all_acm_ids:
            tag2.add(t['id'])

    #print (tag1)
    #print (tag2)
    
    return similarity_tags(tag1, tag2, method)
    
print (similarity_material(material_lookup[148], material_lookup[145], 'matching'))

