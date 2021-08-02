from flask import Flask, request, Response, make_response
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

import json
import networkx as nx
import sys
import requests
from matplotlib import pyplot as plt
from sklearn.manifold import MDS

app = Flask(__name__)

# you'll need to pip3 install networkx

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


@app.route('/')
def homepage():
    return 'homepage'


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


# takes an id of a collection and returns a list of all the materials contained by that collection (not recursive)
def all_materials_in_collection(id):
    url = "https://cs-materials-api.herokuapp.com/data/material/meta?id=" + str(id)
    r = requests.get(url)
    mat = json.loads(r.text)['data']
    ret = []
    for c in mat['materials']:
        ret.append(c['id'])
    return ret


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


# return similarity value between two tags where the two tags have a
# common ancestor at depth d (root is 0) and the first tag is l1 levels
# deeper than the common ancestor and tag 2 is l2 levels deeper than
# the common ancestor
def tag_similarity(d, l1, l2):
    # this formula is completely arbitrary but it gives reasonnable values:
    # tag_sim(0, 2, 2) = 0.0033749999999999995
    # tag_sim(1, 2, 2) = 0.026999999999999996
    # tag_sim(2, 1, 1) = 0.44999999999999996
    # tag_sim(3, 1, 1) = 0.6
    # tag_sim(3, 2, 1) = 0.36
    # tag_sim(3, 2, 2) = 0.21599999999999997

    base = .15 * (d + 1)
    return base ** (l1 + l2 - 1)


# this assumes that t1 and t2 are part of the same acm ontology tree
def tag_match_value(t1, t2):
    if t1 == t2:
        return 1
    else:
        tp1 = tag_path(t1)
        tp2 = tag_path(t2)
        # print (str(tp1)+ "," + str(tp2))

        first_diff = 0
        while first_diff != min(len(tp1), len(tp2)) and tp1[first_diff] == tp2[first_diff]:
            first_diff = first_diff + 1

        d = first_diff - 1
        l1 = len(tp1) - first_diff
        l2 = len(tp2) - first_diff

        return tag_similarity(d, l1, l2)


# computes similarity between two sets of tags
def similarity_tags(tags1, tags2, method='jaccard'):
    if (len(tags1) == 0 or len(tags2) == 0):
        return 0.0
    
    if (method == 'jaccard'):
        return len((tags1 & tags2)) / len((tags1 | tags2))

    if (method == 'matching'):

        # count and remove exact matches
        exact_match = set()
        for t in tags1:
            if t in tags2:
                exact_match.add(t)
        tags1 = tags1 - exact_match
        tags2 = tags2 - exact_match

        # build bipartite graph between tags that remain
        tl1 = list(tags1)
        tl2 = list(tags2)
        g = nx.Graph()
        for ta in tl1:
            for tb in tl2:
                tmv = tag_match_value(ta, tb)
                g.add_edge(ta, tb, weight=tmv)

        # compute bipartite matching
        bipartmatch = nx.max_weight_matching(g)  # returns a set of pairs

        val = 0
        for a, b in bipartmatch:
            val += g[a][b]['weight']

        return (val + 2*len(exact_match)) / (2 * len(exact_match) + (len(tags1) + len(tags2)))


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


# computes similarity between two materialIDs
def similarity_material(mat1: int, mat2: int, method='jaccard', resolve_collection=False) -> float:
    # print (mat1)
    # print (mat2)
    # extracting set of tags that are acm mappings
    tag1 = all_acm_tags_in_list([mat1], resolve_collection)
    tag2 = all_acm_tags_in_list([mat2], resolve_collection)

    # print (tag1)
    # print (tag2)

    return similarity_tags(tag1, tag2, method)


