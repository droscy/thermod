# vim: fileencoding=utf-8

from distutils.core import setup

setup(name='thermod',
      version='0.0.0~beta1',
      description='Programmable thermostat daemon for smart-heating automation.',
      long_description='TODO',
      author='Simone Rossetto',
      author_email='simros85@gmail.com',
      url='TODO',
      license = 'GPL-3.0+',
      packages=['thermod'],
      #package_dir={'thermod': 'lib/thermod'},
      scripts=['bin/thermod'],
      data_files=[('/etc/thermod', ['etc/thermod.conf', 'etc/timetable.json']),
                  #('/lib/systemd/system', ['thermod.service']),
                  ],
)
