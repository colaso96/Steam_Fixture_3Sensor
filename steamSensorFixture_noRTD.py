import matplotlib.pyplot as plt
import xlsxwriter
import os
import sys
import glob
import smtplib
import ADS1256
import RPi.GPIO as GPIO
import math
import numpy as np
import pandas as pd
from datetime import date
import time
import constants
import board
import busio
import digitalio
import adafruit_max31865


#--------------------------------------------------------------------- DIRECTORY FUNCTION -----------------------------------------------------------------------
def new_Dir():
    DATE = date.today().strftime("%m-%d-%y")
    path1 = os.getcwd() + '/' + 'RAW DATA'
    path2 = path1 + "/" + DATE
    path3 = path2 + "/" + constants.STEAM_APPLIANCE
    
    if not os.path.exists(path1):
        os.mkdir(path1)
        os.mkdir(path2)
        os.mkdir(path3)
    elif not os.path.exists(path2):
        os.mkdir(path2)
        os.mkdir(path3)
    elif not os.path.exists(path3):
        os.mkdir(path3)

    onlylinks = [f for f in os.listdir(path3) if os.path.isdir(os.path.join(path3, f))]
    counter = len(onlylinks)
    file_path = path3 + "/" + str(counter)
    os.mkdir(file_path)
    os.chdir(file_path)
    
def reset_Dir():
    os.chdir(constants.START_PATH)
        
#--------------------------------------------------------------------- EXCEL FUNCTION -----------------------------------------------------------------------
def excel_FileName():
    return 'Steam_Fixture_RAW_DATA.xlsx'

def dataframe_to_Excel(derivative_df):
    input_df = input_to_df()
    writer = pd.ExcelWriter(excel_FileName(), engine='xlsxwriter')
    constants.df.to_excel(writer, sheet_name= 'Raw_Data')
    input_df.to_excel(writer, sheet_name= 'Procedure_Results_Data')
    derivative_df.to_excel(writer, sheet_name= 'Top Derivative - Time')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Graphs')
    worksheet.insert_image(0,0,'Steam_Fixture_Graphs.png')
    writer.save()

#--------------------------------------------------------------------- HELPER FUNCTIONS --------------------------------------------------------------------
def to_Humidity(raw):
    return (raw/0x7fffff) * 100.00

def input_to_df():
    input_dict = {'Steam Appliance':['Function', 'Food Load', 'Time Interval (min)', 'Cook Time (min)', 'Sensor Height (in)', 'Initial Water Mass (g)', 'Initial Food Mass (g)',
                    'Final Water Mass (g)', 'Final Food Mass (g)', 'Water Loss (g)','Average Steam Sensor Humidity (%)', 'Steam Accumulation (Count * min)', 'Average Steam Temperature (C)'],
                    constants.STEAM_APPLIANCE: [constants.FUNCTION, constants.FOOD_LOAD, constants.TIME_INTERVAL, constants.MONITOR_TIME/60, constants.SENSOR_HEIGHT, constants.INITIAL_WATER_MASS, 
                    constants.INITIAL_FOOD_MASS, constants.FINAL_WATER_MASS, constants.FINAL_FOOD_MASS, constants.WATER_LOSS, constants.STEAM_SENSOR_HUMIDITY, constants.STEAM_ACCUMULATION, 
                    average_steam_temperature()] }
    input_df = pd.DataFrame(input_dict)
    return input_df

def all_Sensors_to_humidity(ADC_Value):
    analog_Steam_Sensor_1 = ADC_Value[constants.STEAM_SENSOR1]
    analog_Steam_Sensor_2 = ADC_Value[constants.STEAM_SENSOR2]
    analog_Steam_Sensor_3 = ADC_Value[constants.STEAM_SENSOR3]
    humidity_Steam_Sensor_1 = to_Humidity(analog_Steam_Sensor_1)
    humidity_Steam_Sensor_2 = to_Humidity(analog_Steam_Sensor_2)
    humidity_Steam_Sensor_3 = to_Humidity(analog_Steam_Sensor_3)
    return humidity_Steam_Sensor_1, humidity_Steam_Sensor_2, humidity_Steam_Sensor_3

