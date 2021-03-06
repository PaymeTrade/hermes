from hermes.ws.channels.base import Base


class Heartbeat(Base):
    name = "heartbeat"

    def __call__(self, heartbeatTime):
        data = {
            "msg": {
                "heartbeatTime": int(heartbeatTime),
                "userTime": int(self.api.time_sync.server_timestamp * 1000)
            }
        }

        self.send_websocket_request(self.name, data, no_force_send=False)