# query is a list of tags
# matchpool is a set of material ids
def similarity_query_tags(query, matchpool, k, algo):
    k = min(k, len(matchpool))

    sims = [[1] * (k + 1) for i in range(0, k + 1)]
    disims = [[0] * (k + 1) for i in range(0, k + 1)]

    match_pairs = []
    for cand in matchpool:
        s = similarity_tags(query, all_acm_tags_in_list([cand]), algo)
        match_pairs.append((cand, s))

    match_pairs = sorted(match_pairs, key=(lambda x: x[1]), reverse=True)

    # print ("query: ", query, material_lookup[query]['title'])

    # print (sims)

    # print ("source","target","weight", sep=',', file=sys.stderr)
    for i in range(0, k):
        sims[0][i + 1] = match_pairs[i][1]
        sims[i + 1][0] = match_pairs[i][1]
        disims[0][i + 1] = 1 - match_pairs[i][1]
        disims[i + 1][0] = 1 - match_pairs[i][1]
        # print ("query", match_pairs[i][0], match_pairs[i][1], sep=',', file=sys.stderr)

    for i in range(0, k):
        for j in range(i + 1, k):
            if i != j:
                ls = similarity_material(material_lookup[match_pairs[j][0]]['id'],
                                         material_lookup[match_pairs[i][0]]['id'], 'matching')
                sims[i + 1][j + 1] = ls
                sims[j + 1][i + 1] = ls
                disims[i + 1][j + 1] = 1 - ls
                disims[j + 1][i + 1] = 1 - ls
                # print (match_pairs[i][0], match_pairs[j][0], ls, sep=',', file=sys.stderr)

    model = MDS(n_components=2, dissimilarity='precomputed', random_state=1)
    out = model.fit_transform(disims)

    norm = 0
    for i in range(0, k + 1):
        if (abs(out[i][0]) > norm):
            norm = abs(out[i][0])
        if (abs(out[i][1]) > norm):
            norm = abs(out[i][1])

    for i in range(0, k + 1):
        out[i][0] = out[i][0] / norm
        out[i][1] = out[i][1] / norm

    # print (out)

    ret = {}
    ret['query'] = {
        "tags": list(query),
        "mds_x": out[0][0],
        "mds_y": out[0][1]
    }
    ret['result'] = []
    for i in range(1, k + 1):
        result_similarity = sims[i][1:k + 1]
        ret['result'].append({
            'id': match_pairs[i - 1][0],
            'title': material_lookup[match_pairs[i - 1][0]]['title'],
            'query_similarity': match_pairs[i - 1][1],
            'result_similarity': result_similarity,
            "mds_x": out[i][0],
            "mds_y": out[i][1]
        })

    for i in range(0, k + 1):
        name = "\"query\""
        if (i > 0):
            name = "\"" + material_lookup[match_pairs[i - 1][0]]['title'] + "\""
        print(out[i][0], out[i][1], name, sep=' ')

    # print("id", "label", sep=',', file=sys.stdout)
    # print("query", "query", sep=',', file=sys.stdout)

    # for i in range(0, k-1):
    #     print (match_pairs[i][0], material_lookup[match_pairs[i][0]]['title'], sep=',', file=sys.stdout)

    return ret


def add_response_headers(resp):
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp


def return_object(obj):
    resp = Response(json.dumps({
        "data": obj,
        "status": "OK"
    }
    ), mimetype='application/json')
    return add_response_headers(resp)


def return_error(str):
    resp = Response(json.dumps({
        "status": "KO",
        "reason": str
    }
    ), mimetype='application/json')
    return add_response_headers(resp)


# query is a materialID
# matchpool is a set of materialID
def similarity_query(query, matchpool, k, algo):
    similarity_query_tags(all_acm_tags_in_list([query]), matchpool, k, algo)


@app.route('/search')
def my_search():
    matchpool = []

    matchpoolstr = 'all'

    if request.args.get('matchpool') is not None:
        matchpoolstr = request.args.get('matchpool')

    if matchpoolstr == 'all':
        matchpool = list(material_lookup)
    elif matchpoolstr == 'pdc':
        peachy = 263
        erik_parco = 179
        pdc_mats = all_materials_in_collection(peachy)
        pdc_mats.extend(all_materials_in_collection(erik_parco))
        matchpool = pdc_mats
    else:
        return return_error("unknown matchpool parameter")

    tags = []

    if request.args.get('tags') is not None:
        tags = request.args.get('tags').split(',')
        for i in range(0, len(tags)):
            tags[i] = int(tags[i])
        tags = set(tags)

    if request.args.get('matID') is not None:
        matID = int(request.args.get('matID'))
        if matID in matchpool:
            matchpool.remove(matID)
        tags = all_acm_tags_in_list([matID])

    k = 10

    if request.args.get('k') is not None:
        k_query = int(request.args.get('k'))
        if k_query > 0 and k_query < 100:
            k = int(k_query)

    algo = 'matching'

    simdata = similarity_query_tags(tags, matchpool, k, algo)

    if request.args.get('matID') is not None:
        matID = int(request.args.get('matID'))
        simdata['query']['query_matID'] = matID

    return return_object(simdata)

@app.route('/agreement')
def agreement():
    matID = []
    if request.args.get('matID') is not None:
        matID = request.args.get('matID').split(',')

    if len(matID)<2:
        return return_error("need at least 2 materials")

    mapping = {}
    alltags = set()

    #material info
    matinfo = {}
    
    for id in matID:
        mapping[int(id)] = all_acm_tags_in_list([int(id)], True)
        alltags = alltags | mapping[int(id)]
        matinfo[int(id)] = material_lookup[int(id)]

    
        
    #generate counts
    allcount = {}
        
    for tag in alltags:
        #print (tag)
        count = 0
        for id in mapping:
            if tag in mapping[id]:
                count += 1
        allcount[tag] = count

    #generate histogram
    histogram = [0] * (len(mapping)+1)

    percount = {}
    for i in range(len(matID)+1):
        percount[i] = []
    
    for tag in allcount:
        histogram[allcount[tag]] += 1
        percount[allcount[tag]].append(
            {
                'id': tag,
                'title' : tags_lookup[tag]['title']
            })


        
    return return_object(
        {
            'materials': matinfo,
            'count' : allcount,
            'histogram' : histogram,
            'percount': percount
        })
    
