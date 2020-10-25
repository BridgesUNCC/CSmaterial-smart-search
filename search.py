import json
import networkx as nx
import sys
import requests
from sklearn.manifold import MDS

#you'll need to pip3 install networkx

#get materials file and ontology_trees file here:
# https://cs-materials-api.herokuapp.com/data/materials
# https://cs-materials-api.herokuapp.com/data/ontology_trees

materials_json = json.load(open("materials"))

all_material_object = materials_json['data']['materials']
all_tags_object = materials_json['data']['tags']

#print (all_material_object[0])
#print (all_tags_object[0])

#build a lookup table of materials keyed on their 'id'
material_lookup = {}
for m in all_material_object:
    material_lookup[m['id']]= m

tags_lookup = {}
for t in all_tags_object:
    tags_lookup[t['id']]= t

    
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

# takes an id of a collection and returns a list of all the materials contained by that collection (not recursive)
def all_materials_in_collection(id):
    url = "https://cs-materials-api.herokuapp.com/data/material/meta?id=" + str(id)
    r = requests.get(url)
    mat = json.loads(r.text)['data']
    ret = []
    for c in mat['materials']:
        ret.append (c['id'])
    return ret 


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
        while first_diff != min(len(tp1), len(tp2)) and tp1[first_diff] == tp2[first_diff]:
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

        #compute bipartite matching
        bipartmatch = nx.max_weight_matching(g) #returns a set of pairs

        val = 0
        for a, b in bipartmatch:
            val += g[a][b]['weight']

        return (val+len(exact_match)) / (len(exact_match) + 2*(len(tags1)+len(tags2)))

#takes a list of material ID and return all acm tags contained by the materials
def all_acm_tags_in_list (l : list) -> set:
    all_t = set()
    for mid in l:
        mat = material_lookup[mid]
        for tags in mat['tags']:
            if tags['id'] in all_acm_ids:
                all_t.add(tags['id'])
    return all_t

    
#computes similarity between two materialIDs
def similarity_material (mat1 :int, mat2: int, method='jaccard') -> float:
    #print (mat1)
    #print (mat2)
    #extracting set of tags that are acm mappings
    tag1=all_acm_tags_in_list([ mat1 ] )
    tag2=all_acm_tags_in_list([ mat2 ] )

    #print (tag1)
    #print (tag2)
    
    return similarity_tags(tag1, tag2, method)

# query is a list of tags
#matchpool is a set of material ids
def similarity_query_tags(query, matchpool, k, algo):

    sims = [ [ 0 ] * (k+1)  for i in range (0,k+1) ] 

    
    match_pairs = []
    for cand in matchpool:
        s = similarity_tags(query, all_acm_tags_in_list([ cand ]), algo)
        match_pairs.append((cand, s))

    match_pairs = sorted(match_pairs, key=(lambda x: x[1]), reverse= True)


    #print ("query: ", query, material_lookup[query]['title'])


    #print (sims)
    
    #print ("source","target","weight", sep=',', file=sys.stderr) 
    for i in range(0, k-1):
        sims[0][i+1] = 1 - match_pairs[i][1]
        sims[i+1][0] = 1 - match_pairs[i][1]
        #print ("query", match_pairs[i][0], match_pairs[i][1], sep=',', file=sys.stderr)
    
        
    for i in range(0, k-1):
        for j in range(i+1, k-1):
            if i !=j :
                ls = similarity_material(material_lookup[match_pairs[j][0]]['id'], material_lookup[match_pairs[i][0]]['id'], 'matching')
                sims[i+1][j+1] = 1 - ls
                sims[j+1][i+1] = 1 - ls
                #print (match_pairs[i][0], match_pairs[j][0], ls, sep=',', file=sys.stderr)

                

    model = MDS(n_components=2, dissimilarity='precomputed', random_state=1)
    out = model.fit_transform(sims)

    norm = 0
    for i in range (0, k):
        if (abs(out[i][0]) > norm):
            norm = abs(out[i][0])
        if (abs(out[i][1]) > norm):
            norm = abs(out[i][1])
    
    #print (out)

    for i in range (0, k):
        name = "\"query\""
        if (i > 0):
            name = "\""+material_lookup[match_pairs[i-1][0]]['title']+"\""
        print (out[i][0]/norm, out[i][1]/norm, name,  sep=' ')
    
    # print("id", "label", sep=',', file=sys.stdout)
    # print("query", "query", sep=',', file=sys.stdout)

    # for i in range(0, k-1):
    #     print (match_pairs[i][0], material_lookup[match_pairs[i][0]]['title'], sep=',', file=sys.stdout) 

    
        
# query is a materialID
# matchpool is a set of materialID
def similarity_query(query, matchpool, k, algo):
    similarity_query_tags(all_acm_tags_in_list([ query ]), matchpool, k, algo)


query = 154 # KRS - HW - Binary trees
query = 55 # Bacon Number imdb  bridges
query = 237 # 3112 module 3 project
matchpool = list(material_lookup)
matchpool.remove(query)
k = 10




nifty = 264
peachy = 263
erik_ds=178
kr_ds=185
erik_parco=179
kr_3112 = 266
bk_CS1 = 326


pdc_mats = all_materials_in_collection(peachy)
pdc_mats.extend( all_materials_in_collection(erik_parco) )

similarity_query_tags(all_acm_tags_in_list([ query ]), pdc_mats, k, 'matching')

# for n in all_materials_in_collection(bk_CS1):
#     print ("===", n, material_lookup[n]['title'], "===")
#     similarity_query_tags(all_acm_tags_in_list([ n ]), pdc_mats, k, 'matching')


# print (all_materials_in_collection(nifty))


# print (all_acm_tags_in_list(all_materials_in_collection(erik_ds)))
# print (all_acm_tags_in_list(all_materials_in_collection(kr_ds)))

# ds_tags = all_acm_tags_in_list(all_materials_in_collection(erik_ds)).intersection(all_acm_tags_in_list(all_materials_in_collection(kr_ds)))

# print (ds_tags)
# for t in ds_tags:
#     print (tags_lookup[t])
