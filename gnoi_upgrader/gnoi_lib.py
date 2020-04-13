"""Simple library that implements gNOI system.proto.

This library is meant to abstract away gRPC and remove the need to interact with
the proto definition by any application that imports this.  Initial version
implements a simple SetPackage call only but is structured in a way so it can be
easily expanded.
"""

from absl import app
from absl import flags
from absl import logging
import system_pb2
import system_pb2_grpc
import grpc

FLAGS = flags.FLAGS

_ONE_HOUR_SECONDS = 3600
_GNOI_TARGET_PORTS = {
    'mist': '443',
    'arista': '8080',
    'cisco': '10161',
    'aruba': '10162'
}

_GNOI_TARGET_IPS = {'mist': 'openconfig-gnoi.gc1.mist.com',
                    'cisco': 'openconfig.cisco.com'}

# Note casing for host overrides, it matters.
_GNOI_HOST_OVERRIDES = {'mist': 'openconfig-gnoi.gc1.mist.com',
                        'arista': 'openconfig.mojonetworks.com',
                        'aruba': 'OpenConfig.arubanetworks.com'}

# hostname metadata requirements, ie. target is not AP.
_HOSTNAME_REQUIRED = {
    'mist': True,
    'arista': False,
    'cisco': True,
    'aruba': False
}

_ARISTA_CA_CERT = b"""
-----BEGIN CERTIFICATE-----
MIIFZDCCA0wCCQDJgoRi4SucQjANBgkqhkiG9w0BAQsFADBzMQswCQYDVQQGEwJV
UzELMAkGA1UECAwCQ0ExHDAaBgNVBAoME01vam8gTmV0d29ya3MsIEluYy4xEzAR
BgNVBAsMCk9wZW5Db25maWcxJDAiBgNVBAMMG29wZW5jb25maWcubW9qb25ldHdv
cmtzLmNvbTAgFw0xODA3MzAxMDExNDJaGA8yMTE4MDcwNjEwMTE0MlowczELMAkG
A1UEBhMCVVMxCzAJBgNVBAgMAkNBMRwwGgYDVQQKDBNNb2pvIE5ldHdvcmtzLCBJ
bmMuMRMwEQYDVQQLDApPcGVuQ29uZmlnMSQwIgYDVQQDDBtvcGVuY29uZmlnLm1v
am9uZXR3b3Jrcy5jb20wggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDp
QCFFIfd7utWablqAiYAs7W2BlbjauJRjwbGMSqlwc1VenomDClN5IshCx/i6aKFz
fDo1+Vpmcb4057OXImBz06feNFT/wmL9ZDa3matlmizsMjDpkpmTCkV50kKAow3c
ig7vCLMFltH6kKpO2rdVoaUCGhMb/B/K305I1qKVP7totIIwuYnehrgoWeSx5Eie
L1ZU3z0y1yiADhAAS4i1E1ygzYku+Myq8ETf/1Iit08hfasD3q1q+vOj/DE5BCoG
Ds3jIUF3XloBTw3s90Sp92BI2NcFs5zhFK+N5wTQKF88F90dvLid6ukJBQydOZUT
YDHjR3NZ8nuXIt/bq+9ZX67GsNrHmwqUKslC4W5VHzT662HY52EJ0c8VNZH13/92
Hh6KuPIJ8gSjDzTzx9iEwFrGffwVSf+85DkjQJmnc1h1Tyi+FZal7Ytqi4LZr9HU
U1DiPxZyMS+yS99juICAQJLw3Vq31ySeDvClB20ccXpKTQkaxY9RQqiH2UwjYF1V
HWywa4eziORr6/eyVonSixzQkM0eHVH3xi/jA2J7bEKNzXcdVQGAq54pMV9+P5nZ
haFt48R4j1ieIWDb1CWSyDEGEE8rYNI+z+nCZkpR2ttni0D1/R2ApJAO47TCEy0M
9y3050kEbUzvAxZAIC/N2yQaAU2PK+UOYztJpxEMjwIDAQABMA0GCSqGSIb3DQEB
CwUAA4ICAQB0vgULp+vApoPDyZTtYN94QOOsi71vdu9rElJp8c0vungSA6n33sDm
X39eMkilEKi6z+ssHKCCOWsx35UeM9FLhsxqu7bYivxKZV5wwlaj5u57QNVtuPv/
XVKqXS6K80jJH3TiuXDY1Wb4Dlr7sVZYWwRgkUhdFhptzUBRJqU0PSYNzzDL4fSy
MdZvprGW2LxibNGVPUnKO+JuGEynau4TixWdMKHwKYquJpAyJ732C5LZ0RTb2J3b
TiGjV5I/oMgnh7vKdeMaO5lSs9Kn9T+DBDaKfWc4ZgYsO7PzzETMLwUAG3WI1S47
v1WKFgjbMv2kzYbWXpqeGRoK6nwpi66FnUM120DxRIC/7Z4slRXOJHlXfEXzzz7R
oyUFL5kNzOKxGn+QoOsLrRO/Agn7vN2U6RdzLFPxWC3K6EGF2e+9xvWLHF2CbCTn
375TD+tly7wAv4nnRdIhK5PI6LyV9m7IwmjI77MiEBatYu3wWOPX5zcH+D7hFAae
Ro7RLhmgLC4obnn0u2cdJiY28BKyrtVn0OK5bYtjhp5eNkDoIuMIj/jPnFzR8KAy
qDEczPJ35LiRgTv7gnAk2dmJHcJLqeambbc/XT9JdQHnSqWi/tIVTUictTQMORDM
9OVPDGeJ11hW0VQv6WuOwnu+v4qX0NRgapVy0iRqgaGQfBRPE22zaw==
-----END CERTIFICATE-----"""

