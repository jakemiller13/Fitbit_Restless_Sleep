# -*- coding: utf-8 -*-
"""
Created on Tue Sep 10 13:26:38 2019

@author: jmiller
"""

import fitbit
from fitbit import gather_keys_oauth2 as Oauth2
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# Gathered from Fitbit web app
CLIENT_ID = input('Client ID: ')
CLIENT_SECRET = input('Client Secret: ')

# Access Fitbit API
server = Oauth2.OAuth2Server(CLIENT_ID, CLIENT_SECRET)
server.browser_authorize()

# Setup API client (NOTE: updating to v1.2 for Sleep Logs)
ACCESS_TOKEN = str(server.fitbit.client.session.token['access_token'])
REFRESH_TOKEN = str(server.fitbit.client.session.token['refresh_token'])
auth2_client = fitbit.Fitbit(CLIENT_ID, CLIENT_SECRET, oauth2 = True,
                             access_token = ACCESS_TOKEN,
                             refresh_token = REFRESH_TOKEN)
auth2_client.API_VERSION = 1.2

def format_date(in_date):
    '''
    in_date (tuple of integers): (YYYY, MM, DD)
        NOTE: single digit day/months should be entered as D or M, not DD or MM
    returns (datetime): YYYY-MM-DD
    '''
    date = datetime.date(*in_date)
    return date.strftime('%Y-%m-%d')

def get_intraday_hr_data(date):
    '''
    date (str): 'YYYY-MM-DD'
    returns: heart rate date in 1 min intervals for given date
    '''
    return auth2_client.intraday_time_series('activities/heart',
                                             base_date = date,
                                             detail_level = '1sec')

def plot_sleep_levels(sleep_data):
    '''
    Plots a bar chart of sleep levels for 1 day
    '''
    sleep_stages = sleep_data['summary']['stages']
    plt.figure(facecolor = 'w', figsize = (8, 8))
    plt.bar(range(len(sleep_stages)),
            list(sleep_stages.values()),
            align = 'center')
    plt.xticks(range(len(sleep_stages)), list(sleep_stages.keys()))
    plt.ylabel('Minutes')
    plt.grid(axis = 'y')
    plt.title('Minutes per Stage [{}]'.format(date.date()))
    plt.show()
    
###############
# GET HR DATA #
###############
date = format_date((2019, 5, 5)) # start date of last challenge
hr_data = get_intraday_hr_data(date)
hr_df = pd.DataFrame(hr_data['activities-heart-intraday']['dataset'])
hr_df['time'] = hr_df['time'].apply(pd.to_datetime)
hr_df = hr_df.set_index('time')

######################
# LOOP FOR ONE MONTH # can also use start/end
######################
#start_date = format_date((2019, 5, 25))
#date_range = pd.date_range(start_date, periods = 2)
#sleep_df = pd.DataFrame()
#for date in date_range:
#    sleep_data = auth2_client.sleep(date)
#    try:
#        sleep_df = sleep_df.append(pd.DataFrame(
#                                   sleep_data['sleep'][0]['levels']['data']),
#                                   ignore_index = True)
#        plot_sleep_levels(sleep_data)
#    except IndexError:
#        pass
#
#sleep_df['dateTime'] = sleep_df['dateTime'].apply(pd.to_datetime)
#sleep_df = sleep_df.set_index('dateTime')

#####################################
# GET SLEEP DATA FOR (MAX) 100 DAYS #
#####################################
start_date = datetime.datetime(2018, 2, 25)
period = 100
end_date = start_date + datetime.timedelta(days = period)
sleep_data = auth2_client.time_series('sleep',
                                      base_date = start_date,
                                      end_date = end_date)

# Pull out sleep summary
sleep_summary_df = pd.DataFrame()
for date in sleep_data['sleep']:
    temp_df = pd.DataFrame(date['levels']['summary']).loc['minutes']
    temp_df = temp_df.append(pd.Series(date['efficiency'])\
                             .rename({0: 'efficiency'}))
    minutes_data = pd.Series(temp_df.rename(date['dateOfSleep']))
    sleep_summary_df = sleep_summary_df.append(minutes_data)
sleep_summary_df.index = pd.to_datetime(sleep_summary_df.index)

# This drops "old" style columns but keeps NaN to show gaps in information
sleep_summary_df.drop(columns = ['asleep', 'awake', 'restless'],
                      inplace = True)

# Plot wake, light, deep, rem on one axis, sleep efficiency on other
fig, ax1 = plt.subplots(figsize = (10, 10))
ax1.set_title('Sleep Efficiency', fontdict = {'fontsize': 15})
for i in ['wake', 'light', 'deep', 'rem']:
    ax1.plot(sleep_summary_df.index[::-1],
             sleep_summary_df[i],
             linewidth = '2',
             label = i)
ax1.set_xlabel('Date')
ax1.set_xticklabels(labels = sleep_summary_df.index[::-1],
                    rotation = 45,
                    ha = 'right')
ax1.set_ylim(0, 500)
ax1.set_ylabel('Minutes per Stage')
ax2 = plt.twinx(ax = ax1)
ax2.plot(sleep_summary_df.index[::-1],
         sleep_summary_df['efficiency'],
         color = 'black',
         linewidth = '2',
         label = 'efficiency')
ax2.set_ylim(0, 100)
ax2.set_ylabel('Sleep Efficiency')
ax1.grid(which = 'major', axis = 'both')
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax2.legend(lines_1 + lines_2,
           labels_1 + labels_2,
           loc = 'lower center',
           bbox_to_anchor = (0.5, 0.0),
           ncol = 5,
           fancybox = True,
           shadow = True)
plt.show()