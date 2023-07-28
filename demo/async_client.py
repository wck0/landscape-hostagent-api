import asyncio
import logging
import grpc

import hostagent_pb2
import hostagent_pb2_grpc


class FakeHostAgentClient:
    token = "testprotoken"
    uid = "testmachine-testuserid"
    hostname = "testhostname"
    instances = [
        hostagent_pb2.HostAgentInfo.InstanceInfo(
            id="testinstanceid",
            name="testinstancename",
            version_id="jammy",
            instance_state=hostagent_pb2.InstanceState.Running,
        ),
        hostagent_pb2.HostAgentInfo.InstanceInfo(
            id="testinstanceid2",
            name="testinstancename2",
            version_id="focal",
            instance_state=hostagent_pb2.InstanceState.Stopped,
        ),
    ]

    # see https://grpc.github.io/grpc/core/group__grpc__arg__keys.html
    channel_options = {
        # After a duration of this time the client/server pings its peer
        # to see if the transport is still alive.
        "grpc.keepalive_time_ms": 8_000,  # 8s
        # After waiting for a duration of this time,
        # if the keepalive ping sender does not receive the ping ack,
        # it will close the transport.
        "grpc.keepalive_timeout_ms": 5_000,  # 5s
        # How many pings can the client send before needing to send a data/header frame?
        "grpc.http2.max_pings_without_data": 5,
        # Is it permissible to send keepalive pings from the client without any outstanding streams.
        "grpc.keepalive_permit_without_calls": 1,
    }

    def __init__(self, token, uid, hostname, instances=None, channel_options=None):
        self.token = token
        self.uid = uid
        self.hostname = hostname
        if instances:
            self.instances = instances
        if channel_options:
            self.channel_options.update(channel_options)

    async def run(self):
        print(f"Starting client {self.uid}")
        async with grpc.aio.insecure_channel(
            "10.117.1.114:50051", options=self.prepare_channel_options()
            # "10.117.1.158:50051", options=self.prepare_channel_options()
            # "10.117.1.100:50051", options=self.prepare_channel_options()
        ) as channel:
            await channel.channel_ready()
            self.stub = hostagent_pb2_grpc.LandscapeHostAgentStub(channel)
            await self.connect()

    async def connect(self):
        call = self.stub.Connect(self.generate_hostagent_info())
        while True:
            async for response in call:
                await self.handle_response(response)

            await asyncio.sleep(1)

    def generate_hostagent_info(self):
        yield hostagent_pb2.HostAgentInfo(
            token=self.token,
            uid=self.uid,
            hostname=self.hostname,
            instances=self.instances,
        )

    def prepare_channel_options(self):
        return [(key, value) for key, value in self.channel_options.items()]

    async def handle_response(self, response):
        cmd = response.WhichOneof("cmd")
        handler = None
        if cmd:
            handler = getattr(self, "handle_" + cmd, None)
        if handler:
            await handler(response)

    async def handle_assign_host(self, response):
        print("assign_host", response.assign_host.uid)
        self.uid = response.assign_host.uid
        await self.connect()

    async def handle_install(self, response):
        print("install", response.install.id)

    async def handle_set_default(self, response):
        print("set_default", response.set_default.id)

    async def handle_shutdown_host(self, response):
        print("shutdown_host", response.shutdown_host)

    async def handle_start(self, response):
        print("start", response.start.id)

    async def handle_stop(self, response):
        print("stop", response.stop.id)

    async def handle_uninstall(self, response):
        print("uninstall", response.uninstall.id)


def generate_hostagentinfo():
    yield hostagent_pb2.HostAgentInfo(
        token="testprotoken",
        uid="testmachine-testuserid",
        hostname="testhostname",
        instances=[
            hostagent_pb2.HostAgentInfo.InstanceInfo(
                id="testinstanceid",
                name="testinstancename",
                version_id="jammy",
                instance_state=hostagent_pb2.InstanceState.Running,
            ),
            hostagent_pb2.HostAgentInfo.InstanceInfo(
                id="testinstanceid2",
                name="testinstancename2",
                version_id="focal",
                instance_state=hostagent_pb2.InstanceState.Stopped,
            ),
        ],
    )


def get_uid():
    # import uuid
    # uid = uuid.uuid4().hex
    # uid = "test-uid"
    import string
    import random

    uid = "".join(random.choices(string.ascii_lowercase, k=8))
    return uid


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u", "--uid", type=str, default="", help="uid for the host agent"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    uid = args.uid
    client = FakeHostAgentClient("testprotoken", uid, "testhostname")
    asyncio.run(client.run())