_ARUBA_CA_CERT = b"""
-----BEGIN CERTIFICATE-----
MIIFwTCCA6mgAwIBAgIJAMZaSpMC8K9CMA0GCSqGSIb3DQEBCwUAMHcxCzAJBgNV
BAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRcwFQYDVQQKDA5BcnViYSBOZXR3
b3JrczETMBEGA1UECwwKT3BlbkNvbmZpZzElMCMGA1UEAwwcT3BlbkNvbmZpZy5h
cnViYW5ldHdvcmtzLmNvbTAeFw0xOTA5MDMxNDI5MTJaFw0yOTA4MzExNDI5MTJa
MHcxCzAJBgNVBAYTAlVTMRMwEQYDVQQIDApDYWxpZm9ybmlhMRcwFQYDVQQKDA5B
cnViYSBOZXR3b3JrczETMBEGA1UECwwKT3BlbkNvbmZpZzElMCMGA1UEAwwcT3Bl
bkNvbmZpZy5hcnViYW5ldHdvcmtzLmNvbTCCAiIwDQYJKoZIhvcNAQEBBQADggIP
ADCCAgoCggIBAM3fDZdfbQFm/aQo+wYYwBH4X40ymeM9Fhjbx2CwpErtF8MaoCBd
aoGlh5Sgdx/7RR8YrZGO/4vpPXUIGE/0sBqfCNUiqm5txli1nWNWPPXPRsgkfs4j
rLdhRZJq33FHVF6fgpo0Nbw5/eWZUfoYLZkpLMHV8QUgTQoH1RNWBqP+W+DTZefi
LTx93rHrPTTvf7hPjiQr4otOj6fuKgQU07zyGDMUw0e4pRQ6ZqsMe2MA65MOCYED
lZyH9VowmAifE4hevGzurMRlk/c+AOxS7vEllQWbHgl6wBS5Q/L/YzoiiKQ7ddqv
yISOeX/OTQ+SSVii+xd0owlKfVV8c7f36iuTJceezzJ3B12XWVzrtGyGrzVDgTcG
EcJ9lYtRU+oSbU+0Mgx21IOk7NsTU0dxgQTJ04Wf9H2l1p5RKVDUmT1wRBG6Jrl9
5c6mpEHaORro04hs0elKobDJAp5FZN82xCGjEAfHKJ6M7hRU2p7/co6yaLie5AjZ
DJYBrr2S4WCUr/CjN4br8hktxct3LfJSLZS9sTwILLNfbEbWytqsVdxSVVFjv7mW
EHtsZQUlJvDdulw9Rs7khSGR7HISt417JIsvcuGEOw4vJVH2c5BNvI1jp5AP+4HB
I6l4aoxEDHBVyP456TXzj5gzydkdkzsnKww+qT3jQGOYfIO9c9CxBEaDAgMBAAGj
UDBOMB0GA1UdDgQWBBTgNaHDFmYJOL3z+WrhEpWvXN+qZDAfBgNVHSMEGDAWgBTg
NaHDFmYJOL3z+WrhEpWvXN+qZDAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUA
A4ICAQApCEoYKfjS2SR153lKK7y2B957Z/YJKh4vDSeiqbNcEutFlwMXLJZnryJ8
/rH+ZUIqL5mvKALu+4Hx5r7cvhMYd+kaZ9MUfZMBZx7aLkUoehdmQK3VUFqvoXG1
zCrAf4TRKpd6TrL8eFTnET4pB3nP4fxa2t8OMp/xXB8V45wkzkIGjmrvZptwwNN1
StbrUZXokuzlaioQXZ4U878gPb9Z2CKvf+qRuRjLIz9kHqKqh7S9biMeMyu9EJT7
YPD9mjEpYSqclKBfkvynOQWwEBFKH4XYqnhntB7GMZLi2hG9/TRpGk1pMaxbJVcg
i+jngCkdFI+pZZldY9G9VnO9beurZIo/IAJr3WV67RXhjOCO9jnH1KV+cH3kTKmy
3B1Gt0Em6cfSrp/YIEW9+iUghkg4+3HK/YkZ4Mtr62NC7mVzuLUPmgJolDSlJg6t
1fg4hnCxWKENql4RlZbv5f2dNUmqiVz9aqJMU6T7DzlmFKerTvoljxO2bTjCMkYX
KjFgTAXBDQwQuw8LHXIkAArGGc33OiD/zqBlUgrLBv7S+GWQF7kP9pMkfhmfajvF
k+emJSPYCYQn2jTyvdm6CwgQZAILYFOaUYUwwRx/JJUoUFerjCappO8ydY5v7TnO
4qOhdzY8fK+b+DXc4KG+yrBZ24emCJAcf/2mRzXssftdo0l8Sw==
-----END CERTIFICATE-----"""