@app.route('/ontologyCSV')
def ontology_csv():
    ret = ""
    for t in all_acm_ids:
        ret += str(t)
        id = t
        li = [ acm_lookup[id]['title'] ]
        while 'parent' in acm_lookup[id]:
            id = acm_lookup[id]['parent']
            li.insert(0, acm_lookup[id]['title'])
        for ti in li:
            ret += "\t"+ti
        ret += "\n"

    response = make_response(ret, 200)
    response.mimetype = "text/plain"
    return response
    
        

# query = 154 # KRS - HW - Binary trees
# query = 55 # Bacon Number imdb  bridges
# query = 237 # 3112 module 3 project
# matchpool = list(material_lookup)
# matchpool.remove(query)
# k = 10


# nifty = 264
# erik_ds=178
# kr_ds=185
# kr_3112 = 266
# bk_CS1 = 326


# pdc_mats = all_materials_in_collection(peachy)
# pdc_mats.extend( all_materials_in_collection(erik_parco) )

# similarity_query_tags(all_acm_tags_in_list([ query ]), pdc_mats, k, 'matching')


# function with a new route called SimilarityMatrix
# Takes a set of materials as the request parameter MatID


def tag2(args):
    pass


@app.route('/similarity_matrix')
def similarity_matrix():
    matID = []
    if request.args.get('matID') is not None:
        matID = request.args.get('matID').split(',')
        amount = len(matID)

        # if the list has one material, return error

        if amount == 1:
            return return_error("There is only one material in the set.")
        # if there are no materials in the set, return error

    if request.args.get('matID') is None:
        return return_error("There are no materials in the set.")

    # compute similarity between material 1 and material 2

    elif request.args.get('matID') is not None:
        matID = request.args.get('matID').split(',')

        # mat1 = int(matID[0])
        # mat2 = int(matID[1])

        sim_pairs = []
        match_pair = {}

        match_pair['result'] = {}
        match_pair['result']['similarity'] = {}
        
        for i in range(len(matID)):
            mat1 = int(matID[i])
            match_pair['result']['similarity'][mat1] = {}

        for i in range(len(matID)):
            for j in range(i + 1,len(matID)):
                mat1 = int(matID[i])
                mat2 = int(matID[j])
        # return similarity pairs
        return return_object(match_pair)


@app.route('/class_model/<classname>')
def class_model(classname: str):
    if classname == "datastructure":

        erik_ds = 178
        kr_ds = 185

        ds_tags = all_acm_tags_in_list(all_materials_in_collection(erik_ds)).intersection(
            all_acm_tags_in_list(all_materials_in_collection(kr_ds)))

        # for t in ds_tags:
        #     print (acm_lookup[t]['title'])

        return return_object({
            "datastructure": list(ds_tags)
        })
    else:
        return json.dumps(
            {
                "status": "KO"
            }
        )


@app.route('/sets/allpdc')
def all_pdc():
    # nifty = 264
    peachy = 263
    erik_parco = 179
    # erik_ds=178
    # kr_ds=185
    # kr_3112 = 266
    # bk_CS1 = 326
    pdc_mats = all_materials_in_collection(peachy)
    pdc_mats.extend(all_materials_in_collection(erik_parco))
    return return_object({
        "allpdc": list(pdc_mats)
    })


@app.before_first_request
def init():
    update_model()
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=update_model, trigger="interval", minutes=60)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    # query = 154 # KRS - HW - Binary trees
    # query = 55 # Bacon Number imdb  bridges
    # query = 237 # 3112 module 3 project
    # matchpool = list(material_lookup)
    # matchpool.remove(query)
    # k = 10

    # similarity_query_tags(all_acm_tags_in_list([ query ]), pdc_mats, k, 'matching')

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


@app.route('/pagerank')
def pagerank_feature():
    matID = []
    # declare an empty graph from the NetworkX module
    g = nx.Graph()

    # add the classification edges (between materials and tags)

    for mid in material_lookup:
        mat = material_lookup[mid]
        for tags in mat['tags']:
            if tags['id'] in all_acm_ids:
                g.add_edge("m" + str(mat['id']), "t" + str(tags['id']))

    # ontology edges/for all ACM tags tid: add edge between tid and parent tid
    for t in all_acm_ids:
        if 'parent' in acm_lookup[t]:
            parentid = acm_lookup[t]['parent']
            g.add_edge("t" + str(parentid), "t" + str(t))

        # nx.write_edgelist(g, "test.edgelist", data=False)
        # f = plt.figure()
        # nx.draw_spring(g, with_labels=True, ax=f.add_subplot(111))
        # f.savefig('graph.png')
        # return 'empty'

    if request.args.get('matID') is not None:
        matID = request.args.get('matID').split(',')
        amount = len(matID)
        if amount > 2:
            for mid in material_lookup:
                mat = material_lookup[mid]
                personalization = 1 / len(str(mat['id']))

                pr = nx.pagerank(g, alpha=0.85, personalization={personalization}, max_iter=100,
                                 tol=1e-06, nstart=None,
                                 weight='weight', dangling=None)

                return print(pr)
