"""Utilities, functions and constants for thermod daemon."""

import os
import math
import calendar

__updated__ = '2016-02-10'

# TODO inserire logger
# TODO togliere da json_schema riferimenti ad altre variabili (oppure usare solo le variabili)

# paths to main config files
main_config_files = ('thermod.conf',
                     os.path.expanduser('~/.thermod.conf'),
                    '/etc/thermod/thermod.conf')

# logger common settings
logger_base_name = 'thermod'
logger_fmt_msg = '{asctime},{msecs:03.0f} {name:17s} {levelname:8s} {message}'
logger_fmt_msg_syslog = '{name}[{process:d}]: {levelname} {message}'
logger_fmt_time = '%H:%M:%S'
logger_fmt_datetime = '%y-%m-%d %H:%M:%S'
logger_fmt_style = '{'

# thermod name convention (from json file)
json_status = 'status'
json_temperatures = 'temperatures'
json_timetable = 'timetable'
json_differential = 'differential'
json_grace_time = 'grace_time'
json_all_settings = (json_status, json_temperatures, json_timetable,
                     json_differential, json_grace_time)

json_t0_str = 't0'
json_tmin_str = 'tmin'
json_tmax_str = 'tmax'
json_all_temperatures = (json_t0_str, json_tmin_str, json_tmax_str)

json_status_on = 'on'
json_status_off = 'off'
json_status_auto = 'auto'
json_status_t0 = json_t0_str
json_status_tmin = json_tmin_str
json_status_tmax = json_tmax_str
json_all_statuses = (json_status_on, json_status_off, json_status_auto,
                     json_status_t0, json_status_tmin, json_status_tmax)

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
        'status': {'enum': list(json_all_statuses)},
        'differential': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'grace_time': {'anyOf': [{'type': 'number', 'minimum': 0},
                                 {'type': 'string', 'pattern': '[+]?[Ii][Nn][Ff]'}]},
        'temperatures': {
            'type': 'object',
            'properties': {
                json_t0_str: {'type': 'number'},
                json_tmin_str: {'type': 'number'},
                json_tmax_str: {'type': 'number'}},
            'required': list(json_all_temperatures),
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
                    'items': {'anyOf': [{'type': 'number'},
                                        {'type': 'string', 'pattern': '[-+]?[0-9]*\.?[0-9]+'},
                                        {'enum': list(json_all_temperatures)}]}}},
            'required': ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09',
                         '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
                         '20', '21', '22', '23'],
            'additionalProperties': False}}
}


class JsonValueError(ValueError):
    """Exception for invalid settings values in JSON file or socket messages."""
    
    @property
    def message(self):
        return str(self)


def is_valid_temperature(temperature):
    """Return True if the provided temperature is valid.
    
    A temperature is considered valid if it is a number or one of the
    following string values: 't0', 'tmin', 'tmax'. The positive/negative
    infinity and NaN are considered invalid.
    """
    
    result = None

    if temperature in json_all_temperatures:
        result = True
    else:
        try:
            t = float(temperature)
        except:
            result = False
        else:
            if not math.isinf(t) and not math.isnan(t):
                result = True
            else:
                result = False

    return result


def temperature_to_float(temperature):
    """Format the provided temperature as a float with one decimal.
    
    Can be used both for timetable and main temperatures in JSON file or for
    any other simple formatting. The input value must be a number except
    positive/negative infinity and NaN.
    
    @raise ValueError: if the provided temperature cannot be converted to float.
    """
    
    if not is_valid_temperature(temperature) or temperature in json_all_temperatures:
        raise ValueError('the provided temperature is not valid `{}`, '
                         'it must be a number'.format(temperature))
    
    return round(float(temperature), 1)


def json_format_temperature(temperature):
    """Format the provided temperature as a string for timetable JSON file.
    
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
        # if hour cannot be converted to int or is outside 0-23 range
        # raise a ValueError
        if int(float(hour)) not in range(24):
            raise Exception()
    except:
        raise JsonValueError('the provided hour is not valid `{}`, '
                             'it must be in range 0-23'.format(hour))

    return format(int(float(hour)), '0>2d')


def json_get_day_name(day):
    """Return the name of the provided day as used by Thermod.
    
    The input `day` can be a number in range 0-7 (0 and 7 are Sunday,
    1 is Monday, 2 is Tuesday, etc) or a day name in English or in the
    current locale.
    """
    
    result = None
    
    try:
        if day in json_days_name_map.keys():
            result = json_days_name_map[day]
        elif isinstance(day, int) and int(day) in range(8):
            result = json_days_name_map[int(day) % 7]
        elif str(day).lower() in set(json_days_name_map.values()):
            result = str(day).lower()
        else:
            day_name = [name.lower() for name in list(calendar.day_name)]
            day_abbr = [name.lower() for name in list(calendar.day_abbr)]
            
            if str(day).lower() in day_name:
                idx =  (day_name.index(str(day).lower())+1) % 7
                result = json_days_name_map[idx]
            elif str(day).lower() in day_abbr:
                idx =  (day_abbr.index(str(day).lower())+1) % 7
                result = json_days_name_map[idx]
            else:
                raise Exception
    
    except:
        #logger.debug('invalid day name or number: {}'.format(day))
        raise JsonValueError('the provided day name or number `{}` is not valid'.format(day))
    
    return result


# TODO questa funzione non si usa più, se non serve toglierla
def elstr(msg, maxlen=75):
    """Return message `msg` truncated at `maxlen` adding ellipsis '...'."""
    
    if not isinstance(msg, str):
        msg = str(msg)
    
    return (msg[:(maxlen-3)] + '...') if len(msg) > maxlen else msg
