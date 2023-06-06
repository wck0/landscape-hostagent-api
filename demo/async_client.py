import asyncio
import logging
import grpc

import hostagent_pb2
import hostagent_pb2_grpc


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


async def connect(stub):
    call = stub.Connect(generate_hostagentinfo())
    async for response in call:
        print("client received", response)


async def run():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = hostagent_pb2_grpc.LandscapeHostAgentStub(channel)
        await connect(stub)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