def check_Sensors():
    try:
        ADC = ADS1256.ADS1256()
        ADC.ADS1256_init()
        ADC_Value = ADC.ADS1256_GetAll()
        humidity_Steam_Sensor_1, humidity_Steam_Sensor_2, humidity_Steam_Sensor_3 = all_Sensors_to_humidity(ADC_Value)

        time.sleep(.25)
        
        ADC_Value = ADC.ADS1256_GetAll()
        humidity_Steam_Sensor_1, humidity_Steam_Sensor_2, humidity_Steam_Sensor_3 = all_Sensors_to_humidity(ADC_Value)

        if ((humidity_Steam_Sensor_1 > constants.THRESHOLD) |(humidity_Steam_Sensor_2 > constants.THRESHOLD) | (humidity_Steam_Sensor_3 > constants.THRESHOLD)):
            return False

        return True
    
    except :
        GPIO.cleanup()
        exit()

#----------------------------------------------------------------- DATAFRAME FUNCTION -------------------------------------------------------------------
def dataframe_Structure():
    columns = {'Time (min)':[], 'Steam Sensor 1 (Count)':[], 'Humidity 1 (%)':[],'Steam Sensor 2 (Count)':[], 'Humidity 2 (%)':[], 
            'Steam Sensor 3 (Count)':[], 'Humidity 3 (%)':[], 'Steam Temp. (C)':[], 'Surrounding Temp. (C)':[]}
    df = pd.DataFrame(columns)
    return df

def update_Dataframe(updated_time, ADC_Value):
    analog_Steam_Sensor_1 = ADC_Value[constants.STEAM_SENSOR1]
    analog_Steam_Sensor_2 = ADC_Value[constants.STEAM_SENSOR2]
    analog_Steam_Sensor_3 = ADC_Value[constants.STEAM_SENSOR3]
    humidity_Steam_Sensor_1 = to_Humidity(analog_Steam_Sensor_1)
    humidity_Steam_Sensor_2 = to_Humidity(analog_Steam_Sensor_2)
    humidity_Steam_Sensor_3 = to_Humidity(analog_Steam_Sensor_3)
    
    RTD1 = adafruit_max31865.MAX31865(constants.RTD_SPI, constants.CS1, rtd_nominal=1000, ref_resistor=4300.0, wires=3)
    RTD2 = adafruit_max31865.MAX31865(constants.RTD_SPI, constants.CS2, rtd_nominal=1000, ref_resistor=4300.0, wires=3)

    temp1 = RTD1.temperature
    temp2 = RTD2.temperature
    if ((temp1 > 200) | (temp2 > 200)):
        temp1, temp2 = np.nan, np.nan
    else:
        temp1, temp2 = temp1, temp2
    
    if not ((humidity_Steam_Sensor_1 >= constants.THRESHOLD) | (humidity_Steam_Sensor_2 >= constants.THRESHOLD) | (humidity_Steam_Sensor_3 >= constants.THRESHOLD)):
        new_row = {'Time (min)':updated_time, 
                'Steam Sensor 1 (Count)':0, 'Humidity 1 (%)':0,
                'Steam Sensor 2 (Count)':0, 'Humidity 2 (%)':0, 
                'Steam Sensor 3 (Count)':0, 'Humidity 3 (%)':0, 
                'Steam Temp. (C)':temp1, 'Surrounding Temp. (C)':temp2}
        constants.df = constants.df.append(new_row, ignore_index = True)
    if ((humidity_Steam_Sensor_1 >= constants.THRESHOLD) | (humidity_Steam_Sensor_2 >= constants.THRESHOLD) | (humidity_Steam_Sensor_3 >= constants.THRESHOLD)):
        new_row = {'Time (min)':updated_time, 
                'Steam Sensor 1 (Count)':analog_Steam_Sensor_1, 'Humidity 1 (%)':humidity_Steam_Sensor_1,
                'Steam Sensor 2 (Count)':analog_Steam_Sensor_2, 'Humidity 2 (%)':humidity_Steam_Sensor_2, 
                'Steam Sensor 3 (Count)':analog_Steam_Sensor_3, 'Humidity 3 (%)':humidity_Steam_Sensor_3, 
                'Steam Temp. (C)':temp1, 'Surrounding Temp. (C)':temp2}
        constants.df = constants.df.append(new_row, ignore_index = True)
        
