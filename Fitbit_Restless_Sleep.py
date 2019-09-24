# -*- coding: utf-8 -*-
"""
Created on Tue Sep 10 13:26:38 2019

@author: jmiller
"""

import fitbit
from fitbit import gather_keys_oauth2 as Oauth2
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Need to get specifics from https://dev.fitbit.com/apps
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

############################
# DEFINTE DATES TO LOOK AT #
############################
start_date = datetime.datetime(2019, 9, 1)
period = 30
end_date = start_date + datetime.timedelta(days = period)

###############
# GET HR DATA #
###############
date = format_date((2019, 5, 5)) # start date of last challenge
hr_data = get_intraday_hr_data(date)
hr_df = pd.DataFrame(hr_data['activities-heart-intraday']['dataset'])
hr_df['time'] = hr_df['time'].apply(pd.to_datetime)
hr_df = hr_df.set_index('time')

###########################
# GET ACTIVE MINUTES DATA #
###########################
activity_level_df = pd.DataFrame()

# Recall 1440 minutes per day, so Sedentary = 1440 - (other levels)
activity_level = ['LightlyActive', 'FairlyActive', 'VeryActive']
for level in activity_level:
    activity_data = auth2_client.time_series('activities/minutes{}'\
                                             .format(level),
                                             base_date = start_date,
                                             end_date = end_date)
    activity_df = pd.DataFrame(activity_data['activities-minutes{}'.\
                                             format(level)]).\
                               rename({'value': level}, axis = 1)
    activity_df[level] = pd.to_numeric(activity_df[level])
    activity_level_df = activity_level_df.join(activity_df.\
                                               set_index('dateTime'),
                                               how = 'outer')
# Dataframe cleanup
activity_level_df = activity_level_df.reset_index()
activity_level_df['dateTime'] = pd.to_datetime(activity_level_df['dateTime'])

# TODO clean up so these dataframes get created in similar ways

#####################################
# GET SLEEP DATA FOR (MAX) 100 DAYS #
#####################################
sleep_summary_df = pd.DataFrame()

sleep_data = auth2_client.time_series('sleep',
                                      base_date = start_date,
                                      end_date = end_date)
for date in sleep_data['sleep'][::-1]:
    # Minutes in each stage
    sleep_df = pd.DataFrame(date['levels']['summary']).loc['minutes']
    # Sleep efficiency
    sleep_df = sleep_df.append(pd.Series(date['efficiency'])\
                             .rename({0: 'efficiency'}))
    # Asleep before 11 (1 if True, 0 if False)
    start_time = pd.to_datetime(date['startTime']).time()
    sleep_df = sleep_df.append(pd.Series(
                             int(start_time < datetime.time(23, 00, 00))).\
                             rename({0: 'before_11'}))
    
    minutes_data = pd.Series(sleep_df.rename(date['dateOfSleep']))
    sleep_summary_df = sleep_summary_df.append(minutes_data)

# Dataframe cleanup
sleep_summary_df = sleep_summary_df[['efficiency', 'wake', 'light', 'deep',
                                     'rem', 'awake', 'restless', 'asleep',
                                     'before_11']]
sleep_summary_df = sleep_summary_df.reset_index()\
                                   .rename({'index':'dateTime'}, axis = 1)
sleep_summary_df['dateTime'] = pd.to_datetime(sleep_summary_df['dateTime'])

# If Fitbit can't register HR, only tracks "asleep", "awake", "restless"
# Don't correspond to more detailed info (e.g wake vs awake different values)
sleep_summary_df.drop(columns = ['asleep', 'awake', 'restless'],
                      inplace = True)

############
# BOX PLOT #
############
# TODO Improve this plot
sleep_summary_df[['wake', 'light', 'deep', 'rem']].plot(kind = 'box')


# Join dataframes
df = activity_level_df.join(sleep_summary_df.set_index('dateTime'),
                            on = 'dateTime')

# TODO adjust y axis
##################################################
# PLOT SLEEP EFFICIENCY ON TOP OF ACTIVITY LEVEL #
##################################################
fig, ax1 = plt.subplots(figsize = (10, 10))
fig.suptitle('Sleep Efficiency vs. Activity Levels',
             fontsize = 20)
