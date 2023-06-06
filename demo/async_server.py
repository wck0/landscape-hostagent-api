import asyncio
import logging
import grpc

import hostagent_pb2
import hostagent_pb2_grpc


class LandscapeHostAgentServicer(hostagent_pb2_grpc.LandscapeHostAgentServicer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.commands = [
            hostagent_pb2.Command(
                install=hostagent_pb2.Command.Install(
                    id="testid",
                ),
            )
        ]

    async def Connect(self, request_iterator, context):
        print("Connect request from client")
        async for r in request_iterator:
            print("Got request")
            print(r)

        for c in self.commands:
            print("Sending command")
            print(c)
            yield c


async def serve():
    server = grpc.aio.server()
    hostagent_pb2_grpc.add_LandscapeHostAgentServicer_to_server(
        LandscapeHostAgentServicer(),
        server,
    )
    server.add_insecure_port("[::]:50051")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
