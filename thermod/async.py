# -*- coding: utf-8 -*-
"""Draft long polling socket

Copyright (C) 2017 Simone Rossetto <simros85@gmail.com>

This file is part of Thermod.

Thermod is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Thermod is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Thermod.  If not, see <http://www.gnu.org/licenses/>.
"""

import asyncio
from aiohttp import web

__date__ = '2017-03-19'
__updated__ = '2017-03-19'
__version__ = '0.1'


async def return_author(request):
    a = await request.app['q'].get()
    return web.json_response(a)

async def put_author(request):
    q = request.app['q']
    p = await request.post()
    a = p.get('author', 'unknown')
    print(a)
    await q.put({'author': a})
    #print([q.put_nowait({'author': a}) for i in range(q.qsize())])
    return web.Response()


loop = asyncio.get_event_loop()
app = web.Application(loop=loop)
queue = asyncio.Queue(loop=loop)

app['q'] = queue
app.router.add_get('/', return_author)
app.router.add_post('/', put_author)
web.run_app(app, host='127.0.0.1', port=8080)

# vim: fileencoding=utf-8 tabstop=4 shiftwidth=4 expandtab