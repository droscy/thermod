# config module for thermod

# TODO inserire logger

# thermod name convention (from json file)
json_t0_str = 't0'
json_t_min_str = 'tmin'
json_t_max_str = 'tmax'
json_all_temperatures = (json_t0_str, json_t_min_str, json_t_max_str)

json_status_on = 'on'
json_status_off = 'off'
json_status_auto = 'auto'
json_all_statuses = (json_status_on, json_status_off, json_status_auto, json_t0_str, json_t_min_str, json_t_max_str)

json_status = 'status'
json_temperatures = 'temperatures'
json_timetable = 'timetable'

# the key of the following dict is th same number of %w of strftime()
# the name is used to avoid errors with different locales
json_days_name_map = {1:'monday',    '1':'monday',
                      2:'tuesday',   '2':'tuesday',
                      3:'wednesday', '3':'wednesday',
                      4:'thursday',  '4':'thursday',
                      5:'friday',    '5':'friday',
                      6:'saturday',  '6':'saturday',
                      0:'sunday',    '0':'sunday'}

def is_valid_temperature(temperature):
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

def json_format_temperature(temperature):
    result = None
    
    if is_valid_temperature(temperature):
        if temperature in json_all_temperatures:
            result = temperature
        else:
            # rounding returned value in order to avoid to many rapid changes between on and off
            result = format(round(float(temperature),1),'.1f')
    else:
        raise ValueError('the provided temperature is not valid ({}), it must be a number or one of the following values : '.format(temperature) + ', '.join(json_all_temperatures))
        
    return result

def json_format_hour(hour):
    try:
        # if hour cannot be converted to int or is outside 0-23 range rise a ValueError
        if int(float(hour)) not in range(24):
            raise Exception()
    except:
        raise ValueError('the provided hour is not valid ({}), it must be in range 0-23'.format(hour))
        
    return format(int(float(hour)),'0>2d')
