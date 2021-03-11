class RoombaInfo:
    hostname = None
    firmware = None
    ip = None
    mac = None
    robot_name = None
    sku = None
    capabilities = None
    blid = None
    password = None

    def __init__(
        self, hostname, robot_name, ip, mac, firmware, sku, capabilities
    ):
        """Create object with information about roomba."""
        self.hostname = hostname
        self.firmware = firmware
        self.ip = ip
        self.mac = mac
        self.robot_name = robot_name
        self.sku = sku
        self.capabilities = capabilities
        self.blid = hostname.split("-")[1]

    def __str__(self) -> str:
        """Nice output to console."""
        return ", ".join(
            [
                "{key}={value}".format(key=key, value=self.__dict__.get(key))
                for key in self.__dict__
            ]
        )

    def __hash__(self) -> int:
        """Hashcode."""
        return hash(self.mac)

    def __eq__(self, o: object) -> bool:
        """Equals."""
        return isinstance(o, RoombaInfo) and self.mac == o.mac
