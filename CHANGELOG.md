# Thermod Changelog

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