ax2 = plt.twinx(ax = ax1)
df[['LightlyActive', 'FairlyActive', 'VeryActive']].plot(ax = ax1,
                                                         kind = 'bar',
                                                         stacked = True,
                                                         cmap = 'Pastel2')
df[['wake', 'light', 'deep', 'rem']].plot(ax = ax1,
                                          linewidth = '2',
                                          linestyle = '--',
                                          marker = '.',
                                          markersize = 10)
ax1.set_ylabel('Sleep/Activity Minutes', fontsize = 15)
date_range = pd.date_range(start_date - datetime.timedelta(days = 2),
                           end_date,
                           freq = '2D')
ax1.set_xticklabels(pd.Series(date_range).apply(lambda x: x.date()))
ax1.xaxis.set_major_locator(ticker.MultipleLocator(2))
df['efficiency'].plot(ax = ax2,
                      linewidth = '4',
                      color = 'k',
                      label = 'Sleep Efficiency')
# Plot markers where asleep after 11
df[df['before_11'] == 0]['efficiency'].plot(kind = 'line',
                                            marker = '^',
                                            markersize = 10,
                                            linestyle = 'none',
                                            color = 'red',
                                            label = 'Asleep after 11PM')
ax2.set_ylim(50, 100)
ax2.set_ylabel('Sleep Efficiency', fontsize = 15)
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2,
           labels_1 + labels_2,
           loc = 'lower center',
           bbox_to_anchor = (0.5, 1.0),
           ncol = 5,
           fancybox = True,
           shadow = True)
fig.autofmt_xdate()
plt.show()







######################################################
# PLOTTED USING 2 SUBPLOTS, IS THIS BETTER OR WORSE? #
######################################################

fig, axs = plt.subplots(2, gridspec_kw = {'hspace': 0}, figsize = (10, 10))
fig.suptitle('Sleep  Efficiency', fontsize = 20)
for i in ['wake', 'light', 'deep', 'rem']:
    axs[0].plot(sleep_summary_df.index,
             sleep_summary_df[i],
             linewidth = '2',
             linestyle = '--',
             marker = '.',
             markersize = 10,
             label = i)
axs[0].set_xlim(sleep_summary_df.index[0], sleep_summary_df.index[-1])
axs[0].set_xlabel('Date',
               fontdict = {'fontsize': 20})
axs[0].set_xticklabels(labels = sleep_summary_df.index,
                    rotation = 45,
                    ha = 'right')
axs[0].set_ylim(0, 500)
ax2 = plt.twinx(ax = axs[0])
ax2.plot(sleep_summary_df.index,
         sleep_summary_df['efficiency'],
         color = 'black',
         linewidth = '3',
         label = 'efficiency')
ax2.set_ylim(0, 100)
ax2.set_ylabel('Sleep Efficiency',
               fontdict = {'fontsize': 15})
axs[0].grid(which = 'major', axis = 'both')
lines_1, labels_1 = axs[0].get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax2.legend(lines_1 + lines_2,
           labels_1 + labels_2,
           loc = 'lower center',
           bbox_to_anchor = (0.5, 1.0),
           ncol = 5,
           fancybox = True,
           shadow = True)

###################################
# STACKED BAR FOR ACTIVITY LEVELS #
###################################
activity_level_df[activity_level].plot.bar(ax = axs[1],
                                           stacked = True)
axs[1].set_xlabel('Date',
               fontdict = {'fontsize': 20})
axs[1].set_xlim(sleep_summary_df.index[0], sleep_summary_df.index[-1])
axs[1].set_xticklabels(labels = df['dateTime'])
axs[1].legend(loc = 'lower center',
           bbox_to_anchor = (0.5, 0.0),
           ncol = 3,
           fancybox = True,
           shadow = True)
axs[1].grid(which = 'major', axis = 'both')
fig.text(0.05, 0.4, 'Minutes per Stage', ha = 'center', rotation = 'vertical', fontdict = {'fontsize': 15})
plt.show()