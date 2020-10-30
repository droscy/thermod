# Thermod Changelog

## 2.0.0~development

  * Changes that break retro-compatibility:
    - `import thermod` only imports constants and classes useful for clients and monitors
    - remove `error_code` from `Settings` class (it wasn't used anywhere)
    - move `DEGREE*` variables in `common.py` module
    - remove `to_celsius()` and `to_fahrenheit()` from thermometers
      (there is `ScaleAdapterThermometerDecorator` to automatically
      manage the conversion)
    - rename `mode` to `inertia`, `status` to `mode` and `heating_status`
      (or `heatcool_status`) to `status` in config files, in socket messages,
      in TimeTable class, in ThermodStatus class, etc.
    - remove support for different hardwares between heating and cooling systems

  * Other changes:
    - add support for python > 3.5 and aiohttp >= 3.0
    - change setup script to install Thermod using pip
    - temperatures are retrieved via a coroutine to handle long I/O steps
    - add config file and documentation for lighttpd and apache2 web servers
    - add systemd service file

## 1.2.1

  * Fix crash when cooling setting is empty
  * Add auto-restart of averaging task in case of hardware errors

## 1.2.0

  * Add support for cooling system
  * Add support for 1-Wire thermometers
  * Add filter and jail files for fail2ban
  * Add a degree scale adapter (now the temperatures can be shown in
    fahrenheit degrees even if the thermometers are in celsius)
 
## 1.1.0

  * Move the averaging-task outside `PiAnalogZeroThermometer` in order to use
    that feature with any thermometer
  * Add a *similarity-checker* for thermometers in order to recognize
    malfunctions that produce an abnormal temperature reading

## 1.0.0

  * First stable release

