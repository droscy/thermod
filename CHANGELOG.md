# Thermod Changelog

## 2.0.0~development

  * Changes that break retro-compatibility:
    - 'import thermod' only imports constants and classes useful for clients and monitors
    - remove 'error_code' from Settings class (it wasn't used anywhere)

  * New features:

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

  * move the averaging-task outside `PiAnalogZeroThermometer` in order to use
    that feature with any thermometer
  * add a *similarity-checker* for thermometers in order to recognize
    malfunctions that produce an abnormal temperature reading

## 1.0.0

  * first stable release

