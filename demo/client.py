import grpc

import hostagent_pb2
import hostagent_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = hostagent_pb2_grpc.LandscapeHostAgentStub(channel)


def generate_hostagentinfo():
    yield hostagent_pb2.HostAgentInfo(
        token="testprotoken",
        id="testmachine-testuserid",
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
        ]
    )


if __name__ == "__main__":
    for received_command in stub.Connect(generate_hostagentinfo()):
        print("Recieved command")
        print(received_command)
