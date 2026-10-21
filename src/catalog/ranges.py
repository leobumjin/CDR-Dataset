"""Expand an inclusive source-owned ID range from class.yaml."""


def reserved_ids(collection):
    indices = collection.get('indices')
    if (not isinstance(indices, list) or len(indices) != 2
            or any(type(i) is not int for i in indices)
            or not 1 <= indices[0] <= indices[1] <= 9999):
        raise ValueError('indices must be an inclusive [start, end] range within 1..9999')
    source = collection.get('source')
    if not isinstance(source, str) or not source:
        raise ValueError('Collection requires source')
    identifiers = collection.get('identifiers', {'prefix': 'bird_', 'digits': 4})
    return {f"{identifiers['prefix']}{i:0{identifiers['digits']}d}":
            {'source': source, 'concept_uri': None} for i in range(indices[0], indices[1] + 1)}
