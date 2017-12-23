# -*- coding: utf-8 -*-
"""
lambda_decorators
=================

🐍λ✨ - A collection of useful decorators for making AWS Lambda handlers

NOTE: this is in very early stages of development.

Quick example
-------------
.. code:: python

    # handler.py

    from lambda_decorators import cors, json_http_resp, load_json_body

    @cors
    @json_http_resp
    @load_json_body
    handler(event, context):
        return {'hello': event['body']['name']}

Install - TODO
--------------
.. code:: shell

    pip install lambda_decorators

Included Decorators:
--------------------
    * :meth:`async_handler` - support for async handlers
    * :meth:`cors` - automatic injection of CORS headers
    * :meth:`dump_json_body` - auto-serialization of http body to JSON
    * :meth:`json_http_resp` - automatic serialization of python object to HTTP JSON response
    * :meth:`load_json_body` - auto-deserialize of http body from JSON
    * :meth:`no_retry_on_failure` - detect and stop retry attempts for scheduled lambdas

See each individual decorators for specific usage details and the
`examples<https://github.com/dschep/lambda-decorators/tree/master/example>`_
for some more use cases.

-----

"""

import asyncio
import json
from functools import wraps


def async_handler(handler):
    """
    This decorator allows for use of async handlers by automatically running
    them in an event loop.

    Usage::

      @async_handler
      async def handler(event, context):
          return await foobar()
    """
    @wraps(handler)
    def wrapper(event, context):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(handler())

    return wrapper


def cors(handler_or_origin):
    """
Automatically injects Access-Control-Allow-Origin headers to http
responses.

Usage::

        @cors
        def hello(example, context):
            return {'body': 'foobar'}
        # or with custom domain
        @cors('https://example.com')
        def hello_custom_origin(example, context):
            return {'body': 'foobar'}

the ``hello`` example returns

.. code:: python

    {'body': 'foobar', 'headers': {'Access-Control-Allow-Origin': '*'}}
    """
    if isinstance(handler_or_origin, str):
        def wrapper_wrapper(handler):
            @wraps(handler)
            def wrapper(event, context):
                response = handler(event, context)
                headers = response.setdefault('headers', {})
                headers['Access-Control-Allow-Origin'] = handler_or_origin
                return response

            return wrapper

        return wrapper_wrapper
    else:
        return cors('*')(handler_or_origin)


def dump_json_body(handler):
    """
Automatically serialize response bodies with json.dumps.

Returns a 500 error if the response cannot be serialized

Usage::

  @dump_json_body
  @def handler(event, context):
      return {'statusCode': 200, 'body': {'hello': 'world'}}

in this example, the decorators handler returns:

.. code:: python

    {'statusCode': 200, 'body': '{"hello": "world"}'}
    """
    @wraps(handler)
    def wrapper(event, context):
        response = handler(event, context)
        if 'body' in response:
            try:
                response['body'] = json.dumps['body']
            except Exception as exc:
                return {'statusCode': 500, 'body': str(exc)}
        return response


def json_http_resp(handler):
    """
Automatically serialize return value to the body of a successfull HTTP
response.

Returns a 500 error if the response cannot be serialized

Usage::

    @json_http_resp
    def handler(event, context):
        return {'hello': 'world'}

in this example, the decorated handler returns:

.. code:: python

    {'statusCode': 200, 'body': '{"hello": "world"}'}
    """
    @wraps(handler)
    def wrapper(event, context):
        response = handler(event, context)
        try:
            body = json.dumps(response)
        except Exception as exc:
            return {'statusCode': 500, body: str(exc)}
        return {'statusCode': 200, 'body': body}

    return wrapper

    return wrapper


def load_json_body(handler):
    """
    Automatically deserialize event bodies with json.loads.

    Automatically returns a 400 BAD REQUEST if there is an error while parsing.

    Usage::

      @load_json_body
      def handler(event, context):
          return event['body']['foobar']

    note that event['body'] is already a dictionary and didn't have to
    explicitly be parsed.
    """
    @wraps(handler)
    def wrapper(event, context):
        if isinstance(event.get('body'), str):
            try:
                event['body'] = json.loads(event['body'])
            except:
                return {'statusCode': 400, 'body': 'BAD REQUEST'}
        return handler(event, context)

    return wrapper


def no_retry_on_failure(handler):
    """
    AWS Lambda retries scheduled lambdas that don't execute succesfully.

    This detects this by storing requests IDs in memory and exiting early on
    duplicates. Since this is in memory, don't use it on very frequently
    scheduled lambdas. It raises a ``RuntimeError``
    """
    seen_request_ids = set()

    @wraps(handler)
    def wrapper(event, context):
        if context.aws_request_id in seen_request_ids:
            raise RuntimeError(('Retry attempt on request id '
                                '{} detected.').format(context.aws_request_id))
        seen_request_ids.add(context.aws_request_id)
        return handler(event, context)

    return wrapper
