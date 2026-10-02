"""Stable public exception taxonomy for the KT Node Python SDK."""


class KtError(RuntimeError):
    """Base error raised by the KT Node Python SDK."""


class AbiCompatibilityError(KtError):
    """The loaded native library is incompatible with this SDK."""


class UnsupportedCapabilityError(KtError):
    """The loaded runtime does not provide a requested capability."""


class ClosedResourceError(KtError):
    """A runtime or callback context was used after its lifetime ended."""


class ChannelContractError(KtError, ValueError):
    """The node package does not define a usable channel contract."""


class UnknownChannelError(ChannelContractError):
    """A requested channel is absent or has the wrong direction."""


class TypedChannelError(KtError):
    """Base error for manifest-driven typed channel access."""


class MissingCodecError(TypedChannelError):
    """No installed datatype codec matches a declared channel datatype."""


class PayloadDecodeError(TypedChannelError):
    """A channel payload does not satisfy its declared datatype."""


class ValueEncodeError(TypedChannelError):
    """A Python value cannot be encoded for its declared output datatype."""
