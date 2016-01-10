'''
    ThunderGate - an open source toolkit for PCI bus exploration
    Copyright (C) 2015-2016  Saul St. John

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from winlib import *
from tapdrv import verbose

class TapWinInterface(object):
    def __init__(self, dev):
        self.dev = dev
        self.mm = dev.interface.mm
        self._connected = False

    def __enter__(self):
        self.tfd = create_tap_if()
        self._tg_evt = IoctlAsync(IOCTL_TGWINK_PEND_INTR, self.dev.interface.cfgfd, 8)
        self._tap_evt = ReadAsync(self.tfd, 1518)
        self._hCon = GetStdHandle(STD_INPUT_HANDLE)
        self._events = (HANDLE * 3)(self._tg_evt.req.hEvent, self._tap_evt.req.hEvent, self._hCon)
        self._tg_evt.submit()
        return self
    
    def _tg_is_ready(self):
        return self._tg_evt.check()

    def _tap_is_ready(self):
        if not self._connected:
            return False
        return self._tap_evt.check()

    def __exit__(self):
        self._tap_evt.reset(False)
        self._tg_evt.reset(False)
        del self._events
        del self._tap_evt
        del self._tg_evt

        del_tap_if(self.tfd)

    def _conin_is_ready(self):
        res = WaitForSingleObject(self._hCon, 0)
        if WAIT_FAILED == res:
            raise WinError()
        return (res == 0)

    def _get_key(self):
        res = None
        cnt = DWORD(0)
        if not GetNumberOfConsoleInputEvents(self._hCon, pointer(cnt)):
            raise WinError()
        if 0 == cnt.value:
            return ''

        ir = (INPUT_RECORD * cnt.value)()
        rr = DWORD(0)
        
        if not ReadConsoleInput(self._hCon, cast(pointer(ir), POINTER(INPUT_RECORD)), cnt.value, pointer(rr)):
            raise WinError()

        if 0 == rr.value:
            print "[.] no input records available to examine"
            return ''

        print "[.] examining %d input records" % rr.value
        for i in range(rr.value):
            if ir[i].EventType != KEY_EVENT:
                continue
            if not ir[i].Event.KeyEvent.bKeyDown:
                continue
            res = ir[i].Event.KeyEvent.uChar.AsciiChar
            print "[.] found keydown event for key \"%s\" in input record #%d" % (res, i)
            return res
        print "[.] found no keydown events"
        return ''

    def _wait_for_something(self):
        res = WaitForMultipleObjects(3, cast(pointer(self._events), POINTER(c_void_p)), False, INFINITE)
        if WAIT_FAILED == res:
            raise WinError()

    def _get_serial(self):
        serial = cast(self._tg_evt.buffer, POINTER(c_uint64)).contents.value
        self._tg_evt.reset()
        return serial
 
    def _get_packet(self):
        if verbose:
            print "[+] getting a packet from tap device...",
        pkt_len = self._tap_evt.pkt_len
        pkt = self.mm.alloc(pkt_len)
        RtlCopyMemory(pkt, self._tap_evt.buffer, pkt_len)
        self._tap_evt.reset()
        if verbose:
            print "read %d bytes" % pkt_len
        return (pkt, pkt_len)

    def _write_pkt(self, pkt, length):
        if not self._connected:
            return
        o = OVERLAPPED(hEvent = CreateEvent(None, True, False, None))
        try:
            if verbose:
                print "[!] attempting to write to the tap device...",
            if not WriteFile(self.tfd, pkt, length, None, pointer(o)):
                err = WinError()
                if err.winerror != ERROR_IO_PENDING:
                    raise err
                if WAIT_FAILED == WaitForSingleObject(o.hEvent, INFINITE):
                    raise WinError()
            print "wrote %d bytes" % o.InternalHigh
        finally:
            CloseHandle(o.hEvent)

    def _set_tapdev_status(self, connected):
        if verbose:
            print "[+] setting tapdev status to %s" % ("up" if connected else "down")
        o = OVERLAPPED(hEvent = CreateEvent(None, True, False, None))
        try:
            val = c_int32(1 if connected else 0)
            if not DeviceIoControl(self.tfd, TAP_WIN_IOCTL_SET_MEDIA_STATUS, pointer(val), 4, pointer(val), 4, None, pointer(o)):
                err = WinError()
                if err.winerror == ERROR_IO_PENDING:
                    if WAIT_FAILED == WaitForSingleObject(o.hEvent, INFINITE):
                        raise WinError()
                elif err.winerror == 0:
                    pass
                else:
                    raise err
            if connected:
                self._tap_evt.submit()
            else:
                self._tap_evt.reset(False)
            self.connected = connected
        finally:
            CloseHandle(o.hEvent)