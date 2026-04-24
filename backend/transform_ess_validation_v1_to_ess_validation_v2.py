def transform_source_to_target(source: dict) -> dict:
    """Auto-generated transformer: Source → Target"""
    target = {}

    # [DIRECT] data → data
    target['data'] = source.get('data')

    # [DIRECT] data.description → data.description
    target['data'] = target['data'] if isinstance(target['data'], dict) else {}
    target['data'].setdefault('description', {})
    target['data']['description'] = source.get('data').get('description')

    # [DIRECT] data.source → data.source
    target['data'] = target['data'] if isinstance(target['data'], dict) else {}
    target['data'].setdefault('source', {})
    target['data']['source'] = source.get('data').get('source')

    # [DIRECT] data.target → data.target
    target['data'] = target['data'] if isinstance(target['data'], dict) else {}
    target['data'].setdefault('target', {})
    target['data']['target'] = source.get('data').get('target')

    # [DIRECT] event → event
    target['event'] = source.get('event')

    # [DIRECT] event.actor → event.actor
    target['event'] = target['event'] if isinstance(target['event'], dict) else {}
    target['event'].setdefault('actor', {})
    target['event']['actor'] = source.get('event').get('actor')

    # [DIRECT] event.agent → event.agent
    target['event'] = target['event'] if isinstance(target['event'], dict) else {}
    target['event'].setdefault('agent', {})
    target['event']['agent'] = source.get('event').get('agent')

    # [DIRECT] event.time → event.time
    target['event'] = target['event'] if isinstance(target['event'], dict) else {}
    target['event'].setdefault('time', {})
    target['event']['time'] = source.get('event').get('time')

    # [DIRECT] event.trigger → event.trigger
    target['event'] = target['event'] if isinstance(target['event'], dict) else {}
    target['event'].setdefault('trigger', {})
    target['event']['trigger'] = source.get('event').get('trigger')

    # [DIRECT] type → type
    target['type'] = source.get('type')

    # [DIRECT] value → value
    target['value'] = source.get('value')

    # [RENAME] id → ID
    target['ID'] = source.get('id')

    # [RENAME] rule → rules
    target['rules'] = source.get('rule')

    return target
