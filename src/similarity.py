from flask import Flask, Response, Blueprint, request
from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx

import util
import data

similarity_blueprint = Blueprint('similarity', __name__)



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
        tp1 = data.tag_path(t1)
        tp2 = data.tag_path(t2)
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




# computes similarity between two materialIDs
def similarity_material(mat1: int, mat2: int, method='jaccard', resolve_collection=False) -> float:
    # print (mat1)
    # print (mat2)
    # extracting set of tags that are acm mappings
    tag1 = data.all_acm_tags_in_list([mat1], resolve_collection)
    tag2 = data.all_acm_tags_in_list([mat2], resolve_collection)

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
        s = similarity_tags(query, data.all_acm_tags_in_list([cand]), algo)
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
                ls = similarity_material(data.material_lookup[match_pairs[j][0]]['id'],
                                         data.material_lookup[match_pairs[i][0]]['id'], 'matching')
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
            'title': data.material_lookup[match_pairs[i - 1][0]]['title'],
            'query_similarity': match_pairs[i - 1][1],
            'result_similarity': result_similarity,
            "mds_x": out[i][0],
            "mds_y": out[i][1]
        })

    for i in range(0, k + 1):
        name = "\"query\""
        if (i > 0):
            name = "\"" + data.material_lookup[match_pairs[i - 1][0]]['title'] + "\""
        print(out[i][0], out[i][1], name, sep=' ')

    # print("id", "label", sep=',', file=sys.stdout)
    # print("query", "query", sep=',', file=sys.stdout)

    # for i in range(0, k-1):
    #     print (match_pairs[i][0], material_lookup[match_pairs[i][0]]['title'], sep=',', file=sys.stdout)

    return ret



# query is a materialID
# matchpool is a set of materialID
def similarity_query(query, matchpool, k, algo):
    similarity_query_tags(data.all_acm_tags_in_list([query]), matchpool, k, algo)


@similarity_blueprint.route('/search')
def my_search():
    matchpool = []

    matchpoolstr = 'all'

    if request.args.get('matchpool') is not None:
        matchpoolstr = request.args.get('matchpool')

    if matchpoolstr == 'all':
        matchpool = list(data.material_lookup)
    elif matchpoolstr == 'pdc':
        peachy = 263
        erik_parco = 179
        pdc_mats = data.all_materials_in_collection(peachy)
        pdc_mats.extend(data.all_materials_in_collection(erik_parco))
        matchpool = pdc_mats
    else:
        return util.return_error("unknown matchpool parameter")

    tags = util.argument_to_IDlist('tags')
    if tags is not None:
        tags = set(tags)

    if request.args.get('matID') is not None:
        matID = int(request.args.get('matID'))
        if matID in matchpool:
            matchpool.remove(matID)
        tags = data.all_acm_tags_in_list([matID])

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

    return util.return_object(simdata)


@similarity_blueprint.route('/similarity')
def similarity_matrix():
    genMDS = True
        
    matID = util.argument_to_IDlist('matID')
    if matID is None:
        util.return_error ("matID is a necessary parameter")

    if len(matID) < 2:
        return util.return_error("There need to be at least 2 materials in matID.")
        
    sims = {}
        
    for i in range(len(matID)):
        mat1 = int(matID[i])
        sims[mat1] = {}

    for i in range(len(matID)):
        for j in range(i + 1,len(matID)):
            mat1 = int(matID[i])
            mat2 = int(matID[j])

            sim_mat1_mat2 = similarity_material(mat1, mat2, method='matching', resolve_collection=True)
            sims[mat1][mat2] = sim_mat1_mat2
            sims[mat2][mat1] = sim_mat1_mat2

    mds = {}

    if (genMDS):

        disims = [[0] * (len(matID)) for i in range(0, len(matID))]
    
        for i in range (0, len(matID)):
            for j in range (0, len(matID)):
                if i != j:
                    disims[i][j] = 1- sims[matID[i]][matID[j]]

        model = MDS(n_components=2, dissimilarity='precomputed', random_state=1)
        out = model.fit_transform(disims)

        norm = 0
        for i in range(0, len(matID) ):
            if (abs(out[i][0]) > norm):
                norm = abs(out[i][0])
            if (abs(out[i][1]) > norm):
                norm = abs(out[i][1])

        
            
        for i in range(0, len(matID)):
            out[i][0] = out[i][0] / norm
            out[i][1] = out[i][1] / norm
            mds[matID[i]] = (out[i][0], out[i][1])
            
    return util.return_object(
        {
            'data': matID,
            'similarity': sims,
            'mds' : mds
        }
    )
