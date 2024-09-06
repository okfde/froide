"""

Extracted and modified from https://github.com/dirkmoors/drf-tus
available under MIT License, Copyright (c) 2017, Dirk Moors

"""

tus_api_version = "1.0.0"
tus_api_version_supported = ["1.0.0"]
tus_api_extensions = [
    "creation",
    "creation-defer-length",
    "termination",
    "checksum",
    "expiration",
]
tus_api_checksum_algorithms = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]
