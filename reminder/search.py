from flask import current_app
import json


def add_to_index(index, model):
    """
    Function add entries to the index
    """
    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, id=model.id, body=payload)


def remove_from_index(index, model):
    """
    Function deletes the document stored under the given id (remove entries from the index)
    """
    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        return
    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page, filter_data=None):
    """
     Function takes the index name and a text to search for, along with pagination controls,
     so that search results can be paginated like Flask-SQLAlchemy results are
    """
    if not current_app.elasticsearch or not current_app.elasticsearch.ping():
        return [], 0
    if not filter_data:
        body_dict = {
            'query': {
                'multi_match': {
                    'query': query,
                    'fields': ['*']
                }
            },
            'from': (page - 1) * per_page,
            'size': per_page
        }
    else:
        body_dict = {
            'query': {
                'bool': {
                    'must': {
                        'multi_match': {
                            'query': query,
                            'fields': ['*']
                        }
                    },
                    'filter': {
                        'term': filter_data
                    },
                },
            },
            'from': (page - 1) * per_page,
            'size': per_page
        }
    search = current_app.elasticsearch.search(
        index=index,
        body=json.dumps(body_dict))
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']