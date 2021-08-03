from flask import Flask, Response, Blueprint, request
from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx
import time

import util
import data
import similarity
import pagerank


search_blueprint = Blueprint('search', __name__)


def parse_matchpool():

    matchpoolstr = 'all'
    matchpool = None
    
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
    
    return (matchpoolstr,matchpool)
        
@search_blueprint.route('/search')
def my_search():
    (matchpoolstr,matchpool) = parse_matchpool()
    if matchpool is None:
        return util.return_error("unknown matchpool parameter")

    tags = util.argument_to_IDlist('tags')
    if tags is not None:
        tags = set(tags)
    else:
        tags= set()
        
    matID = util.argument_to_IDlist('matID')
    if matID is not None:
        for id in matID:
            if id in matchpool:
                matchpool.remove(id)
    else:
        matID = []

    k = 10

    if request.args.get('k') is not None:
        k = int(request.args.get('k'))
        if k < 1:
            return util.return_error("k must be positive")
            
        if k > 100:
            k = 100

    algo = 'matching'
    if request.args.get('algo') is not None:
        algo = request.args.get('algo')

    results = {}

    if algo == 'jaccard' or algo == 'matching':
        results = similarity.similarity_query_tags(set(tags) | data.all_acm_tags_in_list(matID), matchpool, k, algo)
    elif algo == 'pagerank':
        results = pagerank.pagerank_feature(tags, matID, matchpool, k, algo)
    else:
        return util.return_error("algo unknown")

    cands = list(results.keys())
    cands.sort(reverse=True, key=(lambda x:results[x]))
    cands = cands[0:min(k-1,len(cands))]

    topk = []
    for c in cands:
        topk.append({
            'id' : c,
            'score' : results[c],
            'title': data.material_lookup[c]['title']
            }
        )
    
    return util.return_object({
        'query' : {
            'tags' : list(tags),
            'matID': matID,
            'k': k,
            'algo': algo,
            'matchpool': matchpoolstr
        },
        'results' : topk
    })
