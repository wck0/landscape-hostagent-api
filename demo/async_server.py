import asyncio
from configparser import ConfigParser
import datetime
import grpc
import json
import logging
import urllib.parse

import aio_pika
import hostagent_pb2
import hostagent_pb2_grpc


CONFIG_FILE = "demo/landscape_hostagent.conf"


def get_ampq_config():
    config_parser = ConfigParser()
    config_parser.read(CONFIG_FILE)
    host = config_parser.get("rabbitmq", "host", fallback="localhost")
    port = config_parser.get("rabbitmq", "port", fallback=5672)
    user = config_parser.get("rabbitmq", "user", fallback="guest")
    password = config_parser.get("rabbitmq", "password", fallback="guest")
    vhost = config_parser.get("rabbitmq", "virtual_host", fallback="/")
    # / is the default vhost for RabbitMQ and needs to be escaped as %2F
    # so we override the safe parameter's default of "/"
    quoted_vhost = urllib.parse.quote(vhost, safe="")
    ampq_url = f"ampq://{user}:{password}@{host}:{port}/{quoted_vhost}"
    task_queue = config_parser.get(
        "rabbitmq",
        "landscape_task_queue",
        fallback="landscape-server-hostagent-task-queue",
    )

    return dict(
        host=host,
        port=port,
        user=user,
        password=password,
        vhost=vhost,
        ampq_url=ampq_url,
        task_queue=task_queue,
    )


def get_grpc_server_config():
    # There are many grpc configuration parameters.
    # See https://grpc.github.io/grpc/core/group__grpc__arg__keys.html
    # They all start with "grpc." and the config file should match.
    # Some values must be sent as integers and not as strings.
    # We just convert all digit string values to integers,
    # rather than use the `getint` method of `ConfigParser`
    # so we don't have to write separate handling rules for every
    # individual grpc configuration parameter.
    config_parser = ConfigParser()
    config_parser.read(CONFIG_FILE)
    return [
        (key, int(value)) if value.isdigit() else (key, value)
        for key, value in config_parser.items("grpc")
    ]


class LandscapeHostAgentServicer(hostagent_pb2_grpc.LandscapeHostAgentServicer):
    ampq_config = get_ampq_config()
    server_options = get_grpc_server_config()

    async def Connect(self, request_iterator, context):
        print(type(context))
        print(dir(context))
        async for request in request_iterator:
            if not request.uid:
                command = self.assign_uid(request)
                yield command
            else:
                await self.handle_request(request)
                uid = request.uid
                async for c in self.get_commands(uid):
                    yield c

    def assign_uid(self, request):
        import uuid
        uid = uuid.uuid4().hex
        message = json.dumps({"assign_host": uid})
        command = self.get_command(message)
        return command

    async def handle_request(self, request):
        json_serialized_request = self.serialize_request(request)
        print(json_serialized_request)
        connection = await aio_pika.connect_robust(url=self.ampq_config["ampq_url"])
        channel = await connection.channel()
        await channel.declare_queue(self.ampq_config["task_queue"])
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json_serialized_request,
            ),
            routing_key=self.ampq_config["task_queue"],
        )
        await connection.close()

    def serialize_request(self, request):
        request_as_dict = dict(
            hostname=request.hostname,
            token=request.token,
            uid=request.uid,
            instances=self.serialize_instances(request.instances),
        )
        return json.dumps(request_as_dict).encode()

    def serialize_instances(self, instances):
        return [
            dict(
                id=instance.id,
                instance_state=instance.instance_state,
                name=instance.name,
                version_id=instance.version_id,
            )
            for instance in instances
        ]

    async def get_commands(self, uid):
        connection = await aio_pika.connect_robust(url=self.ampq_config["ampq_url"])

        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(uid, auto_delete=False)

            async with queue.iterator() as queue_iterator:
                async for message in queue_iterator:
                    async with message.process():
                        yield self.get_command(message.body)

    def get_command(self, message_body):
        # TODO: handle fall through cases somehow
        command_json = json.loads(message_body)
        match command_json:
            case {"assign_host": uid}:
                command = hostagent_pb2.Command(
                    assign_host=hostagent_pb2.Command.AssignHost(
                        uid=uid,
                    )
                )
            case {"install": id}:
                command = hostagent_pb2.Command(
                    install=hostagent_pb2.Command.Install(
                        id=id,
                    )
                )
            case {"set_default": id}:
                command = hostagent_pb2.Command(
                    set_default=hostagent_pb2.Command.SetDefault(
                        id=id,
                    )
                )
            case {"shutdown_host": None}:
                command = hostagent_pb2.Command(
                    shutdown_host=hostagent_pb2.Command.ShutdownHost()
                )
            case {"start": id}:
                command = hostagent_pb2.Command(
                    start=hostagent_pb2.Command.Start(
                        id=id,
                    )
                )
            case {"stop": id}:
                command = hostagent_pb2.Command(
                    stop=hostagent_pb2.Command.Stop(
                        id=id,
                    )
                )
            case {"uninstall": id}:
                command = hostagent_pb2.Command(
                    uninstall=hostagent_pb2.Command.Uninstall(
                        id=id,
                    )
                )
        return command

    async def serve(self):
        self._server = grpc.aio.server(options=self.server_options)
        hostagent_pb2_grpc.add_LandscapeHostAgentServicer_to_server(
            LandscapeHostAgentServicer(),
            self._server,
        )
        self._server.add_insecure_port("[::]:50051")
        await self._server.start()
        await self._server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = LandscapeHostAgentServicer()
    asyncio.run(server.serve())