def average_Steam_Sensor_Humidity():
    total = constants.df['Humidity 1 (%)'].sum() + constants.df['Humidity 2 (%)'].sum() + constants.df['Humidity 3 (%)'].sum()
    rows = len(constants.df.index)
    return total/(3*rows)

def average_steam_temperature():
    return constants.df['Steam Temp. (C)'].mean()

def average_surrounding_humidity():
    return constants.df['Surrounding Humidity (%)'].mean()

def average_surrounding_temperature():
    return constants.df['Surrounding Temp. (C)'].mean()
    
def steam_Accumulation():
    constants.df['Delta T (min)'] = abs(constants.df['Time (min)'].diff(periods=-1))
    constants.df['Steam Accumulation (Count * min)'] = (constants.df['Steam Sensor 1 (Count)'] * constants.df['Delta T (min)']) + (constants.df['Steam Sensor 2 (Count)'] * constants.df['Delta T (min)']) + (constants.df['Steam Sensor 3 (Count)'] * constants.df['Delta T (min)'])
    return constants.df['Steam Accumulation (Count * min)'].sum()

def record_data():
    try:
        constants.df = dataframe_Structure()
        ADC = ADS1256.ADS1256()
        ADC.ADS1256_init()
        while constants.UPDATED_TIME > 0:
            ADC_Value = ADC.ADS1256_GetAll()
            updated_time = constants.MONITOR_TIME/60 - constants.UPDATED_TIME/60
            update_Dataframe(updated_time, ADC_Value)
            time.sleep(2)

    except :
        GPIO.cleanup()
        exit()

#----------------------------------------------------------------- GRAPH FUNCTION -------------------------------------------------------------------
def humidity_Graph():
    plt.plot('Time (min)', 'Humidity 1 (%)', data = constants.df, color = 'red')
    plt.plot('Time (min)', 'Humidity 2 (%)', data = constants.df, color = 'black')
    plt.plot('Time (min)', 'Humidity 3 (%)', data = constants.df, color = 'blue')
    plt.xlabel('Time (min)')
    plt.ylabel('Humidity (%)')
    plt.title('Time vs. Steam Sensor\'s Humidity')
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))

def steam_Accumulation_Graph():
    start_Interval = constants.df.iloc[0]['Time (min)']
    end_Interval = start_Interval + constants.TIME_INTERVAL
    derivative_time = dict()
    while start_Interval < constants.MONITOR_TIME:
        df2 = constants.df.loc[(constants.df['Time (min)'] >= start_Interval) & (constants.df['Time (min)'] <= end_Interval)]
        x = df2['Time (min)']
        y = df2['Steam Accumulation (Count * min)']
        if not x.empty and not y.empty:
            m,b = np.polyfit(x,y,1)
            plt.plot(x,y,'ro')
            plt.plot(x, m*x+b)
            derivative_time[m] = start_Interval
        start_Interval = end_Interval
        end_Interval = start_Interval + constants.TIME_INTERVAL
    plt.plot('Time (min)', 'Steam Accumulation (Count * min)', 'o', data = constants.df, color = 'red')
    plt.xlabel('Time (min)')
    plt.ylabel('Steam Accum. (Count * min)')
    plt.title('Time vs. Steam Accumulation')
    return derivative_time

def temperature_Graph():
    plt.plot('Time (min)', 'Steam Temp. (C)', data = constants.df, color = 'red')
    plt.plot('Time (min)', 'Surrounding Temp. (C)', data = constants.df, color = 'blue')
    plt.xlabel('Time (min)')
    plt.ylabel('Temperature (C)')
    plt.title('Time vs. Steam Temperature vs Surrounding Temperature')
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))

def steam_Fixture_Graphs():
    plt.figure(num=None, figsize=(10, 10), dpi=80, facecolor='w', edgecolor='k')
    plt.subplot(311)
    derivative_time = steam_Accumulation_Graph()

    plt.subplot(312)
    humidity_Graph()

    plt.subplot(313)
    temperature_Graph()

    plt.tight_layout()
    return derivative_time
