# config module for thermod

import os

__updated__ = '2015-10-02'

# TODO inserire logger

# path to main config file
# TODO mettere controllo se siamo su Windows o su Unix
main_config_files = ('thermod.conf',
                     os.path.expanduser('~/.thermod.conf'),
                    '/etc/thermod/thermod.conf')

# logger common settings
logger_fmt = '%(asctime)s %(name)-8s %(levelname)-8s %(message)s'
logger_datefmt = '%H:%M:%S'

# thermod name convention (from json file)
json_status = 'status'
json_temperatures = 'temperatures'
json_timetable = 'timetable'
json_all_main_settings = (json_status, json_temperatures, json_timetable)

json_t0_str = 't0'
json_tmin_str = 'tmin'
json_tmax_str = 'tmax'
json_all_temperatures = (json_t0_str, json_tmin_str, json_tmax_str)

json_status_on = 'on'
json_status_off = 'off'
json_status_auto = 'auto'
json_all_statuses = (json_status_on, json_status_off, json_status_auto,
                     json_t0_str, json_tmin_str, json_tmax_str)

# the key of the following dict is th same number of %w of strftime()
# the name is used to avoid errors with different locales
json_days_name_map = {1: 'monday',    '1': 'monday',
                      2: 'tuesday',   '2': 'tuesday',
                      3: 'wednesday', '3': 'wednesday',
                      4: 'thursday',  '4': 'thursday',
                      5: 'friday',    '5': 'friday',
                      6: 'saturday',  '6': 'saturday',
                      0: 'sunday',    '0': 'sunday'}


json_schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Timetable',
    'description': 'Timetable file for thermod daemon',
    'type': 'object',
    'properties': {
        'status': {'enum': ['auto', 'on', 'off', 't0', 'tmin', 'tmax']},
        'temperatures': {
            'type': 'object',
            'properties': {
                't0': {'type': 'number'},
                'tmin': {'type': 'number'},
                'tmax': {'type': 'number'}},
            'required': ['t0', 'tmin', 'tmax'],
            'additionalProperties': False},
        'timetable': {
            'type': 'object',
            'properties': {
                'monday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'tuesday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'wednesday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'thursday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'friday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'saturday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]},
                'sunday': {'type': 'object', 'oneOf': [{'$ref': '#/definitions/day'}]}},
            'required': ['monday', 'tuesday', 'wednesday', 'thursday',
                         'friday', 'saturday', 'sunday'],
            'additionalProperties': False}},
    'required': ['status', 'temperatures', 'timetable'],
    'additionalProperties': False,
    'definitions': {
        'day': {
            'patternProperties': {
                '([01][0-9]|2[0-3])': {
                    'type': 'array',
                    'items': {'oneOf': [{'type': 'number'},
                                        {'type': 'string', 'pattern': '[-+]?[0-9]*\.?[0-9]+'},
                                        {'enum': ['t0', 'tmin', 'tmax']}]}}},
            'required': ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
                         '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
                         '20', '21', '22', '23'],
            'additionalProperties': False}}
}


class JsonValueError(ValueError):
    """Exception for invalid settings value in json file"""
    pass


def is_valid_temperature(temperature):
    """Return True if the temperature is valid.
    
    A temperature is considered valid if it is a number or one of the
    following value: 't0', 'tmin', 'tmax'.
    """
    
    result = None

    if temperature in json_all_temperatures:
        result = True
    else:
        try:
            float(temperature)
            result = True
        except:
            result = False

    return result


def json_format_main_temperature(temperature):
    """Format the provided temperature as a float with one decimal.
    
    Can be used both for timetable and main temperatures in json file.
    """
    
    if not is_valid_temperature(temperature) or temperature in json_all_temperatures:
        raise JsonValueError('the provided temperature is not valid ({}), '
                             'it must be a number'.format(temperature))
    
    return round(float(temperature), 1)


def json_format_temperature(temperature):
    """Format the provided temperature as a string for timetable.
    
    The output can be a number string with one single decimal (XX.Y) or
    one of the following string: 't0', 'tmin', 'tmax'.
    """
    
    result = None

    if is_valid_temperature(temperature):
        if temperature in json_all_temperatures:
            result = temperature
        else:
            # rounding returned value in order to avoid to many rapid changes
            # between on and off
            result = format(round(float(temperature), 1), '.1f')
    else:
        raise JsonValueError('the provided temperature is not valid ({}), '
                             'it must be a number or one of the following '
                             'values: {}'.format(
                                    temperature,
                                    ', '.join(json_all_temperatures)))

    return result


def json_format_hour(hour):
    """Format the provided hour as a string in 24-hour clock with leading 0."""
    try:
        # if hour cannot be converted to int or is outside 0-23 range rise a
        # ValueError
        if int(float(hour)) not in range(24):
            raise Exception()
    except:
        raise JsonValueError('the provided hour is not valid ({}), '
                             'it must be in range 0-23'.format(hour))

    return format(int(float(hour)), '0>2d')
