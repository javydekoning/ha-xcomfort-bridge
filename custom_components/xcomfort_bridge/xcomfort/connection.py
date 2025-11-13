"""Connection module for xComfort integration."""

from base64 import b64decode, b64encode
from enum import IntEnum
import json
import logging
import secrets
import string

import aiohttp
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import rx
import rx.operators as ops

from .constants import Messages

_LOGGER = logging.getLogger(__name__)


class ConnectionState(IntEnum):
    """Connection state enumeration."""

    Initial = 1
    Loading = 2
    Loaded = 3


def generateSalt():
    """Generate a random salt string."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(12))


def hash_password(deviceId, authKey, salt):
    """Hash password for authentication."""
    hasher = SHA256.new()
    hasher.update(deviceId)
    hasher.update(authKey)
    inner = hasher.hexdigest().encode()
    hasher = SHA256.new()
    hasher.update(salt)
    hasher.update(inner)

    return hasher.hexdigest()


def _pad_string(value):
    """Pad string to AES block size."""
    length = len(value)
    pad_size = AES.block_size - (length % AES.block_size)
    return value.ljust(length + pad_size, b"\x00")


def _raise_connection_error(msg):
    """Raise connection error."""
    raise ConnectionError(msg)


def _raise_login_error(msg):
    """Raise login error."""
    raise ConnectionError(msg)


def _raise_secure_connection_error(msg):
    """Raise secure connection error."""
    raise ConnectionError(msg)


def _raise_token_error(msg):
    """Raise token error."""
    raise ConnectionError(msg)


def _raise_renew_token_error(msg):
    """Raise renew token error."""
    raise ConnectionError(msg)


async def setup_secure_connection(session, ip_address, authkey):
    """Set up secure connection to xComfort bridge."""
    _LOGGER.info("Setting up secure connection to %s", ip_address)

    async def __receive(ws):
        """Receive message from websocket."""
        msg = await ws.receive()
        msg = msg.data[:-1]
        parsed = json.loads(msg)
        _LOGGER.debug("Received websocket message type: %s", parsed.get("type_int"))
        return parsed

    async def __send(ws, data):
        """Send message to websocket."""
        msg = json.dumps(data)
        _LOGGER.debug("Sending websocket message type: %s", data.get("type_int"))
        await ws.send_str(msg)

    _LOGGER.debug("Connecting websocket to http://%s/", ip_address)
    ws = await session.ws_connect(f"http://{ip_address}/")

    try:
        msg = await __receive(ws)

        # {'type_int': 0, 'ref': -1, 'info': 'no client-connection available (all used)!'}
        if msg["type_int"] == Messages.NACK:
            _LOGGER.error("Connection rejected: %s", msg.get("info"))
            _raise_connection_error(msg["info"])

        deviceId = msg["payload"]["device_id"]
        connectionId = msg["payload"]["connection_id"]
        _LOGGER.debug("Received device_id: %s, connection_id: %s", deviceId, connectionId)

        _LOGGER.debug("Sending connection confirmation")
        await __send(
            ws,
            {
                "type_int": 11,
                "mc": -1,
                "payload": {
                    "client_type": "shl-app",
                    "client_id": "c956e43f999f8004",
                    "client_version": "3.0.0",
                    "connection_id": connectionId,
                },
            },
        )

        msg = await __receive(ws)

        if msg["type_int"] == Messages.CONNECTION_DECLINED:
            _LOGGER.error("Connection declined: %s", msg["payload"].get("error_message"))
            _raise_connection_error(msg["payload"]["error_message"])

        _LOGGER.debug("Initiating secure connection")
        await __send(ws, {"type_int": 14, "mc": -1})

        msg = await __receive(ws)
        publicKey = msg["payload"]["public_key"]
        _LOGGER.debug("Received public key for encryption")

        rsa = RSA.import_key(publicKey)

        key = get_random_bytes(32)
        iv = get_random_bytes(16)
        _LOGGER.debug("Generated AES key and IV")

        cipher = PKCS1_v1_5.new(rsa)
        secret = b64encode(cipher.encrypt((key.hex() + ":::" + iv.hex()).encode()))
        secret = secret.decode()
        _LOGGER.debug("Encrypted session secret with RSA")

        await __send(ws, {"type_int": 16, "mc": -1, "payload": {"secret": secret}})

        connection = SecureBridgeConnection(ws, key, iv, deviceId)
        _LOGGER.debug("Created SecureBridgeConnection instance")

        # Start LOGIN
        _LOGGER.debug("Starting authentication process")

        msg = await connection.receive()

        if msg["type_int"] != 17:
            _LOGGER.error("Secure connection not established (expected type 17, got %s)", msg["type_int"])
            _raise_secure_connection_error("Failed to establish secure connection")

        salt = generateSalt()
        password = hash_password(deviceId.encode(), authkey.encode(), salt.encode())
        _LOGGER.debug("Generated authentication credentials")

        await connection.send_message(
            30, {"username": "default", "password": password, "salt": salt}
        )

        msg = await connection.receive()

        if msg["type_int"] != 32:
            _LOGGER.error("Login failed (expected type 32, got %s)", msg["type_int"])
            _raise_login_error("Login failed")

        token = msg["payload"]["token"]
        _LOGGER.debug("Login successful, received auth token")

        await connection.send_message(33, {"token": token})

        # {"type_int":34,"mc":-1,"payload":{"valid":true,"remaining":8640000}}
        msg = await connection.receive()
        _LOGGER.debug("Token validation response: valid=%s, remaining=%s",
                     msg.get("payload", {}).get("valid"),
                     msg.get("payload", {}).get("remaining"))

        # Renew token
        _LOGGER.debug("Renewing auth token")
        await connection.send_message(37, {"token": token})

        msg = await connection.receive()

        if msg["type_int"] != 38:
            _LOGGER.error("Token renewal failed (expected type 38, got %s)", msg["type_int"])
            _raise_renew_token_error("Token renewal failed")

        token = msg["payload"]["token"]
        _LOGGER.debug("Token renewed successfully")

        await connection.send_message(33, {"token": token})

        # {"type_int":34,"mc":-1,"payload":{"valid":true,"remaining":8640000}}
        msg = await connection.receive()
        _LOGGER.debug("Renewed token validation: valid=%s, remaining=%s",
                     msg.get("payload", {}).get("valid"),
                     msg.get("payload", {}).get("remaining"))

    except Exception:
        _LOGGER.exception("Error during connection setup")
        await ws.close()
        raise

    else:
        _LOGGER.info("Secure connection setup complete")
        return connection

class SecureBridgeConnection:
    """Secure connection to xComfort bridge."""

    def __init__(self, websocket, key, iv, device_id):
        """Initialize secure connection."""
        self.websocket = websocket
        self.key = key
        self.iv = iv
        self.device_id = device_id

        self.state = ConnectionState.Initial
        self._messageSubject = rx.subject.Subject()
        self.mc = 0

        self.messages = self._messageSubject.pipe(ops.as_observable())

    def __cipher(self):
        """Get AES cipher for encryption/decryption."""
        return AES.new(self.key, AES.MODE_CBC, self.iv)

    def __decrypt(self, data):
        """Decrypt received data."""
        ct = b64decode(data)
        data = self.__cipher().decrypt(ct)
        data = data.rstrip(b"\x00")

        if not data:
            return {}

        return json.loads(data.decode())

    async def pump(self):
        """Pump messages from the connection."""
        self.state = ConnectionState.Loading
        _LOGGER.debug("Starting message pump")

        _LOGGER.debug("Requesting initial data from bridge")
        await self.send_message(240, {})
        await self.send_message(242, {})
        await self.send_message(2, {})

        _LOGGER.info("Message pump active, listening for messages")
        async for msg in self.websocket:
            if msg.type == aiohttp.WSMsgType.TEXT:
                result = self.__decrypt(msg.data)

                if "mc" in result:
                    # ACK
                    _LOGGER.debug("Sending ACK for message counter %s", result["mc"])
                    await self.send({"type_int": 1, "ref": result["mc"]})

                if "payload" in result:
                    _LOGGER.debug("Publishing message to subscribers: type=%s", result.get("type_int"))
                    self._messageSubject.on_next(result)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                _LOGGER.error("Websocket error received, breaking pump loop")
                break

        _LOGGER.info("Message pump stopped")

    async def close(self):
        """Close the connection."""
        _LOGGER.debug("Closing websocket connection")
        await self.websocket.close()

    async def receive(self):
        """Receive a message from the connection."""
        msg = await self.websocket.receive()
        decrypted = self.__decrypt(msg.data)
        _LOGGER.debug("Received and decrypted message type: %s", decrypted.get("type_int"))
        return decrypted

    async def send_message(self, message_type, payload):
        """Send a message through the connection."""
        self.mc += 1

        if isinstance(message_type, Messages):
            message_type_name = message_type.name
            message_type = message_type.value
        else:
            message_type_name = message_type

        _LOGGER.debug("Sending message type %s (mc=%s)", message_type_name, self.mc)
        await self.send({"type_int": message_type, "mc": self.mc, "payload": payload})

    async def send(self, data):
        """Send data through the connection."""
        msg = json.dumps(data)
        msg = _pad_string(msg.encode())
        msg = self.__cipher().encrypt(msg)
        msg = b64encode(msg).decode() + "\u0004"
        _LOGGER.debug("Encrypted and sending message: type=%s", data.get("type_int"))
        await self.websocket.send_str(msg)