class GNOITarget(object):
  """Base class to perform gNOI Operations."""

  def __init__(self, name, vendor, ip=None, port=None, channel=None):
    self.name = name
    self.vendor = vendor
    self.ip = ip or _GNOI_TARGET_IPS.get(vendor.lower(), '0.0.0.0')
    self.port = port or _GNOI_TARGET_PORTS.get(vendor.lower(), '443')
    self.grpc_creds = self._GetCreds(vendor)
    self.channel = channel
    self.stub = self._CreateStub(self.name, self.vendor, self.ip, self.port,
                                 self.grpc_creds)

  def _GetCreds(self, vendor):
    """Returns a gRPC.ssl_channel_credentials object."""
    root_cert = None
    if vendor.lower() == 'arista':
      root_cert = _ARISTA_CA_CERT
    elif vendor.lower() == 'aruba':
      root_cert = _ARUBA_CA_CERT
    else:
      root_cert = None

    return grpc.ssl_channel_credentials(
        root_certificates=root_cert, private_key=None, certificate_chain=None)

  def _CreateStub(self, name, vendor, ip, port, grpc_creds):
    """Creates a gNOI stub/channel for a given target."""
    logging.info('Creating stub for "%s": vendor: "%s", ip: "%s", port: "%s"',
                 name, vendor, ip, port)
    host_override = _GNOI_HOST_OVERRIDES.get(vendor.lower(), None)

    target = ip + ':' + port
    if host_override:
      logging.info('Creating channel: %s, %s, %s',
                   target, grpc_creds, host_override)
      self.channel = grpc.secure_channel(
          target, grpc_creds,
          (('grpc.ssl_target_name_override', host_override,),))
    else:
      self.channel = grpc.secure_channel(target, grpc_creds)

    return system_pb2_grpc.SystemStub(self.channel)

  def SetPackage(self, version, activate=True):
    """Sets the package/firmware version the target should be on.

    Args:
      version(str): The operation system version.
      activate(bool): Make the image active after transfer is complete.
    """
    logging.info('Will set version to %s', version)
    package = system_pb2.Package(version=version, activate=activate)
    request_pb = system_pb2.SetPackageRequest(package=package)

    try:
      self.stub.SetPackage(iter([request_pb]), timeout=120, wait_for_ready=True,
                           metadata=_GetMetadata(self.vendor, self.name))
    except grpc.RpcError as e:
      # Could also key off of grpc.StatusCode.UNAVAILABLE/etc.
      # we close the channel otherwise gRPC may retry indefinitely depending on
      # the failure type/implementation.
      logging.info('Failed to SetPackage RPC, received error: %s', e.code())
      self.channel.close()
      raise

def _GetVendorCreds(vendor):
  """Gets vendor credentials for GNMI/GNOI.

  This would be a good place to call your own secret storage system.
  """
  logging.info('Getting credentials for %s', vendor)
  vendor_name = vendor.lower()
  username = 'admin'
  password = 'admin'

  return username, password

def _GetMetadata(vendor, host_name):
  """Returns appropriate metadata given a vendor and host name."""
  username, password = _GetVendorCreds(vendor)

  if _HOSTNAME_REQUIRED.get(vendor.lower(), False):
    logging.info('Will set hostname on grpc metadata for: %s', host_name)
    return [('username', username), ('password', password),
            ('hostname', host_name)]
  else:
    return [('username', username), ('password', password)]
