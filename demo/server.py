from concurrent import futures

import grpc

import hostagent_pb2
import hostagent_pb2_grpc


class LandscapeHostAgentServicer(hostagent_pb2_grpc.LandscapeHostAgentServicer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.commands = [
            hostagent_pb2.Commands(
                install=hostagent_pb2.Commands.Install(
                    id="testid",
                ),
            )
        ]

    def Connect(self, request_iterator, context):
        print("Connect request from client")
        for r in request_iterator:
            print("Got request")
            print(r)

        for c in self.commands:
            print("Sending command")
            print(c)
            yield c


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hostagent_pb2_grpc.add_LandscapeHostAgentServicer_to_server(
        LandscapeHostAgentServicer(),
        server,
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
