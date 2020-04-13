"""Simple utility to upgrade a device via gNOI.

It implements system.proto SetPackage method.  This project focuses on access
points which are the device types most widely supporting gNOI from all major
vendors.
"""

from absl import app
from absl import flags
from absl import logging
import gnoi_lib

FLAGS = flags.FLAGS

flags.DEFINE_string('name', '', 'Name of the device to upgrade, eg. '
                    '"something.example.com"')
flags.DEFINE_string('vendor', '', 'Name of vendor, eg. "arista"')
flags.DEFINE_string('target_addr', '', 'DNS name of device, may match the name '
                    'flag. eg. "something.example.com"')
flags.DEFINE_string('port', '', 'Port number for the gRPC connection')
flags.DEFINE_string('software_version', '', 'Software version to upgrade to')
flags.DEFINE_boolean('activate', True, 'To activate image immediately')

_CENTRALLY_MANAGED = ('mist', 'cisco')


def main(argv):
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  target_addr = FLAGS.target_addr
  vendor = FLAGS.vendor.lower()
  if vendor in _CENTRALLY_MANAGED:
    target_addr = None

  device = gnoi_lib.GNOITarget(FLAGS.name, vendor, ip=target_addr, port=FLAGS.port)
  logging.info('Will upgrade device %s', device.name)
  response = device.SetPackage(FLAGS.software_version, FLAGS.activate)
  logging.info(response)
  print('Device accepted upgrade call!')

if __name__ == '__main__':
  app.run(main)
