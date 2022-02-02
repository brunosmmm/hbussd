"""Legacy cryptographic routines."""

# cryptographic routines
# @todo Document this
# @todo Actually implement this functionality

import hashlib
import random
import string
import logging

logger = logging.getLogger("hbussd.hbus_crypto")


class hbusSignature:

    e = None
    f = None
    r = None
    s = None

    sigSize = None

    def __init__(self, e, f, r, s, size):

        self.e = e
        self.f = f
        self.r = r
        self.s = s

        self.sigSize = size

    def getByteString(self):

        e_f_r = self.r

        if self.e == -1:
            e_f_r += 16

        if self.f == 2:
            e_f_r += 32

        h = hex(self.s)[2:].rstrip("L")

        if len(h) % 2:
            h = "0%s" % h

        while len(h) < self.sigSize * 2:
            h = "00%s" % h

        h = bytes.fromhex(h)

        myList = list(h)
        myList.extend([e_f_r])

        return myList


def RabinWilliamsSign(msg, p, q, size):

    while True:
        z = "".join(
            random.choice(string.ascii_uppercase + string.digits)
            for x in range(32)
        )  # random 256bit string

        r = int(hashlib.sha224(z.encode("ascii") + msg).hexdigest()[0:1], 16)
        h = int(hashlib.sha1(bytes([r]) + msg).hexdigest(), 16)

        # calcula

        U = pow(h, (q + 1) // 8, q)

        if (U ** 4 - h) % q:
            e = -1
        else:
            e = 1

        V = pow(e * h, (p - 3) // 8, p)

        if (V ** 4) * ((e * h) ** 2) - e * h:
            f = 2
        else:
            f = 1

        q1 = pow(2, (3 * q - 5) // 8, q)
        p1 = pow(2, (9 * p - 11) // 8, p)

        if f == 2:
            W = (q1 * U) % q
            X = (p1 * (V ** 3) * e * h) % p
        else:
            W = U % q
            X = ((V ** 3) * e * h) % p

        pq1 = pow(q, p - 2, p)

        Y = W + q * ((pq1 * (X - W)) % p)

        y = pow(Y, 2, p * q)

        s = min(y, p * q - y)

        if (e * f * (s ** 2)) % (p * q) != h:
            logger.debug("Authentication problem")
        else:
            break

    return hbusSignature(e, f, r, s, size)


def hbusCrypto_RabinWilliamsVerify(msg, sig, n):

    s = (sig.e * sig.f * (sig.s ** 2)) % n

    if s != int(hashlib.sha1(chr(sig.r) + msg).hexdigest(), 16):
        return False
    else:
        return True
