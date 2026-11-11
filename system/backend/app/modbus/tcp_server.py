"""Pure-Python asyncio Modbus TCP Server (Unit ID 1, FC03/FC06/FC16) + TCP Read Client."""
from __future__ import annotations

import asyncio
import struct
import threading
from typing import Callable, Dict, List, Optional


class ModbusRegisterBank:
    """Thread-safe 16-bit holding register image covering Modbus 40001..40640 (offsets 0..639)."""

    def __init__(self, size: int = 640) -> None:
        self._lock = threading.RLock()
        self._regs: List[int] = [0] * size
        self._on_write: Optional[Callable[[int, List[int]], None]] = None

    def set_write_callback(self, cb: Callable[[int, List[int]], None]) -> None:
        self._on_write = cb

    def read(self, offset: int, count: int) -> List[int]:
        with self._lock:
            if offset < 0 or offset + count > len(self._regs):
                raise ValueError("Illegal data address")
            return list(self._regs[offset : offset + count])

    def write(self, offset: int, values: List[int], notify: bool = False) -> None:
        with self._lock:
            if offset < 0 or offset + len(values) > len(self._regs):
                raise ValueError("Illegal data address")
            for idx, val in enumerate(values):
                self._regs[offset + idx] = val & 0xFFFF
        if notify and self._on_write is not None:
            self._on_write(offset, values)


class ModbusTcpServer:
    """Minimal RFC-compliant Modbus/TCP server for Holding Registers (FC 03, 06, 16)."""

    def __init__(self, bank: ModbusRegisterBank, host: str = "127.0.0.1", port: int = 5020, unit_id: int = 1) -> None:
        self.bank = bank
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self._server: Optional[asyncio.AbstractServer] = None

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        socks = self._server.sockets
        if socks:
            self.port = int(socks[0].getsockname()[1])
        return self.port

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                mbap = await reader.readexactly(7)
                tx_id, proto_id, length, unit_id = struct.unpack(">HHHB", mbap)
                if proto_id != 0 or length < 2:
                    break
                pdu = await reader.readexactly(length - 1)
                resp_pdu = self._process_pdu(pdu)
                resp_mbap = struct.pack(">HHHB", tx_id, 0, len(resp_pdu) + 1, unit_id)
                writer.write(resp_mbap + resp_pdu)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def _process_pdu(self, pdu: bytes) -> bytes:
        fc = pdu[0]
        try:
            if fc == 0x03 and len(pdu) == 5:
                start_addr, qty = struct.unpack(">HH", pdu[1:5])
                if qty < 1 or qty > 125:
                    return struct.pack(">BB", fc | 0x80, 0x03)
                regs = self.bank.read(start_addr, qty)
                payload = b"".join(struct.pack(">H", r) for r in regs)
                return struct.pack(">BB", fc, len(payload)) + payload

            if fc == 0x06 and len(pdu) == 5:
                addr, val = struct.unpack(">HH", pdu[1:5])
                self.bank.write(addr, [val], notify=True)
                return pdu

            if fc == 0x10 and len(pdu) >= 6:
                start_addr, qty, byte_cnt = struct.unpack(">HHB", pdu[1:6])
                if byte_cnt != qty * 2 or len(pdu) < 6 + byte_cnt:
                    return struct.pack(">BB", fc | 0x80, 0x03)
                vals = list(struct.unpack(f">{qty}H", pdu[6 : 6 + byte_cnt]))
                self.bank.write(start_addr, vals, notify=True)
                return struct.pack(">BHH", fc, start_addr, qty)

            return struct.pack(">BB", fc | 0x80, 0x01)
        except ValueError:
            return struct.pack(">BB", fc | 0x80, 0x02)


async def modbus_tcp_read_registers(host: str, port: int, start_offset: int, count: int, unit_id: int = 1, tx_id: int = 1) -> List[int]:
    """Read `count` holding registers via Modbus/TCP FC 03."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        pdu = struct.pack(">BHH", 0x03, start_offset, count)
        mbap = struct.pack(">HHHB", tx_id, 0, len(pdu) + 1, unit_id)
        writer.write(mbap + pdu)
        await writer.drain()
        hdr = await reader.readexactly(7)
        _, _, length, _ = struct.unpack(">HHHB", hdr)
        resp = await reader.readexactly(length - 1)
        fc = resp[0]
        if fc & 0x80:
            raise RuntimeError(f"Modbus exception code {resp[1]}")
        byte_cnt = resp[1]
        return list(struct.unpack(f">{byte_cnt // 2}H", resp[2 : 2 + byte_cnt]))
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def modbus_tcp_write_registers(host: str, port: int, start_offset: int, values: List[int], unit_id: int = 1, tx_id: int = 2) -> None:
    """Write holding registers via Modbus/TCP FC 16."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        qty = len(values)
        payload = struct.pack(f">{qty}H", *[v & 0xFFFF for v in values])
        pdu = struct.pack(">BHHB", 0x10, start_offset, qty, len(payload)) + payload
        mbap = struct.pack(">HHHB", tx_id, 0, len(pdu) + 1, unit_id)
        writer.write(mbap + pdu)
        await writer.drain()
        hdr = await reader.readexactly(7)
        _, _, length, _ = struct.unpack(">HHHB", hdr)
        resp = await reader.readexactly(length - 1)
        if resp[0] & 0x80:
            raise RuntimeError(f"Modbus write exception code {resp[1]}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

