from flask import Flask, Response, Blueprint, request
from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx
import time

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
#returns a dictionary mapping materials to a score (the higher the more similar)
def similarity_query_tags(query, matchpool, k:int, algo:str):
    start = time.time()
    k = min(k, len(matchpool))

    print (query)
    
    match_pairs = {}
    for cand in matchpool:
        s = similarity_tags(query, data.all_acm_tags_in_list([cand]), algo)
        match_pairs[cand] = s

    end = time.time()
    print("it took "+str(end - start)+"s to build the compute similarity")

    return match_pairs



# query is a materialID
# matchpool is a set of materialID
def similarity_query(query, matchpool, k, algo):
    similarity_query_tags(data.all_acm_tags_in_list([query]), matchpool, k, algo)




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
