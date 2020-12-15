import jwt
import datetime as dt
import asyncio
from aiohttp import web
from aiohttp_apispec import (docs, request_schema)
from marshmallow import Schema, fields

from app.devices.models import get_device_env
from .models import create_detection


# default interval in milliseconds
DEFAULT_INTEVAL = 3000


class NewDetectionRequestSchema(Schema):
    uuid = fields.String(required=True)
    distance = fields.Float(required=False)
    major = fields.Integer(required=True)
    minor = fields.Integer(required=True)
    rssi = fields.Integer(required=False)
    rxpower = fields.Integer(required=True)


class NewDetectionView(web.View):
    """
    Storing new detection
    """
    @docs(
        tags=['detection'],
        summary='View to create detection'
    )
    @request_schema(NewDetectionRequestSchema())
    async def post(self):
        """
        There we do need to create detection entity in database
        """
        async with self.request.app['db'].acquire() as conn:
            data = await self.process_detection_data(
                self.request.get('data'), conn)
            await asyncio.wait([
                self.request.app['event_bus'].new_detection(data),
                create_detection(data, conn)
            ])
        return web.json_response(status=201)

    async def process_detection_data(self, data, conn):
        """
        Convert api data to database structure
        Extracting hub info from jwt token
        Calculating distance

        :param data:
        :return:
        """
        token_data = self.request['jwt_data']
        detection = dict(
            hubId=token_data['hubId'],
            objectId=data['uuid'],
            distance=await self.get_distance(data, conn),
            major=data['major'],
            minor=data['minor'],
            rxpower=data['rxpower'],
        )
        rssi = data.get('rssi')
        if rssi:
            detection['rssi'] = rssi
        return detection

    async def get_distance(self, data, conn):
        providen_distance = data.get('distance')
        if providen_distance:
            return providen_distance
        env = await get_device_env(data['uuid'], conn)
        return 10**((data['rxpower']-data['rssi'])/10/env)


class ListDetectionsRequestSchema(Schema):
    period = fields.Integer(required=False, default=3000)
    hubs = fields.List(fields.String, required=True)
    devices = fields.List(fields.String, required=True)


class DeviceDetectionView(web.View):
    @docs(
        tags=['detection'],
        summary='View to get device detection'
    )
    @request_schema(ListDetectionsRequestSchema)
    async def get(self):
        """get list of device detections over the period"""
        params = self.request.query
        hubs = []
        devices = []
        interval = params.get('interval') or DEFAULT_INTEVAL

        if 'hubs' in params:
            hubs.extend(params.getall('hubs'))
        if 'devices' in params:
            devices.extend(params.getall('devices'))

        return web.json_response(data=dict(
            interval=interval,
            devices=devices,
            hubs=hubs
        ), status=200)



