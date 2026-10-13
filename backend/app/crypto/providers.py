"""CryptoProvider abstraction (design doc Sections 15/28/65 - cryptographic agility).

Business logic (the sample Auth service in enterprise-lab/, and MigrationSimulator)
depends only on the `CryptoProvider` interface below, never on `cryptography` or
`pqcrypto` directly. Swapping classical -> hybrid -> PQC is a configuration change
(`get_provider(name)`), not a code change - that property is what Experiment 6
(crypto agility) measures concretely.

No cryptographic primitive is implemented from scratch here (Rule 6): classical
operations use `cryptography` (pyca, audited), PQC operations use `pqcrypto`
(PQClean reference implementations of the FIPS 203/204/205 standards).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pqcrypto.kem.ml_kem_512 as _mlkem512
import pqcrypto.kem.ml_kem_768 as _mlkem768
import pqcrypto.kem.ml_kem_1024 as _mlkem1024
import pqcrypto.sign.ml_dsa_44 as _mldsa44
import pqcrypto.sign.ml_dsa_65 as _mldsa65
import pqcrypto.sign.ml_dsa_87 as _mldsa87
import pqcrypto.sign.slh_dsa_sha2_128f as _slhdsa128f
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dh, ec, padding, rsa
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@dataclass
class KeyPair:
    public_key: bytes
    secret_key: bytes
    # opaque handles for classical keys that don't serialize cheaply per-op;
    # kept alongside the raw bytes representation.
    _public_obj: object = None
    _secret_obj: object = None


class UnsupportedOperation(NotImplementedError):
    pass


class CryptoProvider(Protocol):
    name: str
    supports_kem: bool
    supports_sign: bool

    def generate_keypair(self) -> KeyPair: ...
    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]: ...  # (ciphertext, shared_secret)
    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes: ...
    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes: ...
    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool: ...


# --------------------------------------------------------------- classical --
class RSAProvider:
    """RSA used both as a KEM (OAEP key-transport of a random 32-byte secret,
    the standard construction underlying RSA-based key exchange) and for
    signatures (PSS)."""

    supports_kem = True
    supports_sign = True

    def __init__(self, key_bits: int = 2048):
        self.name = f"RSA-{key_bits}"
        self.key_bits = key_bits

    def generate_keypair(self) -> KeyPair:
        sk = rsa.generate_private_key(public_exponent=65537, key_size=self.key_bits)
        pk = sk.public_key()
        pk_bytes = pk.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        sk_bytes = sk.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        return KeyPair(public_key=pk_bytes, secret_key=sk_bytes, _public_obj=pk, _secret_obj=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        import os
        pk = serialization.load_der_public_key(public_key)
        secret = os.urandom(32)
        ct = pk.encrypt(
            secret,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        return ct, secret

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        sk = secret_key_pair._secret_obj or serialization.load_der_private_key(secret_key_pair.secret_key, password=None)
        return sk.decrypt(
            ciphertext,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        sk = secret_key_pair._secret_obj or serialization.load_der_private_key(secret_key_pair.secret_key, password=None)
        return sk.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        pk = serialization.load_der_public_key(public_key)
        try:
            pk.verify(
                signature, message,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False


class ECDSAProvider:
    """NIST P-256 ECDSA - signature role only."""

    supports_kem = False
    supports_sign = True
    name = "ECDSA-P256"

    def generate_keypair(self) -> KeyPair:
        sk = ec.generate_private_key(ec.SECP256R1())
        pk = sk.public_key()
        pk_bytes = pk.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        sk_bytes = sk.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        return KeyPair(public_key=pk_bytes, secret_key=sk_bytes, _public_obj=pk, _secret_obj=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        raise UnsupportedOperation("ECDSA does not support key encapsulation; use ECDHProvider")

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        raise UnsupportedOperation("ECDSA does not support key encapsulation; use ECDHProvider")

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        sk = secret_key_pair._secret_obj
        return sk.sign(message, ec.ECDSA(hashes.SHA256()))

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        pk = serialization.load_der_public_key(public_key)
        try:
            pk.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False


class ECDHProvider:
    """ECDH-based KEM (ECIES-KEM construction): encapsulate() generates an
    ephemeral key pair, performs ECDH with the recipient's static public key,
    and derives a 32-byte shared secret via HKDF - the standard way ECDH is
    used as a key-encapsulation primitive."""

    supports_kem = True
    supports_sign = False
    name = "ECDH-P256"

    def generate_keypair(self) -> KeyPair:
        sk = ec.generate_private_key(ec.SECP256R1())
        pk = sk.public_key()
        pk_bytes = pk.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        sk_bytes = sk.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        return KeyPair(public_key=pk_bytes, secret_key=sk_bytes, _public_obj=pk, _secret_obj=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        recipient_pk = serialization.load_der_public_key(public_key)
        ephemeral_sk = ec.generate_private_key(ec.SECP256R1())
        shared = ephemeral_sk.exchange(ec.ECDH(), recipient_pk)
        secret = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-ecdh-kem").derive(shared)
        ct = ephemeral_sk.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return ct, secret

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        sk = secret_key_pair._secret_obj
        ephemeral_pk = serialization.load_der_public_key(ciphertext)
        shared = sk.exchange(ec.ECDH(), ephemeral_pk)
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-ecdh-kem").derive(shared)

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        raise UnsupportedOperation("ECDH does not support signing; use ECDSAProvider")

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        raise UnsupportedOperation("ECDH does not support signing; use ECDSAProvider")


class DHProvider:
    """Finite-field Diffie-Hellman used as a KEM (ephemeral-static DH + HKDF,
    the standard "DH-KEM" construction), against the fixed RFC 3526 Group 14
    (2048-bit MODP) parameters - a well-known, standardized parameter set, not
    freshly generated per keypair (live 2048-bit DH parameter generation is a
    multi-second operation and would make this a parameter-generation
    benchmark rather than a key-exchange benchmark)."""

    supports_kem = True
    supports_sign = False
    name = "DH-2048"

    _P = int(
        "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
        "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
        "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
        "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
        "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
        "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
        "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
        "3995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF",
        16,
    )
    _G = 2
    _PARAMETERS = dh.DHParameterNumbers(_P, _G).parameters()

    def generate_keypair(self) -> KeyPair:
        sk = self._PARAMETERS.generate_private_key()
        pk = sk.public_key()
        pk_bytes = pk.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        sk_bytes = sk.private_bytes(
            serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
        return KeyPair(public_key=pk_bytes, secret_key=sk_bytes, _public_obj=pk, _secret_obj=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        recipient_pk = serialization.load_der_public_key(public_key)
        ephemeral_sk = self._PARAMETERS.generate_private_key()
        shared = ephemeral_sk.exchange(recipient_pk)
        secret = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-dh-kem").derive(shared)
        ct = ephemeral_sk.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return ct, secret

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        sk = secret_key_pair._secret_obj
        ephemeral_pk = serialization.load_der_public_key(ciphertext)
        shared = sk.exchange(ephemeral_pk)
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-dh-kem").derive(shared)

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        raise UnsupportedOperation("DH does not support signing")

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        raise UnsupportedOperation("DH does not support signing")


# --------------------------------------------------------------------- pqc --
_KEM_MODULES = {"ml_kem_512": _mlkem512, "ml_kem_768": _mlkem768, "ml_kem_1024": _mlkem1024}
_SIG_MODULES = {
    "ml_dsa_44": _mldsa44, "ml_dsa_65": _mldsa65, "ml_dsa_87": _mldsa87,
    "slh_dsa_sha2_128f": _slhdsa128f,
}


class PQCKEMProvider:
    supports_kem = True
    supports_sign = False

    def __init__(self, provider_key: str):
        self._mod = _KEM_MODULES[provider_key]
        self.name = provider_key

    def generate_keypair(self) -> KeyPair:
        pk, sk = self._mod.keygen()
        return KeyPair(public_key=pk, secret_key=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        ct, ss = self._mod.encaps(public_key)
        return ct, ss

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        return self._mod.decaps(secret_key_pair.secret_key, ciphertext)

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        raise UnsupportedOperation(f"{self.name} is a KEM, not a signature scheme")

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        raise UnsupportedOperation(f"{self.name} is a KEM, not a signature scheme")


class PQCSignatureProvider:
    supports_kem = False
    supports_sign = True

    def __init__(self, provider_key: str):
        self._mod = _SIG_MODULES[provider_key]
        self.name = provider_key

    def generate_keypair(self) -> KeyPair:
        pk, sk = self._mod.keygen()
        return KeyPair(public_key=pk, secret_key=sk)

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        raise UnsupportedOperation(f"{self.name} is a signature scheme, not a KEM")

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        raise UnsupportedOperation(f"{self.name} is a signature scheme, not a KEM")

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        return self._mod.sign(secret_key_pair.secret_key, message)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        try:
            self._mod.verify(public_key, message, signature)
            return True
        except Exception:
            return False


# ------------------------------------------------------------------ hybrid --
class HybridKEMProvider:
    """Composition of a classical KEM and a PQC KEM: the combined shared secret
    is HKDF(classical_secret || pqc_secret). Secure if either component is
    secure - a standard construction (cf. draft-ietf-tls-hybrid-design) - not a
    novel or unvetted composition. We do NOT claim this provides security
    beyond what each component individually provides."""

    supports_kem = True
    supports_sign = False
    name = "HYBRID-ECDH-ML-KEM-768"

    def __init__(self):
        self._classical = ECDHProvider()
        self._pqc = PQCKEMProvider("ml_kem_768")

    def generate_keypair(self) -> KeyPair:
        c = self._classical.generate_keypair()
        p = self._pqc.generate_keypair()
        pk = len(c.public_key).to_bytes(4, "big") + c.public_key + p.public_key
        sk = len(c.secret_key).to_bytes(4, "big") + c.secret_key + p.secret_key
        return KeyPair(public_key=pk, secret_key=sk, _public_obj=(c, p), _secret_obj=(c, p))

    @staticmethod
    def _split(buf: bytes) -> tuple[bytes, bytes]:
        n = int.from_bytes(buf[:4], "big")
        return buf[4:4 + n], buf[4 + n:]

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        c_pk, p_pk = self._split(public_key)
        c_ct, c_ss = self._classical.encapsulate(c_pk)
        p_ct, p_ss = self._pqc.encapsulate(p_pk)
        combined = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-hybrid-kem").derive(c_ss + p_ss)
        ct = len(c_ct).to_bytes(4, "big") + c_ct + p_ct
        return ct, combined

    def decapsulate(self, secret_key_pair: KeyPair, ciphertext: bytes) -> bytes:
        c_sk_bytes, p_sk_bytes = self._split(secret_key_pair.secret_key)
        c_ct, p_ct = self._split(ciphertext)
        from cryptography.hazmat.primitives import serialization as _s
        c_sk_obj = _s.load_der_private_key(c_sk_bytes, password=None)
        c_ss = self._classical.decapsulate(KeyPair(b"", c_sk_bytes, _secret_obj=c_sk_obj), c_ct)
        p_ss = self._pqc.decapsulate(KeyPair(b"", p_sk_bytes), p_ct)
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"quantumshield-hybrid-kem").derive(c_ss + p_ss)

    def sign(self, secret_key_pair: KeyPair, message: bytes) -> bytes:
        raise UnsupportedOperation("Hybrid KEM provider does not sign")

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        raise UnsupportedOperation("Hybrid KEM provider does not sign")


_PROVIDER_FACTORIES = {
    "rsa2048": lambda: RSAProvider(2048),
    "rsa3072": lambda: RSAProvider(3072),
    "ecdsa_p256": lambda: ECDSAProvider(),
    "ecdh_p256": lambda: ECDHProvider(),
    "dh2048": lambda: DHProvider(),
    "ml_kem_512": lambda: PQCKEMProvider("ml_kem_512"),
    "ml_kem_768": lambda: PQCKEMProvider("ml_kem_768"),
    "ml_kem_1024": lambda: PQCKEMProvider("ml_kem_1024"),
    "ml_dsa_44": lambda: PQCSignatureProvider("ml_dsa_44"),
    "ml_dsa_65": lambda: PQCSignatureProvider("ml_dsa_65"),
    "ml_dsa_87": lambda: PQCSignatureProvider("ml_dsa_87"),
    "slh_dsa_sha2_128f": lambda: PQCSignatureProvider("slh_dsa_sha2_128f"),
    "hybrid_ecdh_mlkem768": lambda: HybridKEMProvider(),
}


def get_provider(provider_key: str):
    if provider_key not in _PROVIDER_FACTORIES:
        raise KeyError(f"No CryptoProvider registered for {provider_key!r}")
    return _PROVIDER_FACTORIES[provider_key]()
