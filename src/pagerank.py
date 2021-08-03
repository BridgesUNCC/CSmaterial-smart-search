from flask import Flask, Response, Blueprint, request
from matplotlib import pyplot as plt
from sklearn.manifold import MDS
import networkx as nx

import util
import data

pagerank_blueprint = Blueprint('pagerank', __name__)


@pagerank_blueprint.route('/pagerank')
def pagerank_feature():
    matID = []
    
    # declare an empty graph from the NetworkX module
    g = nx.Graph()

    # add the classification edges (between materials and tags)

    for mid in data.material_lookup:
        mat = data.material_lookup[mid]
        if 'tags' in mat:
            for tags in mat['tags']:
                if tags['id'] in data.all_acm_ids:
                    g.add_edge("m" + str(mat['id']), "t" + str(tags['id']))

    # ontology edges/for all ACM tags tid: add edge between tid and parent tid
    for t in data.all_acm_ids:
        if 'parent' in data.acm_lookup[t]:
            parentid = data.acm_lookup[t]['parent']
            g.add_edge("t" + str(parentid), "t" + str(t))

        # nx.write_edgelist(g, "test.edgelist", data=False)
        # f = plt.figure()
        # nx.draw_spring(g, with_labels=True, ax=f.add_subplot(111))
        # f.savefig('graph.png')
        # return 'empty'

    matID = util.argument_to_IDlist('matID')

    perso = {}
    for id in matID:
        perso["m"+str(id)] = 1./len(matID)
    

    pr = nx.pagerank(g, alpha=0.85, personalization=perso, max_iter=100,
                     tol=1e-06, nstart=None,
                     weight='weight', dangling=None)

    res = []
    
    for e in pr:
        if e[0] == 'm':
            id = int (e[1:])
            if id not in matID:
                val = pr[e]
                res.append((id, val, data.material_lookup[id]['title']))
            
    res.sort(key=lambda p: p[1], reverse=True)

    k = 30
    
    return util.return_object(res[0:min(k,len(res))])
